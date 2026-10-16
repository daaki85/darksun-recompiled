/*
 * opl.c - the FM chip (YM3812 / YMF262) as the AIL drivers see it.
 *
 * Address and data ports at 388h-38Bh (AdLib) and 220h-223h / 228h-229h
 * (Sound Blaster Pro: left, right, both). The drivers find the chip by its
 * timers: reset the flags, start timer 1, wait, and expect the status register
 * to read C0h. The wait is a loop of port reads, each of which took about a
 * microsecond on the ISA bus, so the chip keeps its own clock: real time, plus
 * a microsecond for every access. Both timers and the status register are modelled; every
 * register write is kept (and counted) for the synthesiser that will turn
 * them into sound.
 */
#include "runtime.h"
#include <stdlib.h>
#include <string.h>
int opl_port_in_(uint16_t port, uint8_t *v);

static uint8_t g_reg[2][256];
static uint8_t g_index[2];
static uint64_t g_t1_start, g_t2_start;
static int g_t1_run, g_t2_run;
static uint8_t g_status_flags;
unsigned long g_opl_writes;

static uint64_t g_io_us;
static uint64_t now_us(void) { return host_us() + g_io_us; }

static uint8_t status(void)
{
    uint64_t now = now_us();
    if (g_t1_run && !(g_reg[0][4] & 0x40)) {
        unsigned period = (256 - g_reg[0][2]) * 80;
        if (now - g_t1_start >= period) g_status_flags |= 0x40;
    }
    if (g_t2_run && !(g_reg[0][4] & 0x20)) {
        unsigned period = (256 - g_reg[0][3]) * 320;
        if (now - g_t2_start >= period) g_status_flags |= 0x20;
    }
    uint8_t s = g_status_flags;
    if (s & 0x60) s |= 0x80;
    return s;                         /* low bits 0: an OPL3, as on a SB Pro 2 */
}

static void write_reg(int bank, uint8_t idx, uint8_t val)
{
    g_reg[bank][idx] = val;
    g_opl_writes++;
    if (bank == 0 && idx == 4) {
        if (val & 0x80) { g_status_flags = 0; return; }
        if ((val & 1) && !g_t1_run) g_t1_start = now_us();
        if ((val & 2) && !g_t2_run) g_t2_start = now_us();
        g_t1_run = val & 1; g_t2_run = (val >> 1) & 1;
    }
}

static int g_log = -1;
static void logio(const char *d, uint16_t port, uint8_t v)
{
    if (g_log < 0) g_log = getenv("DS_TRACE_OPL") ? 5000 : 0;
    if (g_log > 0) { g_log--; trace("[opl] %s %03X %02X\n", d, port, v); }
}

int opl_port_in(uint16_t port, uint8_t *v)
{
    int r = opl_port_in_(port, v);
    if (r) logio("in ", port, *v);
    return r;
}

/* The Sound Blaster Pro's mixer (CT1345) at 224h/225h. The FM driver checks
 * the card is a Pro by writing the microphone level (register 0Ah), of which
 * only bits 1-2 exist, and reading it back. */
static uint8_t g_mix_i, g_mix[256];

static uint8_t mixer_read(void)
{
    if (g_mix_i == 0x0A) return g_mix[0x0A] & 0x06;
    return g_mix[g_mix_i];
}

int opl_port_in_(uint16_t port, uint8_t *v)
{
    g_io_us++;
    if (port == 0x224) { *v = g_mix_i; return 1; }
    if (port == 0x225) { *v = mixer_read(); return 1; }
    switch (port) {
    case 0x388: case 0x220: case 0x222: case 0x228: *v = status(); return 1;
    case 0x389: case 0x38B: case 0x221: case 0x223: case 0x229: *v = 0xFF; return 1;
    case 0x38A: *v = 0; return 1;
    }
    return 0;
}

static int opl_port_out_(uint16_t port, uint8_t v);
int opl_port_out(uint16_t port, uint8_t v)
{
    int r = opl_port_out_(port, v);
    if (r) logio("out", port, v);
    return r;
}

static int opl_port_out_(uint16_t port, uint8_t v)
{
    g_io_us++;
    if (port == 0x224) { g_mix_i = v; return 1; }
    if (port == 0x225) { g_mix[g_mix_i] = v; if (g_mix_i == 0) memset(g_mix, 0, sizeof g_mix); return 1; }
    switch (port) {
    case 0x388: case 0x220: case 0x228: g_index[0] = v; return 1;
    case 0x38A: case 0x222: g_index[1] = v; return 1;
    case 0x389: case 0x221: case 0x229: write_reg(0, g_index[0], v); return 1;
    case 0x38B: case 0x223: write_reg(1, g_index[1], v); return 1;
    }
    return 0;
}
