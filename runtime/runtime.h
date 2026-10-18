/*
 * runtime.h - what the recompiled game calls into, and what the runtime's
 * parts share.
 *
 * The lifted code (build/<game>/gen) runs against pcrecomp's CPU model
 * (cpu.h: registers, flat 1 MB + HMA memory, flags). It leaves the machine
 * through four doors: software interrupts, port I/O, calls and jumps through
 * addresses known only at run time, and the interrupt poll on loop back-edges.
 * The runtime is a small PC behind those doors: DOS, the BIOS, a VGA, the PIT
 * and PIC, a mouse driver and an XMS driver.
 */
#ifndef DS_RUNTIME_H
#define DS_RUNTIME_H

#define RECOMP_MEM_HOOK 1      /* the VGA's planes sit behind A000 */
#define RECOMP_IRQ 1           /* timer and keyboard interrupts */
#define RECOMP_TRACE 1         /* remember the last functions entered */

#include "cpu.h"
#include <stdint.h>
#include <stdio.h>

/* ---- calls the generated code makes -------------------------------------- */
void int_handler(CPU *cpu, int vec);
void dos_int21(CPU *cpu);
void bios_int10(CPU *cpu);
void bios_int16(CPU *cpu);
void mouse_int33(CPU *cpu);
uint8_t  port_in8(CPU *cpu, uint16_t port);
void     port_out8(CPU *cpu, uint16_t port, uint8_t val);
uint16_t port_in16(CPU *cpu, uint16_t port);
void     port_out16(CPU *cpu, uint16_t port, uint16_t val);
int  recomp_dispatch(CPU *cpu, unsigned seg, unsigned off);
void dispatch_near(CPU *cpu, unsigned seg, unsigned off);
void dispatch_far(CPU *cpu, unsigned seg, unsigned off);
void recomp_div0(const char *kind);
void recomp_missing(CPU *cpu, const char *name);
void recomp_unlifted(CPU *cpu, unsigned lin);

typedef void (*recomp_fn)(CPU *);
typedef struct { unsigned addr; recomp_fn fn; } DispEntry;

/* A translated Miles driver: recognised in memory by the CRC of its first
 * SIG_LEN bytes, its functions by offset (tools/lift_drivers.py). */
typedef struct { unsigned off; recomp_fn fn; } DrvEntry;
typedef struct { int id; uint32_t crc; unsigned size; const DrvEntry *fns; } DrvImage;
#define SIG_LEN 256
extern uint16_t g_drv_seg[64];

/* One translated game (tools/lift.py writes one of these per game). */
typedef struct {
    const char *tag, *title, *exe;
    unsigned exe_size;
    uint16_t psp, entry_cs, entry_ip, ss, sp;
    const DispEntry *dispatch; int ndispatch;
    const DrvImage *drivers; const int *ndrivers;
    const char *cd_sub;          /* folder under the game's with the CD's files, if it has a CD */
} GameDesc;
extern const GameDesc *g_game;                /* the one running */
extern const GameDesc *const g_games[];       /* the ones built in (games.c, written by CMake) */
extern const int g_ngames;

/* ---- the machine ---------------------------------------------------------- */
extern CPU *g_cpu;
extern const char *g_game_dir;

/* Native entry points the guest reaches by far call or through the IVT:
 * BIOS default interrupt handlers (one per vector) and the XMS driver. */
#define BIOS_SEG        0xF000u
#define BIOS_VEC_OFF    0xE000u          /* F000:E000 + vector */
#define XMS_ENTRY_OFF   0xF000u          /* F000:F000 */
#define BIOS_LIN(o)     ((BIOS_SEG << 4) + (o))

void dos_init(CPU *cpu);
void dos_service(CPU *cpu);
void bios_init(CPU *cpu);
void bios_service(CPU *cpu, int vec);
void xms_service(CPU *cpu);
void mouse_service(CPU *cpu);
void run_guest_interrupt(CPU *cpu, int vec);   /* through the IVT */

/* Interrupt controller and timer */
void irq_raise(int irq);
void pit_write(uint16_t port, uint8_t val);
uint8_t pit_read(uint16_t port);
void irq_poll(CPU *cpu);                         /* deliver what is pending */

/* VGA */
void vga_init(void);
uint8_t vga_port_in(uint16_t port);
void vga_port_out(uint16_t port, uint8_t val);
void vga_set_mode(CPU *cpu, int mode);
int  vga_mode(void);
void vga_render(uint32_t *rgba, int *w, int *h);   /* the screen as shown */
void vga_save_bmp(const char *path);
extern volatile unsigned long g_vga_frames;      /* retraces the game waited on */

/* The host: clock, window, input */
uint64_t host_us(void);
void host_sleep_us(unsigned us);
void host_key_event(uint8_t scancode, int down, uint16_t biosword);
int  host_key_pop(uint16_t *word, int peek);     /* BIOS keyboard buffer */
uint8_t host_scancode(void);                     /* port 60h */
void host_mouse(int *x, int *y, int *buttons);
void host_mouse_set(int x, int y);
int  host_headless(void);

void trace(const char *fmt, ...);
void fatal(const char *fmt, ...);

#endif
