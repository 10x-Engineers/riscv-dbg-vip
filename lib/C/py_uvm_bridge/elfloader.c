/*
 * elfloader.c — Standalone DPI-C ELF loader for CVA6 SoC simulation
 *
 * Provides the same DPI-C interface as the CVA6 elfloader.cc but without
 * the fesvr dependency.  Reads ELF64 and ELF32 LOAD segments directly.
 *
 * DPI-C exports:
 *   void read_elf       (const char *filename);
 *   char get_section    (long long *address, long long *len);
 *   void read_section_sv(long long  address, const svOpenArrayHandle buffer);
 *
 * The SV side imports these as:
 *   import "DPI-C" function void read_elf(input string filename);
 *   import "DPI-C" function byte get_section(output longint address, output longint len);
 *   import "DPI-C" context function void read_section_sv(input longint address, inout byte buffer[]);
 */

#include <svdpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <assert.h>

/* ── Minimal ELF definitions (avoids fesvr dependency) ───────────────────── */

#define EI_NIDENT   16
#define EI_CLASS     4
#define ELFCLASS32   1
#define ELFCLASS64   2
#define PT_LOAD      1

typedef struct {
    unsigned char e_ident[EI_NIDENT];
    uint16_t e_type, e_machine;
    uint32_t e_version;
    uint64_t e_entry, e_phoff, e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize, e_phentsize, e_phnum;
    uint16_t e_shentsize, e_shnum, e_shstrndx;
} Elf64_Ehdr;

typedef struct {
    uint32_t p_type, p_flags;
    uint64_t p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align;
} Elf64_Phdr;

typedef struct {
    unsigned char e_ident[EI_NIDENT];
    uint16_t e_type, e_machine;
    uint32_t e_version, e_entry, e_phoff, e_shoff, e_flags;
    uint16_t e_ehsize, e_phentsize, e_phnum;
    uint16_t e_shentsize, e_shnum, e_shstrndx;
} Elf32_Ehdr;

typedef struct {
    uint32_t p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz;
    uint32_t p_flags, p_align;
} Elf32_Phdr;

/* ── Section storage ─────────────────────────────────────────────────────── */

#define MAX_SECTIONS 64

typedef struct {
    uint64_t address;
    uint64_t length;
    uint8_t *data;      /* malloc'd copy of file segment */
} section_t;

static section_t sections[MAX_SECTIONS];
static int       num_sections  = 0;
static int       section_index = 0;

/* ── read_elf ────────────────────────────────────────────────────────────── */

void read_elf(const char *filename) {
    int fd;
    struct stat st;
    char *buf;
    int i;

    /* Reset state (allows calling read_elf multiple times) */
    for (i = 0; i < num_sections; i++)
        free(sections[i].data);
    num_sections  = 0;
    section_index = 0;

    fd = open(filename, O_RDONLY);
    assert(fd >= 0 && "Cannot open ELF file");
    assert(fstat(fd, &st) == 0);

    buf = (char *)mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    assert(buf != MAP_FAILED);
    close(fd);

    /* Check ELF magic */
    assert(st.st_size >= (long)sizeof(Elf64_Ehdr));
    assert(buf[0] == 0x7f && buf[1] == 'E' && buf[2] == 'L' && buf[3] == 'F');

    unsigned char ei_class = (unsigned char)buf[EI_CLASS];

    if (ei_class == ELFCLASS64) {
        Elf64_Ehdr *eh = (Elf64_Ehdr *)buf;
        Elf64_Phdr *ph = (Elf64_Phdr *)(buf + eh->e_phoff);
        for (i = 0; i < eh->e_phnum && num_sections < MAX_SECTIONS; i++) {
            if (ph[i].p_type == PT_LOAD && ph[i].p_filesz > 0) {
                sections[num_sections].address = ph[i].p_paddr;
                sections[num_sections].length  = ph[i].p_filesz;
                sections[num_sections].data    = (uint8_t *)malloc(ph[i].p_filesz);
                memcpy(sections[num_sections].data, buf + ph[i].p_offset, ph[i].p_filesz);
                num_sections++;
            }
        }
    } else if (ei_class == ELFCLASS32) {
        Elf32_Ehdr *eh = (Elf32_Ehdr *)buf;
        Elf32_Phdr *ph = (Elf32_Phdr *)(buf + eh->e_phoff);
        for (i = 0; i < eh->e_phnum && num_sections < MAX_SECTIONS; i++) {
            if (ph[i].p_type == PT_LOAD && ph[i].p_filesz > 0) {
                sections[num_sections].address = ph[i].p_paddr;
                sections[num_sections].length  = ph[i].p_filesz;
                sections[num_sections].data    = (uint8_t *)malloc(ph[i].p_filesz);
                memcpy(sections[num_sections].data, buf + ph[i].p_offset, ph[i].p_filesz);
                num_sections++;
            }
        }
    } else {
        assert(0 && "Unknown ELF class (not 32 or 64 bit)");
    }

    munmap(buf, st.st_size);
    fprintf(stderr, "[elfloader] Loaded %d LOAD segment(s) from %s\n",
            num_sections, filename);
}

/* ── get_section ─────────────────────────────────────────────────────────── */

char get_section(long long *address, long long *len) {
    if (section_index < num_sections) {
        *address = (long long)sections[section_index].address;
        *len     = (long long)sections[section_index].length;
        section_index++;
        return 1;
    }
    return 0;
}

/* ── read_section_sv ─────────────────────────────────────────────────────── */
/* SV calls:  read_section_sv(address, buffer)
 * where buffer is an inout dynamic byte array.
 * On the C side this arrives as an svOpenArrayHandle.
 */

void read_section_sv(long long address, const svOpenArrayHandle buffer) {
    void *buf_ptr = svGetArrayPtr(buffer);
    int i;
    assert(buf_ptr != NULL);

    /* Find the section with this address */
    for (i = 0; i < num_sections; i++) {
        if ((long long)sections[i].address == address) {
            memcpy(buf_ptr, sections[i].data, sections[i].length);
            return;
        }
    }
    /* If we get here, the section wasn't found — shouldn't happen */
    fprintf(stderr, "[elfloader] ERROR: section at address 0x%llx not found\n", address);
    assert(0);
}
