/*
 * vga.c - a VGA, at the level of its registers and planes.
 *
 * Dark Sun draws in Mode X: mode 13h with chain-4 turned off, so video memory
 * is four 64 KB planes, a byte address names four pixels, and the Map Mask,
 * the write modes and the latches decide what a write does. Copies between
 * two places in video memory go through the latches (write mode 1), and the
 * page shown is the CRTC's start address. All of that is modelled; text modes
 * are not drawn.
 */
#include "runtime.h"
#include <stdlib.h>
#include <string.h>

static uint8_t g_plane[4][65536];
static uint8_t g_latch[4];
static uint8_t g_seq[8], g_seq_i;
static uint8_t g_gc[16], g_gc_i;
static uint8_t g_crtc[32], g_crtc_i;
static uint8_t g_attr[32], g_attr_i, g_attr_flip;
static uint8_t g_dac[256][3];
static uint8_t g_dac_w, g_dac_r, g_dac_c, g_dac_rc;
static uint8_t g_misc = 0x63;
static int g_mode = 3;
volatile unsigned long g_vga_frames;

void mem_watch_init(void);

void vga_init(void)
{
    mem_watch_init();
    memset(g_plane, 0, sizeof g_plane);
    g_seq[2] = 0x0F; g_seq[4] = 0x0E;
    g_gc[5] = 0x40; g_gc[6] = 0x05; g_gc[8] = 0xFF;
    g_crtc[0x13] = 40; g_crtc[0x09] = 0x41; g_crtc[0x14] = 0x40; g_crtc[0x17] = 0xA3;
    g_crtc[0x12] = 0x8F; g_crtc[0x07] = 0x1F;
    for (int i = 0; i < 256; i++) g_dac[i][0] = g_dac[i][1] = g_dac[i][2] = (uint8_t)(i >> 2);
}

void vga_set_mode(CPU *cpu, int mode)
{
    (void)cpu;
    g_mode = mode;
    trace("[vga] mode %02Xh\n", mode);
    vga_init();
    if (mode == 0x13) {
        g_seq[4] = 0x0E;            /* chain-4 */
        g_crtc[0x14] = 0x40;        /* doubleword */
        g_crtc[0x17] = 0xA3;
    }
}

int vga_mode(void) { return g_mode; }

static int chain4(void) { return (g_seq[4] & 0x08) != 0; }

/* ---- memory ------------------------------------------------------------------ */
static uint8_t alu(uint8_t v, uint8_t latch)
{
    switch ((g_gc[3] >> 3) & 3) {
    case 1: return v & latch;
    case 2: return v | latch;
    case 3: return v ^ latch;
    }
    return v;
}

static void planar_write(uint16_t a, uint8_t val)
{
    uint8_t mask = g_seq[2] & 0x0F;
    int wm = g_gc[5] & 3;
    if (wm == 1) {                                     /* latch copy */
        for (int p = 0; p < 4; p++) if (mask & (1 << p)) g_plane[p][a] = g_latch[p];
        return;
    }
    uint8_t bitmask = g_gc[8];
    int rot = g_gc[3] & 7;
    if (rot) val = (uint8_t)((val >> rot) | (val << (8 - rot)));
    for (int p = 0; p < 4; p++) {
        if (!(mask & (1 << p))) continue;
        uint8_t v;
        if (wm == 0) {
            v = (g_gc[1] & (1 << p)) ? ((g_gc[0] & (1 << p)) ? 0xFF : 0x00) : val;
            v = alu(v, g_latch[p]);
            v = (uint8_t)((v & bitmask) | (g_latch[p] & ~bitmask));
        } else if (wm == 2) {
            v = (val & (1 << p)) ? 0xFF : 0x00;
            v = alu(v, g_latch[p]);
            v = (uint8_t)((v & bitmask) | (g_latch[p] & ~bitmask));
        } else {
            uint8_t bm = (uint8_t)(val & bitmask);
            v = (g_gc[0] & (1 << p)) ? 0xFF : 0x00;
            v = (uint8_t)((v & bm) | (g_latch[p] & ~bm));
        }
        g_plane[p][a] = v;
    }
}

static uint8_t planar_read(uint16_t a)
{
    for (int p = 0; p < 4; p++) g_latch[p] = g_plane[p][a];
    if (g_gc[5] & 0x08) {                              /* colour compare */
        uint8_t r = 0;
        for (int bit = 0; bit < 8; bit++) {
            int match = 1;
            for (int p = 0; p < 4; p++) {
                if (!(g_gc[7] & (1 << p))) continue;
                if (((g_plane[p][a] >> bit) & 1) != ((g_gc[2] >> p) & 1)) match = 0;
            }
            if (match) r |= (uint8_t)(1 << bit);
        }
        return r;
    }
    return g_plane[g_gc[4] & 3][a];
}

/* DS_WATCH=<linear hex>: report writes to one address, with who made them */
static uint32_t g_watch = 0xFFFFFFFFu;
void mem_watch_init(void)
{
    const char *e = getenv("DS_WATCH");
    if (e) g_watch = (uint32_t)strtoul(e, NULL, 16);
}
extern void dispatch_backtrace(void);

int recomp_mem_write8(CPU *cpu, uint32_t addr, uint8_t val)
{
    (void)cpu;
    if ((addr & ~1u) == (g_watch & ~1u)) {
        trace("[watch] %05X <- %02X\n", addr, val);
        dispatch_backtrace();
    }
    if (addr < 0xA0000 || addr >= 0xB0000) return 0;
    uint16_t a = (uint16_t)(addr - 0xA0000);
    if (chain4()) { g_plane[a & 3][a >> 2] = val; return 1; }
    planar_write(a, val);
    return 1;
}

int recomp_mem_read8(CPU *cpu, uint32_t addr, uint8_t *out)
{
    (void)cpu;
    if (addr < 0xA0000 || addr >= 0xB0000) return 0;
    uint16_t a = (uint16_t)(addr - 0xA0000);
    if (chain4()) { *out = g_plane[a & 3][a >> 2]; return 1; }
    *out = planar_read(a);
    return 1;
}

/* ---- ports --------------------------------------------------------------------- */
uint8_t vga_port_in(uint16_t port)
{
    switch (port) {
    case 0x3C4: return g_seq_i;
    case 0x3C5: return g_seq[g_seq_i & 7];
    case 0x3CE: return g_gc_i;
    case 0x3CF: return g_gc[g_gc_i & 15];
    case 0x3D4: return g_crtc_i;
    case 0x3D5: return g_crtc[g_crtc_i & 31];
    case 0x3C0: return g_attr_i;
    case 0x3C1: return g_attr[g_attr_i & 31];
    case 0x3CC: return g_misc;
    case 0x3C7: return 0;
    case 0x3C8: return g_dac_w;
    case 0x3C9: {
        uint8_t v = g_dac[g_dac_r][g_dac_rc];
        if (++g_dac_rc == 3) { g_dac_rc = 0; g_dac_r++; }
        return v; }
    case 0x3DA: case 0x3BA: {
        /* 70 Hz: about 1.4 ms of each 14.3 ms frame is vertical retrace */
        uint64_t t = host_us() % 14286;
        uint8_t v = 0;
        if (t >= 12886) { v |= 0x09; }
        else if ((t % 32) < 6) v |= 0x01;          /* horizontal blanking */
        g_attr_flip = 0;
        static int was;
        if ((v & 8) && !was) g_vga_frames++;
        was = v & 8;
        return v; }
    }
    return 0xFF;
}

void vga_port_out(uint16_t port, uint8_t val)
{
    switch (port) {
    case 0x3C4: g_seq_i = val; break;
    case 0x3C5: g_seq[g_seq_i & 7] = val; break;
    case 0x3CE: g_gc_i = val; break;
    case 0x3CF: g_gc[g_gc_i & 15] = val; break;
    case 0x3D4: case 0x3B4: g_crtc_i = val; break;
    case 0x3D5: case 0x3B5: g_crtc[g_crtc_i & 31] = val; break;
    case 0x3C0:
        if (!g_attr_flip) g_attr_i = val; else g_attr[g_attr_i & 31] = val;
        g_attr_flip ^= 1; break;
    case 0x3C2: g_misc = val; break;
    case 0x3C7: g_dac_r = val; g_dac_rc = 0; break;
    case 0x3C8: g_dac_w = val; g_dac_c = 0; break;
    case 0x3C9:
        g_dac[g_dac_w][g_dac_c] = val & 0x3F;
        if (++g_dac_c == 3) { g_dac_c = 0; g_dac_w++; }
        break;
    }
}

/* ---- the picture ----------------------------------------------------------------- */
#include "font8x16.h"

/* Text mode (the character transfer utility runs in mode 3): 80x25 cells of
 * character and attribute at B800:0000, drawn 8x16 into 640x400 with the
 * CGA's sixteen colours; the cursor from the BIOS data area (0040:0050, its
 * shape at 0040:0060, bit 5 of the start line hiding it). */
static const uint32_t CGA[16] = {
    0xFF000000, 0xFF0000AA, 0xFF00AA00, 0xFF00AAAA, 0xFFAA0000, 0xFFAA00AA, 0xFFAA5500, 0xFFAAAAAA,
    0xFF555555, 0xFF5555FF, 0xFF55FF55, 0xFF55FFFF, 0xFFFF5555, 0xFFFF55FF, 0xFFFFFF55, 0xFFFFFFFF,
};

int vga_text_mode(void) { return g_mode <= 3 || g_mode == 7; }

static void render_text(uint32_t *rgba)
{
    const uint8_t *m = g_cpu->mem;
    extern uint8_t *bios_text_mem(CPU *);
    const uint8_t *cell = bios_text_mem(g_cpu);
    int cx = m[0x450], cy = m[0x451];
    int cur_start = m[0x461] & 0x1F, cur_end = m[0x460] & 0x1F, cur_on = !(m[0x461] & 0x20);
    for (int row = 0; row < 25; row++)
        for (int col = 0; col < 80; col++) {
            uint8_t ch = cell[(row * 80 + col) * 2], at = cell[(row * 80 + col) * 2 + 1];
            uint32_t fg = CGA[at & 15], bg = CGA[(at >> 4) & 7];
            const unsigned char *gl = FONT8X16[ch];
            for (int y = 0; y < 16; y++) {
                unsigned bits = gl[y];
                if (cur_on && row == cy && col == cx && y >= cur_start && y <= cur_end) bits = 0xFF;
                uint32_t *o = rgba + (row * 16 + y) * 640 + col * 8;
                for (int x = 0; x < 8; x++) o[x] = (bits & (0x80 >> x)) ? fg : bg;
            }
        }
}

void vga_render(uint32_t *rgba, int *w, int *h)
{
    int W = 320, H = 200;
    if (vga_text_mode()) { render_text(rgba); *w = 640; *h = 400; return; }
    unsigned start = ((unsigned)g_crtc[0x0C] << 8) | g_crtc[0x0D];
    unsigned pitch = g_crtc[0x13] * 2u;                 /* bytes per line, byte mode */
    unsigned vde = g_crtc[0x12] | ((g_crtc[0x07] & 0x02) << 7) | ((g_crtc[0x07] & 0x40) << 3);
    int dbl = (g_crtc[0x09] & 0x1F) + 1 + ((g_crtc[0x09] & 0x80) ? 1 : 0);
    if (vde) H = (int)(vde + 1) / (dbl > 0 ? dbl : 1);
    if (H > 240 || H < 100) H = 200;
    unsigned lc = g_crtc[0x18] | ((g_crtc[0x07] & 0x10) << 4) | ((g_crtc[0x09] & 0x40) << 3);
    int lc_line = (int)(lc + 1) / (dbl > 0 ? dbl : 1);
    uint32_t pal[256];
    for (int i = 0; i < 256; i++) {
        uint32_t r = g_dac[i][0] * 255u / 63, g = g_dac[i][1] * 255u / 63, b = g_dac[i][2] * 255u / 63;
        pal[i] = 0xFF000000u | (r << 16) | (g << 8) | b;
    }
    for (int y = 0; y < H; y++) {
        unsigned row = (y >= lc_line) ? (unsigned)(y - lc_line) * pitch : start + (unsigned)y * pitch;
        for (int x = 0; x < W; x++) {
            uint8_t c;
            if (chain4()) {
                unsigned o = (start * 4 + (unsigned)y * 320 + (unsigned)x) & 0xFFFF;
                c = g_plane[o & 3][(o >> 2) & 0xFFFF];
            } else {
                c = g_plane[x & 3][(row + (unsigned)(x >> 2)) & 0xFFFF];
            }
            rgba[y * W + x] = pal[c];
        }
    }
    *w = W; *h = H;
}

void vga_save_bmp(const char *path)
{
    static uint32_t px[640 * 400];
    int w, h;
    vga_render(px, &w, &h);
    FILE *f = fopen(path, "wb");
    if (!f) return;
    uint32_t sz = 54 + (uint32_t)(w * h * 3);
    uint8_t hd[54] = {'B', 'M'};
    memcpy(hd + 2, &sz, 4); hd[10] = 54; hd[14] = 40;
    int32_t ww = w, hh = -h; memcpy(hd + 18, &ww, 4); memcpy(hd + 22, &hh, 4);
    hd[26] = 1; hd[28] = 24;
    fwrite(hd, 1, 54, f);
    for (int i = 0; i < w * h; i++) {
        uint8_t b[3] = {(uint8_t)px[i], (uint8_t)(px[i] >> 8), (uint8_t)(px[i] >> 16)};
        fwrite(b, 1, 3, f);
    }
    fclose(f);
}
