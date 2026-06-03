/*
 * uvm_bridge.c
 *
 * Unix-socket JSON server that runs inside the simulator process (via DPI).
 * Spawned in a POSIX thread at time-zero by the UVM test.
 *
 * Protocol (newline-delimited JSON):
 *   Python → C:  {"id":1,"op":"read", "addr":17}
 *   Python → C:  {"id":2,"op":"write","addr":16,"data":2147483649}
 *   Python → C:  {"id":3,"op":"reset"}
 *   Python → C:  {"id":4,"op":"shutdown"}
 *
 *   C → Python:  {"id":1,"status":"ok","data":3}
 *   C → Python:  {"id":2,"status":"ok"}
 *   C → Python:  {"id":4,"status":"ok"}
 *   C → Python:  {"id":X,"status":"err","msg":"..."}
 *
 * The C bridge acts as a passive relay between Python and UVM.
 * It uses a mutex-protected shared buffer and condition variables
 * to safely hand off requests/responses between the server thread
 * and the simulator's main thread (via DPI polling).
 *
 * Build alongside the simulator:
 *   gcc -shared -fPIC -std=c11 uvm_bridge.c -o uvm_bridge.so -lpthread
 *
 * The socket path is set by UVM_BRIDGE_SOCK (env var) or defaults to
 * /tmp/uvm_bridge.sock.
 */

#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include "svdpi.h"

/* ── Configuration ──────────────────────────────────────────────────────── */
#define DEFAULT_SOCK  "/tmp/uvm_bridge.sock"
#define RECV_BUF_SZ   1024
#define SEND_BUF_SZ   256
#define MAX_CLIENTS   1     /* single Python driver */

/* ── Op codes (must match SV side) ──────────────────────────────────────── */
#define OP_READ     1
#define OP_WRITE    2
#define OP_RESET    3
#define OP_SHUTDOWN 4

/* ── Shared state (bridge ↔ server thread) ──────────────────────────────── */
static volatile int g_shutdown = 0;    /* set to 1 to stop the thread */
static int          g_server_fd = -1;

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  g_cond  = PTHREAD_COND_INITIALIZER;

static int g_req_valid = 0;
static int g_req_op = 0;
static int g_req_addr = 0;
static unsigned int g_req_data = 0;

static int g_rsp_valid = 0;
static unsigned int g_rsp_data = 0;

/* ── Simple JSON helpers (no external library dependency) ───────────────── */

/* Find the integer value of a JSON key in a flat object string.
   Returns 1 on success, 0 if key not found. */
static int json_get_int(const char *json, const char *key, long long *out) {
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char *p = strstr(json, pattern);
    if (!p) return 0;
    p += strlen(pattern);
    while (*p == ':' || *p == ' ') p++;
    char *end;
    *out = strtoll(p, &end, 10);
    return end != p;
}

/* Find the string value of a JSON key (writes into buf, max buf_len). */
static int json_get_str(const char *json, const char *key, char *buf, size_t buf_len) {
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    const char *p = strstr(json, pattern);
    if (!p) return 0;
    p += strlen(pattern);
    while (*p == ':' || *p == ' ') p++;
    if (*p != '"') return 0;
    p++;
    size_t i = 0;
    while (*p && *p != '"' && i < buf_len - 1)
        buf[i++] = *p++;
    buf[i] = '\0';
    return 1;
}

/* ── Request handler ────────────────────────────────────────────────────── */

static void send_response(int client_fd, const char *buf) {
    size_t total = strlen(buf);
    size_t sent  = 0;
    while (sent < total) {
        ssize_t n = write(client_fd, buf + sent, total - sent);
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("[uvm_bridge] write");
            break;
        }
        sent += (size_t)n;
    }
}

static void handle_request(int client_fd, const char *line) {
    char send_buf[SEND_BUF_SZ];
    long long id   = -1;
    char op[32]    = {0};
    long long addr = -1;
    long long data = 0;

    json_get_int(line, "id",   &id);
    json_get_str(line, "op",   op, sizeof(op));
    json_get_int(line, "addr", &addr);
    json_get_int(line, "data", &data);

    if (strcmp(op, "shutdown") == 0) {
        /* Shutdown: signal SV to exit its command loop */
        pthread_mutex_lock(&g_mutex);
        g_req_op = OP_SHUTDOWN;
        g_req_addr = 0;
        g_req_data = 0;
        g_req_valid = 1;
        g_rsp_valid = 0;
        /* Wait for SV to acknowledge */
        while (!g_rsp_valid) { pthread_cond_wait(&g_cond, &g_mutex); }
        pthread_mutex_unlock(&g_mutex);
        snprintf(send_buf, sizeof(send_buf), "{\"id\":%lld,\"status\":\"ok\"}\n", id);
        send_response(client_fd, send_buf);
        return;
    }

    if (strcmp(op, "read") == 0 || strcmp(op, "write") == 0 || strcmp(op, "reset") == 0) {
        pthread_mutex_lock(&g_mutex);
        if (strcmp(op, "read") == 0) {
            g_req_op = OP_READ; g_req_addr = addr; g_req_data = 0;
        } else if (strcmp(op, "write") == 0) {
            g_req_op = OP_WRITE; g_req_addr = addr; g_req_data = data;
        } else {
            g_req_op = OP_RESET; g_req_addr = 0; g_req_data = 0;
        }
        g_req_valid = 1;
        g_rsp_valid = 0;
        while (!g_rsp_valid) { pthread_cond_wait(&g_cond, &g_mutex); }

        if (strcmp(op, "read") == 0) {
            snprintf(send_buf, sizeof(send_buf),
                     "{\"id\":%lld,\"status\":\"ok\",\"data\":%u}\n", id, g_rsp_data);
        } else {
            snprintf(send_buf, sizeof(send_buf),
                     "{\"id\":%lld,\"status\":\"ok\"}\n", id);
        }
        pthread_mutex_unlock(&g_mutex);
        send_response(client_fd, send_buf);
        return;
    }

    /* Unknown op */
    snprintf(send_buf, sizeof(send_buf),
             "{\"id\":%lld,\"status\":\"err\",\"msg\":\"unknown op: %s\"}\n",
             id, op);
    send_response(client_fd, send_buf);
}

/* ── Server thread ──────────────────────────────────────────────────────── */

static void *server_thread(void *arg) {
    (void)arg;
    char recv_buf[RECV_BUF_SZ];

    while (!g_shutdown) {
        int client_fd = accept(g_server_fd, NULL, NULL);
        if (client_fd < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            if (g_shutdown) break;
            perror("[uvm_bridge] accept");
            continue;
        }
        printf("[uvm_bridge] Python client connected\n");
        fflush(stdout);

        FILE *stream = fdopen(client_fd, "r");
        if (!stream) { close(client_fd); continue; }

        while (fgets(recv_buf, sizeof(recv_buf), stream)) {
            /* Strip trailing newline */
            size_t len = strlen(recv_buf);
            if (len > 0 && recv_buf[len-1] == '\n')
                recv_buf[len-1] = '\0';
            if (len == 0) continue;
            handle_request(client_fd, recv_buf);
        }

        printf("[uvm_bridge] Python client disconnected\n");
        fflush(stdout);
        fclose(stream);
    }
    return NULL;
}

/* ── Public API (called from DPI SystemVerilog) ─────────────────────────── */

int dpi_bridge_get_req(int *op, int *addr, unsigned int *data) {
    int ret = 0;
    pthread_mutex_lock(&g_mutex);
    if (g_req_valid) {
        *op = g_req_op;
        *addr = g_req_addr;
        *data = g_req_data;
        g_req_valid = 0;
        ret = 1;
    }
    pthread_mutex_unlock(&g_mutex);
    return ret;
}

void dpi_bridge_put_rsp(unsigned int data) {
    pthread_mutex_lock(&g_mutex);
    g_rsp_data = data;
    g_rsp_valid = 1;
    pthread_cond_signal(&g_cond);
    pthread_mutex_unlock(&g_mutex);
}

/* Called from the UVM test via DPI.
   Starts the socket server in a background thread.
   Returns 0 on success, -1 on error. */
int uvm_bridge_start(void) {
    const char *sock_path = getenv("UVM_BRIDGE_SOCK");
    if (!sock_path) sock_path = DEFAULT_SOCK;

    /* Remove stale socket */
    unlink(sock_path);

    g_server_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (g_server_fd < 0) { perror("[uvm_bridge] socket"); return -1; }

    /* Allow rapid restart */
    int opt = 1;
    setsockopt(g_server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, sock_path, sizeof(addr.sun_path) - 1);

    if (bind(g_server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("[uvm_bridge] bind"); close(g_server_fd); return -1;
    }
    chmod(sock_path, 0666);

    if (listen(g_server_fd, MAX_CLIENTS) < 0) {
        perror("[uvm_bridge] listen"); close(g_server_fd); return -1;
    }

    pthread_t tid;
    if (pthread_create(&tid, NULL, server_thread, NULL) != 0) {
        perror("[uvm_bridge] pthread_create"); return -1;
    }
    pthread_detach(tid);

    printf("[uvm_bridge] listening on %s\n", sock_path);
    fflush(stdout);
    return 0;
}

/* Called from end-of-test DPI hook to stop the thread cleanly. */
void uvm_bridge_stop(void) {
    g_shutdown = 1;
    if (g_server_fd >= 0) {
        shutdown(g_server_fd, SHUT_RDWR);
        close(g_server_fd);
        g_server_fd = -1;
    }
    printf("[uvm_bridge] stopped\n");
    fflush(stdout);
}
