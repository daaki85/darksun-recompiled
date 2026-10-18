/*
 * aildrv.c - calls into a Miles AIL 2 driver (.ADV) the game loaded.
 *
 * Dark Sun's sound library loads its drivers from RESOURCE.GFF into heap
 * memory and calls their functions by far call, so they are code no build
 * step saw. A driver image starts with the offset of its function table,
 * then "Copyright (C) 1991,1992 Miles Design, Inc."; the table pairs AIL
 * function numbers with offsets. A call that lands on one of those offsets
 * is answered here.
 *
 * For now the answer is a sound card that makes no sound: describe_driver
 * returns the driver's own description table (so the game reads what the file
 * says), detect_device succeeds (Dark Sun's sound library stops with "MIDI
 * Detect Fail" otherwise), and everything else does nothing and returns 0. Real sound is the
 * next step: either these drivers translated like the game, against emulated
 * hardware, or AIL 2.14's drivers in C (Exhume's runtime/port/sound, MIT).
 */
#include "runtime.h"
#include <string.h>

uint16_t g_drv_seg[64];

/* Drivers that run as translated code. The digital ones would need a Sound
 * Blaster DSP and its DMA, which the runtime does not have yet; they keep the
 * silent answers below. */
static int lifted_ok(int id)
{
    switch (id) {
    case 3: case 13: case 18: case 20: return 0;   /* PAS, AdLib Gold, GUS, Aria digital: no such cards here */
    }
    return 1;
}

/* CRC-32 (IEEE), the same polynomial zlib's crc32 and tools/lift_drivers.py use */
static uint32_t crc32_of(const uint8_t *p, size_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1)));
    }
    return ~c;
}

static const DrvImage *which_driver(CPU *cpu, uint32_t base)
{
    static uint32_t cache_base[8]; static const DrvImage *cache_img[8]; static int ncache;
    for (int i = 0; i < ncache; i++) if (cache_base[i] == base) return cache_img[i];
    if (base + SIG_LEN > 0xA0000) return NULL;
    uint32_t crc = crc32_of(cpu->mem + base, SIG_LEN);
    const DrvImage *drivers = g_game->drivers;
    for (int i = 0; i < *g_game->ndrivers; i++)
        if (drivers[i].crc == crc) {
            if (ncache < 8) { cache_base[ncache] = base; cache_img[ncache++] = &drivers[i]; }
            trace("[ail] ADV %d is loaded at %04X:0000\n", drivers[i].id, base >> 4);
            return &drivers[i];
        }
    return NULL;
}

/* how often each driver function ran, for the report at exit */
static struct { int id; unsigned off; unsigned long n; } g_calls[128];
static int g_ncalls;

static void ail_count(int id, unsigned off)
{
    for (int i = 0; i < g_ncalls; i++)
        if (g_calls[i].id == id && g_calls[i].off == off) { g_calls[i].n++; return; }
    if (g_ncalls < 128) { g_calls[g_ncalls].id = id; g_calls[g_ncalls].off = off; g_calls[g_ncalls++].n = 1; }
}

void ail_report(void)
{
    for (int i = 0; i < g_ncalls; i++)
        fprintf(stderr, "[ail] ADV %d +%04X ran %lu times\n", g_calls[i].id, g_calls[i].off, g_calls[i].n);
}

static int run_lifted(CPU *cpu, unsigned seg, unsigned off)
{
    const DrvImage *d = which_driver(cpu, (uint32_t)seg << 4);
    if (!d || !lifted_ok(d->id)) return 0;
    for (const DrvEntry *e = d->fns; e->fn; e++)
        if (e->off == off) {
            g_drv_seg[d->id] = (uint16_t)seg;
            uint16_t args[4];
            for (int k = 0; k < 4; k++) args[k] = mem_read16(cpu, cpu->ss, (uint16_t)(cpu->sp + 4 + 2 * k));
            e->fn(cpu);
            ail_count(d->id, off);
            static int logged;
            if (logged++ < 60)
                trace("[ail] ADV %d +%04X (%04X %04X %04X %04X) -> DX:AX %04X:%04X\n",
                      d->id, off, args[0], args[1], args[2], args[3], cpu->dx, cpu->ax);
            return 1;
        }
    trace("[ail] ADV %d has no function at %04X\n", d->id, off);
    return 0;
}

#define AIL_DESCRIBE_DRIVER 0x64
#define AIL_DETECT_DEVICE   0x65
#define AIL_TIMBRE_REQUEST  0x9B    /* next timbre the sequence needs; FFFF: none */

static int is_driver(CPU *cpu, uint32_t base)
{
    if (base + 0x40 >= 0xA0000 || memcmp(cpu->mem + base + 2, "Copyright (C) 199", 17)) return 0;
    for (int i = 2; i < 0x40 - 12; i++)                  /* MinGW has no memmem */
        if (!memcmp(cpu->mem + base + i, "Miles Design", 12)) return 1;
    return 0;
}

/* 1 if (seg, off) is a function of a loaded AIL driver, which is then done */
int ail_driver_call(CPU *cpu, unsigned seg, unsigned off)
{
    uint32_t base = (uint32_t)seg << 4;
    if (run_lifted(cpu, seg, off)) return 1;
    if (!is_driver(cpu, base)) return 0;
    uint16_t table = mem_read16(cpu, (uint16_t)seg, 0);
    int fn = -1;
    for (int i = 0; i < 64; i++) {
        uint16_t f = mem_read16(cpu, (uint16_t)seg, (uint16_t)(table + 4 * i));
        uint16_t o = mem_read16(cpu, (uint16_t)seg, (uint16_t)(table + 4 * i + 2));
        if (f == 0xFFFF) break;
        if (o == off) { fn = f; break; }
    }
    if (fn < 0) return 0;
    cpu->ax = 0; cpu->dx = 0;
    if (fn == AIL_DESCRIBE_DRIVER) {
        /* mov dx,cs / mov cs:[name_seg],dx / mov ax,OFFSET ddt */
        const uint8_t *p = cpu->mem + base + off;
        for (int k = 0; k < 24; k++)
            if (p[k] == 0x8C && p[k + 1] == 0xCA && p[k + 2] == 0x2E && p[k + 3] == 0x89 && p[k + 7] == 0xB8) {
                mem_write16(cpu, (uint16_t)seg, (uint16_t)(p[k + 5] | p[k + 6] << 8), (uint16_t)seg);
                cpu->ax = (uint16_t)(p[k + 8] | p[k + 9] << 8);
                cpu->dx = (uint16_t)seg;
                break;
            }
    }
    if (fn == AIL_DETECT_DEVICE) cpu->ax = 1;
    if (fn == AIL_TIMBRE_REQUEST) cpu->ax = 0xFFFF;
    static int logged;
    if (logged++ < 40)
        trace("[ail] driver %04X function %02X -> %04X:%04X\n", seg, fn, cpu->dx, cpu->ax);
    cpu->sp += 4;                                       /* its retf */
    return 1;
}
