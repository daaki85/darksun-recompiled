/*
 * bios.c - the interrupt vector table, the BIOS services, the PIC and PIT,
 * port I/O, the mouse driver and the XMS driver.
 *
 * Every vector starts out pointing at F000:FE00+n, which dispatch.c answers
 * natively. When the game installs a handler of its own (INT 21h AH=25h, or
 * by writing the table), interrupts through that vector run the guest's code
 * instead, with a real FLAGS/CS/IP frame, and its `call far [old]` reaches
 * the native handler again. That is how a PC does it, and it keeps chaining
 * correct without knowing what the game hooks.
 */
#include "runtime.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

int g_recomp_tick_budget = 1000;

/* ---- interrupt vectors ---------------------------------------------------- */
static uint32_t ivt_get(CPU *cpu, int vec)
{
    return mem_read16(cpu, 0, (uint16_t)(vec * 4)) |
           ((uint32_t)mem_read16(cpu, 0, (uint16_t)(vec * 4 + 2)) << 16);
}

static int ivt_is_default(CPU *cpu, int vec)
{
    uint32_t v = ivt_get(cpu, vec);
    return (v >> 16) == BIOS_SEG && (v & 0xFFFF) == BIOS_VEC_OFF + (unsigned)vec;
}

static int g_in_irq;

void run_guest_interrupt(CPU *cpu, int vec)
{
    if (ivt_is_default(cpu, vec)) { bios_service(cpu, vec); return; }
    uint32_t v = ivt_get(cpu, vec);
    /* The frame carries CS:IP as the code keeps them: the mod's helper reads
     * the byte after the INT through it and moves it to send the game on
     * (tools/lift.py sets them before each such INT). The lifted iret pops
     * them back into cpu->cs:ip and returns to C. */
    push16(cpu, cpu->flags);
    push16(cpu, cpu->cs);
    push16(cpu, cpu->ip);
    cpu->flags &= ~(FLAG_IF | FLAG_TF);
    uint16_t sp = cpu->sp;
    static int watch = -2;                     /* DS_TRACE_INT=<vector hex>: registers around each one */
    if (watch == -2) { const char *w = getenv("DS_TRACE_INT"); watch = !w ? -1 : !strcmp(w, "all") ? -3 : (int)strtol(w, NULL, 16); }
    int watched = vec == watch || (watch == -3 && vec >= 0x60);   /* "all": every user vector (the mod's) */
    if (watched)
        fprintf(stderr, "[int %02X] in  cs:ip=%04X:%04X ds=%04X ss:sp=%04X:%04X ax=%04X bx=%04X [ds:9C]=%04X above=%04X:%04X\n", vec,
                cpu->cs, cpu->ip, cpu->ds, cpu->ss, cpu->sp, cpu->ax, cpu->bx, mem_read16(cpu, cpu->ds, 0x9C),
                mem_read16(cpu, cpu->ss, cpu->sp + 8), mem_read16(cpu, cpu->ss, cpu->sp + 6));   /* the far return address a handler standing in for a routine's start sees */
    g_in_int++;
    int ok = recomp_dispatch(cpu, v >> 16, v & 0xFFFF);
    g_in_int--;
    if (watched)
        fprintf(stderr, "[int %02X] out cs:ip=%04X:%04X ds=%04X ss:sp=%04X:%04X ax=%04X flags=%04X\n", vec,
                cpu->cs, cpu->ip, cpu->ds, cpu->ss, cpu->sp, cpu->ax, cpu->flags);
    if (!ok) {
        trace("[int] vector %02X -> %04X:%04X is not code\n", vec, v >> 16, v & 0xFFFF);
        cpu->sp = sp;
        cpu->sp += 4; cpu->flags = pop16(cpu);
    }
}
int g_in_int;

void int_handler(CPU *cpu, int vec)
{
    run_guest_interrupt(cpu, vec & 0xFF);
}

void dos_int21(CPU *cpu)  { int_handler(cpu, 0x21); }
void bios_int10(CPU *cpu) { int_handler(cpu, 0x10); }
void bios_int16(CPU *cpu) { int_handler(cpu, 0x16); }
void mouse_int33(CPU *cpu){ int_handler(cpu, 0x33); }

/* A hardware interrupt arrives between two instructions of whatever was
 * running: everything it changes it must put back, so make that so. */
static void hw_interrupt(CPU *cpu, int vec)
{
    CPU saved = *cpu;
    g_in_irq++;
    run_guest_interrupt(cpu, vec);
    g_in_irq--;
    uint8_t *mem = cpu->mem;
    *cpu = saved;
    cpu->mem = mem;
}

/* ---- PIC and PIT ------------------------------------------------------------ */
static uint8_t g_pic_mask, g_pic_mask2;
static volatile unsigned g_irq_pending;
static unsigned g_pit_div = 65536;
static uint64_t g_pit_last;
static int g_pit_latch_hi, g_pit_wlo, g_pit_mode;
static uint16_t g_pit_latch;
static uint16_t g_pit_load;
static uint8_t g_port61;
static unsigned long g_ticks_delivered;

void irq_raise(int irq) { __atomic_fetch_or(&g_irq_pending, 1u << irq, __ATOMIC_SEQ_CST); }

void pit_write(uint16_t port, uint8_t val)
{
    if (port == 0x43) {
        if ((val >> 6) == 0) {
            if (((val >> 4) & 3) == 0) {           /* counter latch */
                uint64_t el = host_us() - g_pit_last;
                unsigned d = g_pit_div;
                uint64_t cnt = (el * 1193182ull / 1000000ull) % d;
                g_pit_latch = (uint16_t)(d - cnt);
                g_pit_latch_hi = 0;
            } else {
                g_pit_mode = (val >> 1) & 7;
                g_pit_wlo = 1;
            }
        }
        return;
    }
    if (port == 0x40) {
        if (g_pit_wlo) { g_pit_load = val; g_pit_wlo = 0; }
        else {
            g_pit_load |= (uint16_t)val << 8; g_pit_wlo = 1;
            g_pit_div = g_pit_load ? g_pit_load : 65536;
            g_pit_last = host_us();
            trace("[pit] channel 0 divisor %u (%.1f Hz)\n", g_pit_div, 1193182.0 / g_pit_div);
        }
    }
}

uint8_t pit_read(uint16_t port)
{
    if (port != 0x40) return 0;
    uint8_t v = g_pit_latch_hi ? (uint8_t)(g_pit_latch >> 8) : (uint8_t)g_pit_latch;
    g_pit_latch_hi ^= 1;
    if (!g_pit_latch_hi) {                         /* next read pair re-latches */
        uint64_t el = host_us() - g_pit_last;
        g_pit_latch = (uint16_t)(g_pit_div - (el * 1193182ull / 1000000ull) % g_pit_div);
    }
    return v;
}

static void pit_update(void)
{
    uint64_t now = host_us();
    if (!g_pit_last) g_pit_last = now;
    uint64_t period = (uint64_t)g_pit_div * 1000000ull / 1193182ull;
    if (period == 0) period = 1;
    if (now - g_pit_last >= period) {
        uint64_t n = (now - g_pit_last) / period;
        g_pit_last += n * period;
        if (now - g_pit_last > 100000) g_pit_last = now;   /* do not catch up forever */
        irq_raise(0);
    }
}

void mouse_poll(CPU *cpu);
void kbd_irq(CPU *cpu);

void irq_poll(CPU *cpu)
{
    pit_update();
    if (g_in_irq || !(cpu->flags & FLAG_IF)) return;
    for (int irq = 0; irq < 8; irq++) {
        unsigned bit = 1u << irq;
        if (!(g_irq_pending & bit) || (g_pic_mask & bit)) continue;
        __atomic_fetch_and(&g_irq_pending, ~bit, __ATOMIC_SEQ_CST);
        if (irq == 0) { g_ticks_delivered++; hw_interrupt(cpu, 0x08); }
        else if (irq == 1) kbd_irq(cpu);
        else hw_interrupt(cpu, 0x08 + irq);
    }
    mouse_poll(cpu);
}

volatile int g_want_backtrace;

void recomp_tick(CPU *cpu)
{
    g_recomp_tick_budget = 2000;
    if (g_want_backtrace) {
        extern void dispatch_backtrace(void);
        g_want_backtrace = 0;
        trace("[tick] the game is in:\n");
        dispatch_backtrace();
    }
    irq_poll(cpu);
}

/* ---- keyboard ---------------------------------------------------------------- */
static uint8_t g_port60;

void kbd_irq(CPU *cpu)
{
    g_port60 = host_scancode();
    g_in_irq++;
    {
        CPU saved = *cpu;
        run_guest_interrupt(cpu, 0x09);
        uint8_t *mem = cpu->mem; *cpu = saved; cpu->mem = mem;
    }
    g_in_irq--;
}

/* ---- ports ---------------------------------------------------------------------- */
int opl_port_in(uint16_t port, uint8_t *v);
int opl_port_out(uint16_t port, uint8_t v);
int sb_port_in(uint16_t port, uint8_t *v);
int sb_port_out(uint16_t port, uint8_t v);

uint8_t port_in8(CPU *cpu, uint16_t port)
{
    (void)cpu;
    if (port >= 0x3B0 && port <= 0x3DF) return vga_port_in(port);
    { uint8_t v; if (opl_port_in(port, &v)) return v; if (sb_port_in(port, &v)) return v; }
    switch (port) {
    case 0x20: return 0;
    case 0x21: return g_pic_mask;
    case 0xA1: return g_pic_mask2;
    case 0x40: return pit_read(port);
    case 0x60: return g_port60;
    case 0x61: return g_port61 ^= 0x10;          /* refresh toggle */
    case 0x64: return 0x14;
    case 0x201: return 0xFF;                      /* no joystick */
    }
    { static int n; if (n++ < 40) trace("[port] in %03X: nothing there\n", port); }
    return 0xFF;                                  /* nothing there: no sound card */
}

void port_out8(CPU *cpu, uint16_t port, uint8_t val)
{
    (void)cpu;
    if (port >= 0x3B0 && port <= 0x3DF) { vga_port_out(port, val); return; }
    if (opl_port_out(port, val)) return;
    if (sb_port_out(port, val)) return;
    switch (port) {
    case 0x20: case 0xA0: return;                 /* EOI */
    case 0x21: g_pic_mask = val; return;
    case 0xA1: g_pic_mask2 = val; return;
    case 0x40: case 0x41: case 0x42: case 0x43: pit_write(port, val); return;
    case 0x61: g_port61 = val; return;
    }
    { static int n; if (n++ < 40) trace("[port] out %03X %02X: nothing there\n", port, val); }
}

uint16_t port_in16(CPU *cpu, uint16_t port)
{
    return port_in8(cpu, port) | ((uint16_t)port_in8(cpu, (uint16_t)(port + 1)) << 8);
}

void port_out16(CPU *cpu, uint16_t port, uint16_t val)
{
    port_out8(cpu, port, (uint8_t)val);
    port_out8(cpu, (uint16_t)(port + 1), (uint8_t)(val >> 8));
}

/* ---- BIOS data area --------------------------------------------------------------- */
#define BDA(o) (0x400 + (o))

void bios_init(CPU *cpu)
{
    for (int v = 0; v < 256; v++) {
        mem_write16(cpu, 0, (uint16_t)(v * 4), (uint16_t)(BIOS_VEC_OFF + v));
        mem_write16(cpu, 0, (uint16_t)(v * 4 + 2), BIOS_SEG);
        cpu->mem[BIOS_LIN(BIOS_VEC_OFF) + v] = 0xCF;     /* iret, for anyone who looks */
    }
    /* Marks the mod's Loader can find this memory by: DOSBox's BIOS date at
     * F000:FFF5 (the helper's ring, in the HMA, overwrites it) and our own
     * name at F000:FFC0, which stays. */
    memcpy(cpu->mem + 0xFFFF5, "01/01/92", 8);
    memcpy(cpu->mem + 0xFFFC0, "DARKSUN-RECOMPILED", 19);
    cpu->mem[BIOS_LIN(XMS_ENTRY_OFF)] = 0xCB;            /* retf */
    uint8_t *m = cpu->mem;
    m[BDA(0x10)] = 0x26; m[BDA(0x11)] = 0x00;            /* equipment: VGA, mouse port */
    m[BDA(0x13)] = 0x80; m[BDA(0x14)] = 0x02;            /* 640 KB */
    m[BDA(0x49)] = 0x03;                                 /* video mode */
    m[BDA(0x4A)] = 80;
    m[BDA(0x84)] = 24;
    m[BDA(0x63)] = 0xD4; m[BDA(0x64)] = 0x03;            /* CRTC at 3D4 */
    memcpy(&m[0xFFFF5], "01/01/92", 8);
    m[0xFFFFE] = 0xFC;                                   /* an AT */
}

static void bda_tick(CPU *cpu)
{
    uint32_t t = mem_read16(cpu, 0x40, 0x6C) | ((uint32_t)mem_read16(cpu, 0x40, 0x6E) << 16);
    t++;
    if (t >= 0x1800B0) { t = 0; cpu->mem[BDA(0x70)] = 1; }
    mem_write16(cpu, 0x40, 0x6C, (uint16_t)t);
    mem_write16(cpu, 0x40, 0x6E, (uint16_t)(t >> 16));
}

static void set_cf(CPU *cpu, int on)
{
    if (on) cpu->flags |= FLAG_CF; else cpu->flags &= ~FLAG_CF;
}

static void int10(CPU *cpu)
{
    switch (cpu->ah) {
    case 0x00: vga_set_mode(cpu, cpu->al & 0x7F); cpu->mem[BDA(0x49)] = cpu->al & 0x7F; break;
    case 0x0F: cpu->al = (uint8_t)vga_mode(); cpu->ah = 80; cpu->bh = 0; break;
    case 0x10:
        if (cpu->al == 0x10) {
            vga_port_out(0x3C8, cpu->bl); vga_port_out(0x3C9, cpu->dh);
            vga_port_out(0x3C9, cpu->ch); vga_port_out(0x3C9, cpu->cl);
        } else if (cpu->al == 0x12) {
            vga_port_out(0x3C8, cpu->bl);
            for (unsigned i = 0; i < cpu->cx * 3u; i++)
                vga_port_out(0x3C9, mem_read8(cpu, cpu->es, (uint16_t)(cpu->dx + i)));
        } else if (cpu->al == 0x15) {
            vga_port_out(0x3C7, cpu->bl);
            cpu->dh = vga_port_in(0x3C9); cpu->ch = vga_port_in(0x3C9); cpu->cl = vga_port_in(0x3C9);
        } else if (cpu->al == 0x17) {
            vga_port_out(0x3C7, cpu->bl);
            for (unsigned i = 0; i < cpu->cx * 3u; i++)
                mem_write8(cpu, cpu->es, (uint16_t)(cpu->dx + i), vga_port_in(0x3C9));
        }
        break;
    case 0x0E: fputc(cpu->al, stderr); break;
    case 0x12: if (cpu->bl == 0x10) { cpu->bh = 0; cpu->bl = 3; cpu->cx = 0; } break;
    case 0x1A: if (cpu->al == 0) { cpu->al = 0x1A; cpu->bx = 0x0008; } break;
    case 0x4F: cpu->ax = 0x0100; break;          /* no VESA */
    case 0x03: cpu->dx = 0; cpu->cx = 0x0607; break;
    default: break;
    }
}

static void int16(CPU *cpu)
{
    uint16_t w;
    switch (cpu->ah) {
    case 0x00: case 0x10:
        while (!host_key_pop(&w, 0)) { irq_poll(cpu); host_sleep_us(2000); }
        cpu->ax = w;
        break;
    case 0x01: case 0x11:
        if (host_key_pop(&w, 1)) { cpu->ax = w; cpu->flags &= ~FLAG_ZF; }
        else cpu->flags |= FLAG_ZF;
        break;
    case 0x02: case 0x12: cpu->al = cpu->mem[BDA(0x17)]; break;
    default: break;
    }
}

static void int2f(CPU *cpu)
{
    if (cpu->ax == 0x4300) { cpu->al = 0x80; return; }           /* XMS present */
    if (cpu->ax == 0x4310) { cpu->es = BIOS_SEG; cpu->bx = XMS_ENTRY_OFF; return; }
    extern const char *g_cd_dir;
    if (cpu->ax == 0x1500) { cpu->bx = g_cd_dir ? 1 : 0; cpu->cx = 3; return; }   /* MSCDEX: one drive, D: */
    if (cpu->ax == 0x150B) { cpu->ax = (g_cd_dir && cpu->cx == 3) ? 0x0100 : 0; cpu->bx = 0xADAD; return; }
    if (cpu->ax == 0x150C) { cpu->bx = 0x0215; return; }         /* MSCDEX 2.21 */
    if (cpu->ax == 0x150D) { if (g_cd_dir) mem_write8(cpu, cpu->es, cpu->bx, 3); return; }
    if (cpu->ax == 0x1600) { cpu->al = 0; return; }              /* not Windows */
    if (cpu->ax == 0x1510 && g_cd_dir && cpu->cx == 3) {       /* send a device request to D: */
        extern void cd_device_request(CPU *);
        cd_device_request(cpu);
        set_cf(cpu, 0);
        return;
    }
    if (cpu->ah == 0x15) { set_cf(cpu, 1); cpu->ax = 1; return; }  /* other MSCDEX calls: not there */
}

void bios_service(CPU *cpu, int vec)
{
    switch (vec) {
    case 0x08: bda_tick(cpu); run_guest_interrupt(cpu, 0x1C); break;
    case 0x09: {
        /* The host already queued the BIOS word with the scancode; keep the
         * shift state at 0040:0017 (right shift, left shift, ctrl, alt), which
         * programs poll through INT 16h AH=02 -- Wake of the Ravager's intro
         * skips while a Shift key is down. */
        uint8_t sc = g_port60 & 0x7F, bit = 0;
        if (sc == 0x36) bit = 1; else if (sc == 0x2A) bit = 2; else if (sc == 0x1D) bit = 4; else if (sc == 0x38) bit = 8;
        if (bit) { if (g_port60 & 0x80) cpu->mem[BDA(0x17)] &= ~bit; else cpu->mem[BDA(0x17)] |= bit; }
        extern void host_key_commit(void);
        host_key_commit();
        break; }
    case 0x10: int10(cpu); break;
    case 0x11: cpu->ax = mem_read16(cpu, 0x40, 0x10); break;
    case 0x12: cpu->ax = 640; break;
    case 0x15:
        if (cpu->ah == 0x86) { host_sleep_us(((uint32_t)cpu->cx << 16 | cpu->dx)); set_cf(cpu, 0); }
        else if (cpu->ah == 0x88) { cpu->ax = 0; set_cf(cpu, 0); }
        else { cpu->ah = 0x86; set_cf(cpu, 1); }
        break;
    case 0x16: int16(cpu); break;
    case 0x1A:
        if (cpu->ah == 0) {
            cpu->cx = mem_read16(cpu, 0x40, 0x6E); cpu->dx = mem_read16(cpu, 0x40, 0x6C);
            cpu->al = cpu->mem[BDA(0x70)]; cpu->mem[BDA(0x70)] = 0;
        } else set_cf(cpu, 1);
        break;
    case 0x21: dos_service(cpu); break;
    case 0x2F: int2f(cpu); break;
    case 0x33: mouse_service(cpu); break;
    case 0x67: cpu->ah = 0x80; break;            /* no EMS */
    case 0x1C: case 0x1B: case 0x23: case 0x28: break;
    case 0x24: cpu->al = 3; break;               /* critical error: fail */
    default:
        trace("[int] unhandled INT %02Xh AX=%04X\n", vec, cpu->ax);
        break;
    }
}

/* ---- mouse driver (INT 33h) ---------------------------------------------------------- */
static int g_mx_min, g_mx_max = 639, g_my_min, g_my_max = 199;
static uint16_t g_mhandler_mask, g_mhandler_seg, g_mhandler_off;
static int g_mouse_last_x = -1, g_mouse_last_y = -1, g_mouse_last_b;
static int g_press_count[3], g_release_count[3];
static int g_mouse_shown;

static void mouse_pos(int *x, int *y, int *b)
{
    host_mouse(x, y, b);
    *x = g_mx_min + *x * (g_mx_max - g_mx_min + 1) / 320;
    *y = g_my_min + *y * (g_my_max - g_my_min + 1) / 200;
}

void mouse_service(CPU *cpu)
{
    int x, y, b;
    switch (cpu->ax) {
    case 0x00: cpu->ax = 0xFFFF; cpu->bx = 2; g_mhandler_mask = 0; g_mouse_shown = 0; break;
    case 0x01: g_mouse_shown++; break;
    case 0x02: g_mouse_shown--; break;
    case 0x03: mouse_pos(&x, &y, &b); cpu->bx = (uint16_t)b; cpu->cx = (uint16_t)x; cpu->dx = (uint16_t)y; break;
    case 0x04: host_mouse_set((cpu->cx - g_mx_min) * 320 / (g_mx_max - g_mx_min + 1),
                              (cpu->dx - g_my_min) * 200 / (g_my_max - g_my_min + 1)); break;
    case 0x05: case 0x06: {
        int k = cpu->bx < 3 ? cpu->bx : 0;
        mouse_pos(&x, &y, &b);
        cpu->ax = (uint16_t)b;
        cpu->bx = (uint16_t)(cpu->ax == 5 ? g_press_count[k] : g_release_count[k]);
        if (cpu->ax == 5) g_press_count[k] = 0; else g_release_count[k] = 0;
        cpu->cx = (uint16_t)x; cpu->dx = (uint16_t)y;
        break; }
    case 0x07: g_mx_min = cpu->cx; g_mx_max = cpu->dx; break;
    case 0x08: g_my_min = cpu->cx; g_my_max = cpu->dx; break;
    case 0x0C: g_mhandler_mask = cpu->cx; g_mhandler_seg = cpu->es; g_mhandler_off = cpu->dx;
               trace("[mouse] handler %04X:%04X mask %02X\n", cpu->es, cpu->dx, cpu->cx); break;
    case 0x14: { uint16_t m = g_mhandler_mask, s = g_mhandler_seg, o = g_mhandler_off;
                 g_mhandler_mask = cpu->cx; g_mhandler_seg = cpu->es; g_mhandler_off = cpu->dx;
                 cpu->cx = m; cpu->es = s; cpu->dx = o; break; }
    case 0x0F: case 0x1A: case 0x1D: case 0x0A: case 0x10: break;
    case 0x15: cpu->bx = 64; break;
    case 0x21: cpu->ax = 0xFFFF; cpu->bx = 2; break;
    case 0x24: cpu->bx = 0x0626; cpu->ch = 4; cpu->cl = 0; break;
    default: trace("[mouse] unhandled function %04X\n", cpu->ax); break;
    }
}

void mouse_poll(CPU *cpu)
{
    int x, y, b;
    mouse_pos(&x, &y, &b);
    int ev = 0;
    if (x != g_mouse_last_x || y != g_mouse_last_y) ev |= 1;
    for (int k = 0; k < 2; k++) {
        int was = (g_mouse_last_b >> k) & 1, is = (b >> k) & 1;
        if (is && !was) { ev |= 2 << (2 * k); g_press_count[k]++; }
        if (!is && was) { ev |= 4 << (2 * k); g_release_count[k]++; }
    }
    g_mouse_last_x = x; g_mouse_last_y = y; g_mouse_last_b = b;
    if (!(ev & g_mhandler_mask) || !g_mhandler_seg) return;
    CPU saved = *cpu;
    g_in_irq++;
    cpu->ax = (uint16_t)(ev & g_mhandler_mask); cpu->bx = (uint16_t)b;
    cpu->cx = (uint16_t)x; cpu->dx = (uint16_t)y;
    cpu->si = 0; cpu->di = 0;
    push16(cpu, BIOS_SEG); push16(cpu, 0xFFFF);
    if (!recomp_dispatch(cpu, g_mhandler_seg, g_mhandler_off)) cpu->sp += 4;
    g_in_irq--;
    uint8_t *mem = cpu->mem; *cpu = saved; cpu->mem = mem;
}

/* ---- XMS driver ------------------------------------------------------------------ */
#define XMS_KB (16 * 1024)
#define XMS_HANDLES 64
static struct { uint32_t kb; uint8_t *mem; int locks; int used; } g_xms[XMS_HANDLES];
static unsigned g_xms_used_kb;

static uint8_t *xms_ptr(CPU *cpu, uint16_t h, uint32_t off, uint32_t len)
{
    if (h == 0) {                                 /* conventional seg:off */
        uint32_t lin = ((off >> 16) << 4) + (off & 0xFFFF);
        return lin + len <= MEM_SIZE ? cpu->mem + lin : NULL;
    }
    if (h >= XMS_HANDLES || !g_xms[h].used) return NULL;
    if (off + len > g_xms[h].kb * 1024u) return NULL;
    return g_xms[h].mem + off;
}

void xms_service(CPU *cpu)
{
    static int quiet = -1;
    if (quiet < 0) quiet = getenv("DS_TRACE_XMS") == NULL;
    if (!quiet) trace("[xms] AH=%02X BX=%04X DX=%04X\n", cpu->ah, cpu->bx, cpu->dx);
    switch (cpu->ah) {
    case 0x00: cpu->ax = 0x0300; cpu->bx = 0x0300; cpu->dx = 1; break;
    case 0x03: case 0x04: case 0x05: case 0x06: cpu->ax = 1; cpu->bl = 0; break;
    case 0x07: cpu->ax = 1; cpu->bl = 0; break;
    case 0x08: {
        unsigned freek = XMS_KB - g_xms_used_kb;
        cpu->ax = (uint16_t)freek; cpu->dx = (uint16_t)freek; cpu->bl = 0;
        break; }
    case 0x09: {
        unsigned kb = cpu->dx;
        if (g_xms_used_kb + kb > XMS_KB) { cpu->ax = 0; cpu->bl = 0xA0; break; }
        for (int h = 1; h < XMS_HANDLES; h++) if (!g_xms[h].used) {
            g_xms[h].used = 1; g_xms[h].kb = kb; g_xms[h].locks = 0;
            g_xms[h].mem = calloc(kb ? kb : 1, 1024);
            g_xms_used_kb += kb;
            cpu->ax = 1; cpu->dx = (uint16_t)h;
            trace("[xms] allocated %u KB as handle %d\n", kb, h);
            return;
        }
        cpu->ax = 0; cpu->bl = 0xA1;
        break; }
    case 0x0A: {
        uint16_t h = cpu->dx;
        if (h && h < XMS_HANDLES && g_xms[h].used) {
            free(g_xms[h].mem); g_xms_used_kb -= g_xms[h].kb; memset(&g_xms[h], 0, sizeof g_xms[h]);
            cpu->ax = 1;
        } else { cpu->ax = 0; cpu->bl = 0xA2; }
        break; }
    case 0x0B: {
        uint16_t si = cpu->si, ds = cpu->ds;
        uint32_t len = mem_read32(cpu, ds, si);
        uint16_t sh = mem_read16(cpu, ds, (uint16_t)(si + 4));
        uint32_t so = mem_read32(cpu, ds, (uint16_t)(si + 6));
        uint16_t dh = mem_read16(cpu, ds, (uint16_t)(si + 10));
        uint32_t dof = mem_read32(cpu, ds, (uint16_t)(si + 12));
        uint8_t *s = xms_ptr(cpu, sh, so, len), *d = xms_ptr(cpu, dh, dof, len);
        if (!s || !d || (len & 1)) { cpu->ax = 0; cpu->bl = 0xA7; break; }
        memmove(d, s, len);
        cpu->ax = 1;
        break; }
    case 0x0C: cpu->ax = 0; cpu->bl = 0xA4; break;     /* no locking to linear */
    case 0x0D: cpu->ax = 1; break;
    case 0x0E: {
        uint16_t h = cpu->dx;
        if (h && h < XMS_HANDLES && g_xms[h].used) {
            cpu->ax = 1; cpu->bh = (uint8_t)g_xms[h].locks; cpu->bl = 32; cpu->dx = (uint16_t)g_xms[h].kb;
        } else { cpu->ax = 0; cpu->bl = 0xA2; }
        break; }
    case 0x0F: {
        uint16_t h = cpu->dx; unsigned kb = cpu->bx;
        if (!h || h >= XMS_HANDLES || !g_xms[h].used) { cpu->ax = 0; cpu->bl = 0xA2; break; }
        uint8_t *n = realloc(g_xms[h].mem, (kb ? kb : 1) * 1024u);
        if (kb > g_xms[h].kb) memset(n + g_xms[h].kb * 1024u, 0, (kb - g_xms[h].kb) * 1024u);
        g_xms_used_kb += kb - g_xms[h].kb;
        g_xms[h].mem = n; g_xms[h].kb = kb; cpu->ax = 1;
        break; }
    case 0x10: cpu->ax = 0; cpu->bl = 0xB1; cpu->dx = 0; break;   /* no UMBs */
    default:
        trace("[xms] unhandled function %02X\n", cpu->ah);
        cpu->ax = 0; cpu->bl = 0x80;
        break;
    }
}
