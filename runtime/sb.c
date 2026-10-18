/*
 * sb.c - a Sound Blaster Pro's digital side: the DSP at 22xh, DMA channel 1
 * on the 8237, IRQ 5, and the samples it plays, mixed by audio.c.
 *
 * The translated digital driver (AIL's SBPDIG) resets the DSP and expects
 * AAh back, asks its version, sends F2h to find its IRQ, sets the time
 * constant, and plays 8-bit unsigned PCM from a DMA buffer in auto-init mode
 * (block size with 48h, start with 1Ch), taking an interrupt at the end of
 * every block to refill the half just played. All of that is here; the DMA
 * buffer is read straight from guest memory as the audio clock consumes it.
 */
#include "runtime.h"
#include <string.h>

#define SB_BASE 0x220
#define SB_IRQ  5
#define SB_DMA  1

static struct {
    int reset_state;             /* 1 after a 1 written to 226h */
    uint8_t cmd[8]; int cmd_n, cmd_need;
    uint8_t out[8]; int out_r, out_w;
    int speaker;
    uint8_t tc;                  /* time constant: rate = 1e6 / (256 - tc) */
    unsigned block;              /* DSP block length, bytes (as set by 48h/14h) - 1 */
    unsigned block_left;
    int playing, autoinit, paused;
    int irq_pending;
} dsp;

static struct {
    uint16_t base[4], count[4];  /* as programmed */
    uint32_t cur[4]; int32_t left[4];
    uint8_t page[4], mode[4], mask, flipflop;
} dma;

static double g_pos;             /* fractional sample position in the DMA stream */
static int g_last;               /* the last sample taken (for holding) */

static void dsp_out(uint8_t v) { dsp.out[dsp.out_w++ & 7] = v; }

static void dma_reload(int ch)
{
    dma.cur[ch] = ((uint32_t)dma.page[ch] << 16) | dma.base[ch];
    dma.left[ch] = (int32_t)dma.count[ch] + 1;
}

static void start_play(int autoinit)
{
    dsp.playing = 1; dsp.autoinit = autoinit; dsp.paused = 0;
    dsp.block_left = dsp.block + 1;
    trace("[sb] play %s, block %u, %u Hz, DMA %05X x %d\n", autoinit ? "auto-init" : "single",
          dsp.block + 1, 1000000u / (256u - dsp.tc), dma.cur[SB_DMA], dma.left[SB_DMA]);
}

static void dsp_command(uint8_t v)
{
    if (dsp.cmd_n == 0) {
        dsp.cmd[0] = v; dsp.cmd_n = 1;
        switch (v) {
        case 0x10: case 0x40: case 0xE4: dsp.cmd_need = 2; return;     /* one data byte */
        case 0x14: case 0x16: case 0x17: case 0x48: case 0x74: case 0x75:
        case 0x76: case 0x77: case 0x80: dsp.cmd_need = 3; return;     /* two */
        default: dsp.cmd_need = 1; break;
        }
    } else {
        dsp.cmd[dsp.cmd_n++] = v;
        if (dsp.cmd_n < dsp.cmd_need) return;
    }
    uint8_t c = dsp.cmd[0];
    unsigned len = dsp.cmd_n >= 3 ? (unsigned)dsp.cmd[1] | ((unsigned)dsp.cmd[2] << 8) : 0;
    dsp.cmd_n = 0;
    switch (c) {
    case 0xE1: dsp_out(3); dsp_out(2); break;            /* DSP 3.02: a Sound Blaster Pro 2 */
    case 0xE0: dsp_out((uint8_t)~dsp.cmd[1]); break;
    case 0xE3: for (const char *p = "COPYRIGHT (C) CREATIVE TECHNOLOGY LTD, 1992."; *p; p++) dsp_out((uint8_t)*p); dsp_out(0); break;
    case 0xD1: dsp.speaker = 1; break;
    case 0xD3: dsp.speaker = 0; break;
    case 0xD8: dsp_out(dsp.speaker ? 0xFF : 0); break;
    case 0x40: dsp.tc = dsp.cmd[1]; break;
    case 0x48: dsp.block = len; break;
    case 0x14: dsp.block = len; start_play(0); break;
    case 0x1C: case 0x90: start_play(1); break;
    case 0xD0: dsp.paused = 1; break;
    case 0xD4: dsp.paused = 0; break;
    case 0xDA: dsp.autoinit = 0; break;                  /* stop at the end of this block */
    case 0xF2: dsp.irq_pending = 1; irq_raise(SB_IRQ); break;
    case 0x10: g_last = ((int)dsp.cmd[1] - 128) << 6; break;   /* direct DAC */
    default: trace("[sb] DSP command %02X\n", c); break;
    }
}

int sb_port_in(uint16_t port, uint8_t *v)
{
    if (port >= 0x00 && port <= 0x0F) {                   /* 8237 */
        if (port < 8) {
            int ch = port >> 1;
            uint16_t val = (port & 1) ? (uint16_t)(dma.left[ch] > 0 ? dma.left[ch] - 1 : 0xFFFF)
                                      : (uint16_t)dma.cur[ch];
            *v = dma.flipflop ? (uint8_t)(val >> 8) : (uint8_t)val;
            dma.flipflop ^= 1;
        } else if (port == 0x08) *v = 0;
        else *v = 0;
        return 1;
    }
    switch (port) {
    case SB_BASE + 0xA:                                   /* read data */
        *v = dsp.out_r != dsp.out_w ? dsp.out[dsp.out_r++ & 7] : 0xFF;
        return 1;
    case SB_BASE + 0xC: *v = 0x7F; return 1;              /* ready for a command */
    case SB_BASE + 0xE:                                   /* data available; reading acknowledges the IRQ */
        *v = (uint8_t)((dsp.out_r != dsp.out_w ? 0x80 : 0) | 0x7F);
        dsp.irq_pending = 0;
        return 1;
    case SB_BASE + 0xF: *v = 0xFF; dsp.irq_pending = 0; return 1;
    case SB_BASE + 0x6: *v = 0xFF; return 1;
    }
    return 0;
}

int sb_port_out(uint16_t port, uint8_t v)
{
    if (port <= 0x0F) {
        if (port < 8) {
            int ch = port >> 1;
            if (port & 1) { if (dma.flipflop) dma.count[ch] = (uint16_t)((dma.count[ch] & 0xFF) | (v << 8)); else dma.count[ch] = (uint16_t)((dma.count[ch] & 0xFF00) | v); }
            else          { if (dma.flipflop) dma.base[ch] = (uint16_t)((dma.base[ch] & 0xFF) | (v << 8)); else dma.base[ch] = (uint16_t)((dma.base[ch] & 0xFF00) | v); }
            dma.flipflop ^= 1;
            dma_reload(ch);
        } else if (port == 0x0A) {                        /* single mask */
            if (v & 4) dma.mask |= (uint8_t)(1 << (v & 3)); else dma.mask &= (uint8_t)~(1 << (v & 3));
        } else if (port == 0x0B) dma.mode[v & 3] = v;
        else if (port == 0x0C) dma.flipflop = 0;
        else if (port == 0x0D) { memset(&dma, 0, sizeof dma); dma.mask = 0x0F; }
        else if (port == 0x0F) dma.mask = (uint8_t)(v & 0x0F);
        return 1;
    }
    if (port == 0x83 || port == 0x81 || port == 0x82 || port == 0x87) {
        static const int chan[] = { [0x87 - 0x80] = 0, [0x83 - 0x80] = 1, [0x81 - 0x80] = 2, [0x82 - 0x80] = 3 };
        int ch = chan[port - 0x80];
        dma.page[ch] = v;
        dma_reload(ch);
        return 1;
    }
    switch (port) {
    case SB_BASE + 0x6:
        if (v & 1) dsp.reset_state = 1;
        else if (dsp.reset_state) {
            dsp.reset_state = 0;
            memset(&dsp, 0, sizeof dsp);
            dsp_out(0xAA);
            g_last = 0;
        }
        return 1;
    case SB_BASE + 0xC: dsp_command(v); return 1;
    }
    return 0;
}

/* One output frame's worth of the DMA stream, at the audio clock's rate.
 * Returns a 16-bit sample (both channels alike) and advances the stream. */
int16_t sb_sample(unsigned out_rate)
{
    if (!dsp.playing || dsp.paused || (dma.mask & (1 << SB_DMA))) return (int16_t)(dsp.speaker ? g_last : 0);
    double rate = 1000000.0 / (256 - dsp.tc);
    g_pos += rate / out_rate;
    while (g_pos >= 1.0 && dsp.playing) {
        g_pos -= 1.0;
        if (dma.left[SB_DMA] <= 0) {
            if (dma.mode[SB_DMA] & 0x10) dma_reload(SB_DMA);     /* auto-initialize */
            else { dsp.playing = 0; g_last = 0; break; }
        }
        uint32_t a = dma.cur[SB_DMA] & 0xFFFFF;
        g_last = ((int)g_cpu->mem[a] - 128) << 6;
        dma.cur[SB_DMA] = (dma.cur[SB_DMA] & 0xF0000) | ((dma.cur[SB_DMA] + 1) & 0xFFFF);   /* a channel never crosses a page */
        dma.left[SB_DMA]--;
        if (--dsp.block_left == 0) {
            dsp.irq_pending = 1;
            irq_raise(SB_IRQ);
            if (dsp.autoinit) dsp.block_left = dsp.block + 1;
            else { dsp.playing = 0; g_last = 0; }      /* back to silence, not the last level */
        }
    }
    return (int16_t)(dsp.speaker ? g_last : 0);
}
