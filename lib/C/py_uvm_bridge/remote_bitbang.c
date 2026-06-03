// See LICENSE.Berkeley for license details.
// Modified for pydebug: non-blocking accept, proper disconnect handling

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include "remote_bitbang.h"

int rbs_init(uint16_t port)
{
    socket_fd  = 0;
    client_fd  = 0;
    recv_start = 0;
    recv_end   = 0;
    rbs_err    = 0;

    socket_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (socket_fd == -1) {
        fprintf(stderr, "remote_bitbang failed to make socket: %s (%d)\n",
                strerror(errno), errno);
        abort();
    }

    fcntl(socket_fd, F_SETFL, O_NONBLOCK);
    int reuseaddr = 1;
    if (setsockopt(socket_fd, SOL_SOCKET, SO_REUSEADDR, &reuseaddr,
                   sizeof(int)) == -1) {
        fprintf(stderr, "remote_bitbang failed setsockopt: %s (%d)\n",
                strerror(errno), errno);
        abort();
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port        = htons(port);

    if (bind(socket_fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        fprintf(stderr, "remote_bitbang failed to bind socket: %s (%d)\n",
                strerror(errno), errno);
        abort();
    }

    if (listen(socket_fd, 1) == -1) {
        fprintf(stderr, "remote_bitbang failed to listen on socket: %s (%d)\n",
                strerror(errno), errno);
        abort();
    }

    socklen_t addrlen = sizeof(addr);
    if (getsockname(socket_fd, (struct sockaddr *)&addr, &addrlen) == -1) {
        fprintf(stderr, "remote_bitbang getsockname failed: %s (%d)\n",
                strerror(errno), errno);
        abort();
    }

    tck   = 1;
    tms   = 1;
    tdi   = 1;
    trstn = 1;
    quit  = 0;

    fprintf(stderr, "JTAG remote bitbang server is ready\n");
    fprintf(stderr, "Listening on port %d\n", ntohs(addr.sin_port));
    return 1;
}

// Non-blocking accept — returns immediately if no client is waiting.
void rbs_accept()
{
    client_fd = accept(socket_fd, NULL, NULL);
    if (client_fd == -1) {
        if (errno == EAGAIN) {
            // No client yet — just return, we'll try next tick.
        } else {
            fprintf(stderr, "failed to accept on socket: %s (%d)\n",
                    strerror(errno), errno);
            abort();
        }
        client_fd = 0;
    } else {
        fcntl(client_fd, F_SETFL, O_NONBLOCK);
        fprintf(stderr, "Accepted successfully.\n");
    }
}

void rbs_tick(unsigned char *jtag_tck, unsigned char *jtag_tms,
              unsigned char *jtag_tdi, unsigned char *jtag_trstn,
              unsigned char jtag_tdo)
{
    static int tick_count = 0;
    tick_count++;
    if (tick_count % 1000000 == 0) {
        fprintf(stderr, "[bitbang-tick] %dM ticks, client_fd=%d\n", tick_count/1000000, client_fd);
    }

    if (client_fd > 0) {
        tdo = jtag_tdo;
        rbs_execute_command();
    } else {
        rbs_accept();
    }

    *jtag_tck   = tck;
    *jtag_tms   = tms;
    *jtag_tdi   = tdi;
    *jtag_trstn = trstn;
}

void rbs_reset()
{
    // trstn = 0;
}

void rbs_set_pins(char _tck, char _tms, char _tdi)
{
    tck = _tck;
    tms = _tms;
    tdi = _tdi;
}

void rbs_execute_command()
{
    static int cmd_count = 0;
    char command;
    ssize_t num_read = read(client_fd, &command, sizeof(command));

    if (num_read == -1) {
        if (errno == EAGAIN) {
            // No data available right now — return, will try next tick.
            return;
        } else {
            fprintf(stderr,
                    "remote_bitbang failed to read on socket: %s (%d)\n",
                    strerror(errno), errno);
            abort();
        }
    } else if (num_read == 0) {
        // Client disconnected (EOF).
        fprintf(stderr, "Remote end disconnected (after %d commands)\n", cmd_count);
        close(client_fd);
        client_fd = 0;
        return;
    }

    cmd_count++;
    if (cmd_count % 1000 == 0) {
        fprintf(stderr, "[bitbang] %d commands processed (last='%c')\n", cmd_count, command);
    }

    int dosend = 0;
    char tosend = '?';

    switch (command) {
    case 'B': break;
    case 'b': break;
    case 'r': rbs_reset(); break;
    case 's': rbs_reset(); break;
    case 't': rbs_reset(); break;
    case 'u': rbs_reset(); break;
    case '0': rbs_set_pins(0, 0, 0); break;
    case '1': rbs_set_pins(0, 0, 1); break;
    case '2': rbs_set_pins(0, 1, 0); break;
    case '3': rbs_set_pins(0, 1, 1); break;
    case '4': rbs_set_pins(1, 0, 0); break;
    case '5': rbs_set_pins(1, 0, 1); break;
    case '6': rbs_set_pins(1, 1, 0); break;
    case '7': rbs_set_pins(1, 1, 1); break;
    case 'R':
        dosend = 1;
        tosend = tdo ? '1' : '0';
        break;
    case 'Q':
        quit = 1;
        break;
    default:
        fprintf(stderr, "remote_bitbang got unsupported command '%c'\n",
                command);
    }

    if (dosend) {
        while (1) {
            ssize_t bytes = write(client_fd, &tosend, sizeof(tosend));
            if (bytes == -1) {
                fprintf(stderr, "failed to write to socket: %s (%d)\n",
                        strerror(errno), errno);
                abort();
            }
            if (bytes > 0) {
                break;
            }
        }
    }

    if (quit) {
        fprintf(stderr, "Remote end disconnected\n");
        close(client_fd);
        client_fd = 0;
    }
}

unsigned char rbs_done()
{
    return quit;
}

int rbs_exit_code()
{
    return rbs_err;
}
