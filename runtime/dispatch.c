/*
 * dispatch.c - calls and jumps through addresses known only at run time.
 *
 * The lifter turns every direct call into a C call. What is left -- function
 * pointers, `call far [vector]`, a far return that is really a jump -- comes
 * here with the guest's segment:offset, and is looked up by linear address in
 * the table lift.py generates. Two native areas sit beside the game's code:
 * the BIOS's default interrupt handlers and the XMS driver's entry point.
 *
 * Addresses no function covers are remembered and written to misses.txt on
 * exit; find_funcs.py turns them into entry points on the next build.
 */
#include "runtime.h"
#include <stdlib.h>
#include <string.h>
#ifdef __linux__
#include <execinfo.h>
#endif

#define RING 256
static const char *g_ring[RING];
static unsigned g_ring_i;
#define MAXMISS 4096
static unsigned g_miss[MAXMISS];
static int g_nmiss;
static int g_depth;

void dispatch_backtrace(void);

static int inside_function(unsigned lin);

static void note_miss(unsigned lin)
{
    unsigned stack = (g_cpu->ss & 0xFFFF) << 4;
    if (lin >= stack && lin < stack + 0x10000) return;   /* something built on the stack: not a function */
    /* With the mod's helper, a return into the middle of the game's code is
     * the helper sending the game on (recomp_return), not an entry point:
     * recorded, it would be lifted as a function and called as one. */
    if (g_game->tsr_cs && lin < 0xA0000 && inside_function(lin)) return;
    for (int i = 0; i < g_nmiss; i++)
        if (g_miss[i] == lin) return;
    if (g_nmiss < MAXMISS) g_miss[g_nmiss++] = lin;
    trace("[dispatch] no function at %05X (ds=%04X ss:sp=%04X:%04X)\n",
          lin, g_cpu->ds, g_cpu->ss, g_cpu->sp);
    if (g_nmiss <= 12) dispatch_backtrace();
    const char *dump = getenv("DS_DUMP");            /* DS_DUMP=<linear>:<bytes> shown at each miss */
    if (dump && g_nmiss <= 12) {
        unsigned at = (unsigned)strtoul(dump, NULL, 16), n = 32;
        const char *c = strchr(dump, ':');
        if (c) n = (unsigned)strtoul(c + 1, NULL, 0);
        fprintf(stderr, "           %05X:", at);
        for (unsigned i = 0; i < n && at + i < MEM_SIZE; i++) fprintf(stderr, "%s%02X", (i % 2) ? "" : " ", g_cpu->mem[at + i]);
        fprintf(stderr, "\n");
    }
    if (lin < 0xA0000 && g_nmiss <= 4) {
        fprintf(stderr, "           bytes there:");
        for (int i = -16; i < 32; i++) fprintf(stderr, "%s%02X", i == 0 ? " [" : " ", g_cpu->mem[lin + i]);
        fprintf(stderr, "\n");
    }
}

void dispatch_backtrace(void)
{
    {
#ifdef __linux__
        /* the guest's call chain is the host's: lifted functions are C functions */
        void *bt[24];
        int n = backtrace(bt, 24);
        char **sym = backtrace_symbols(bt, n);
        fprintf(stderr, "           called from:");
        for (int i = 2; i < n && sym; i++) {
            char *p = strstr(sym[i], "_fn_");
            if (p) { char *e = strchr(p, '+'); fprintf(stderr, " %.*s", (int)(e ? e - p - 4 : 8), p + 4); }
        }
        fprintf(stderr, "\n");
        if (getenv("DS_SITES")) {           /* for addr2line -e dsun */
            fprintf(stderr, "           sites:");
            for (int i = 2; i < n && i < 5 && sym; i++) fprintf(stderr, " %s", sym[i]);
            fprintf(stderr, "\n");
        }
        free(sym);
#endif
    }
}

void dispatch_dump_misses(const char *path)
{
    if (!g_nmiss) return;
    /* merge with what is there: the list only grows */
    unsigned old[MAXMISS]; int n = 0;
    FILE *f = fopen(path, "r");
    if (f) { while (n < MAXMISS && fscanf(f, "%x", &old[n]) == 1) n++; fclose(f); }
    f = fopen(path, "w");
    if (!f) return;
    for (int i = 0; i < n; i++) fprintf(f, "%05X\n", old[i]);
    for (int i = 0; i < g_nmiss; i++) {
        int dup = 0;
        for (int k = 0; k < n; k++) if (old[k] == g_miss[i]) dup = 1;
        if (!dup) fprintf(f, "%05X\n", g_miss[i]);
    }
    fclose(f);
    fprintf(stderr, "[dispatch] %d new address(es) for the next build -> %s\n", g_nmiss, path);
}

static recomp_fn lookup(unsigned lin)
{
    const DispEntry *d = g_game->dispatch;
    int lo = 0, hi = g_game->ndispatch - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (d[mid].addr == lin) return d[mid].fn;
        if (d[mid].addr < lin) lo = mid + 1; else hi = mid - 1;
    }
    return NULL;
}

int recomp_dispatch(CPU *cpu, unsigned seg, unsigned off)
{
    unsigned lin = ((seg & 0xFFFF) << 4) + (off & 0xFFFF);
    if (lin >= BIOS_LIN(BIOS_VEC_OFF) && lin < BIOS_LIN(BIOS_VEC_OFF) + 0x100) {
        /* A guest handler chaining to the BIOS's (`pushf / call far [old]`
         * or `jmp far [old]`): do the work, then the default handler's iret. */
        /* Services report in CF (and ZF for the keyboard), which the real
         * handlers write into the flags they return to. */
        bios_service(cpu, (int)(lin - BIOS_LIN(BIOS_VEC_OFF)));
        cpu->sp += 4;
        uint16_t keep = FLAG_CF | FLAG_ZF;
        cpu->flags = (pop16(cpu) & ~keep) | (cpu->flags & keep);
        return 1;
    }
    if (lin == BIOS_LIN(XMS_ENTRY_OFF)) {
        xms_service(cpu);
        cpu->sp += 4;                          /* the driver's retf */
        return 1;
    }
    if (lin == 0) return 0;
    /* Borland's int86x builds `int nn / retf [n]` on the stack and far-calls
     * it, so the interrupt comes with a real return address. The game's
     * builds vary: `push bp` before, `mov bp,[bp+d8]` before, `pop bp` after.
     * Run the pieces and the return. */
    {
        unsigned at = lin;
        int pushed_bp = 0, moved_bp = -1;
        if (cpu->mem[at] == 0x55) { pushed_bp = 1; at++; }
        if (cpu->mem[at] == 0x8B && cpu->mem[at + 1] == 0x6E) { moved_bp = (int8_t)cpu->mem[at + 2]; at += 3; }
        if (cpu->mem[at] == 0xCD) {
            unsigned after = at + 2;
            int pops_bp = cpu->mem[after] == 0x5D;
            if (pops_bp) after++;
            if (cpu->mem[after] == 0xCB || cpu->mem[after] == 0xCA) {
                if (pushed_bp) push16(cpu, cpu->bp);
                if (moved_bp != -1) {
                    unsigned a = ((cpu->ss & 0xFFFF) << 4) + ((cpu->bp + moved_bp) & 0xFFFF);
                    cpu->bp = cpu->mem[a] | (cpu->mem[a + 1] << 8);
                }
                run_guest_interrupt(cpu, cpu->mem[at + 1]);
                if (pops_bp) cpu->bp = pop16(cpu);
                unsigned extra = cpu->mem[after] == 0xCA ? (cpu->mem[after + 1] | (cpu->mem[after + 2] << 8)) : 0;
                cpu->sp += 4 + extra;
                return 1;
            }
        }
    }
    /* Offset FFFF is the return address every lifted call site pushes. Code
     * that pops its own return address and later jumps to it (Borland's
     * _setargv does: `pop [x] ... jmp [x]`) is returning to its C caller. */
    if ((off & 0xFFFF) == 0xFFFF) return 1;
    recomp_fn fn = lookup(lin);
    if (!fn) {
        extern int ail_driver_call(CPU *, unsigned, unsigned);
        if (ail_driver_call(cpu, seg, off)) return 1;
        /* Inside an interrupt handler, a jump into the middle of the game's
         * code is the mod's helper sending the game on from the INT it came
         * from: leave the address in CS:IP, and the code after that INT
         * continues there (tools/lift.py, SiteLifter). */
        note_miss(lin);
        return 0;
    }
    if (++g_depth > 2000) fatal("dispatch nested %d deep at %05X", g_depth, lin);
    fn(cpu);
    g_depth--;
    return 1;
}

void dispatch_reset_depth(void) { g_depth = 0; }

/* A far return to an address that is not the sentinel: to a function's entry
 * it is a tail call; to the middle of the game's code, from inside an
 * interrupt handler, it is the mod's helper returning with `retf 2` or to
 * the address it put in the frame -- CS:IP are left for the code after the
 * INT to act on (tools/lift.py, SiteLifter). */
static int inside_function(unsigned lin)       /* in the middle of a lifted function's code? */
{
    int lo = 0, hi = g_game->nranges - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_game->ranges[mid][0] <= lin && lin < g_game->ranges[mid][1]) return 1;
        if (g_game->ranges[mid][0] < lin) lo = mid + 1; else hi = mid - 1;
    }
    return 0;
}

void recomp_return(CPU *cpu, unsigned seg, unsigned off)
{
    unsigned lin = ((seg & 0xFFFF) << 4) + (off & 0xFFFF);
    /* Only into the game's own code (below the video memory): a return into
     * the middle of the helper is a continuation the finder has not seen,
     * which the miss list turns into an entry on the next build. */
    if (!lookup(lin) && g_in_int && g_game->tsr_cs && lin < 0xA0000 && inside_function(lin)) {
        static int shown;
        if (shown++ < 10 && getenv("DS_TRACE_INT")) trace("[dispatch] a handler sends the game on to %04X:%04X\n", seg, off);
        cpu->cs = (uint16_t)seg; cpu->ip = (uint16_t)off;
        return;
    }
    recomp_dispatch(cpu, seg, off);
}

void dispatch_near(CPU *cpu, unsigned seg, unsigned off)
{
    if (!recomp_dispatch(cpu, seg, off)) cpu->sp += 2;
}

void dispatch_far(CPU *cpu, unsigned seg, unsigned off)
{
    if (!recomp_dispatch(cpu, seg, off)) cpu->sp += 4;
}

void recomp_missing(CPU *cpu, const char *name)
{
    (void)cpu;
    trace("[dispatch] call to unresolved %s\n", name);
}

void recomp_unlifted(CPU *cpu, unsigned lin)
{
    (void)cpu;
    fatal("function %05X could not be lifted", lin);
}

void recomp_div0(const char *kind)
{
    trace("[cpu] divide error (%s)\n", kind);
}

/* ---- where it was -------------------------------------------------------------
 * Every lifted function announces itself (RECOMP_ENTER); the last few hundred
 * names are kept, with how often each was entered, and printed when a run
 * ends by timeout -- which turns "it hangs" into the loop it hangs in. */
static unsigned long g_entered;

void recomp_enter(const char *fn)
{
    g_ring[g_ring_i++ & (RING - 1)] = fn;
    g_entered++;
}

void recomp_trace_last(int n)
{
    fprintf(stderr, "           after:");
    for (int k = n; k >= 1; k--)
        if (g_ring_i >= (unsigned)k) { const char *n = g_ring[(g_ring_i - k) & (RING - 1)], *f = strstr(n, "fn_"); fprintf(stderr, " %s", f ? f + 3 : n); }
    fprintf(stderr, "\n");
}

void recomp_trace_dump(const char *why)
{
    fprintf(stderr, "[trace] %s: %lu functions entered; the last %d, oldest first:\n",
            why, g_entered, RING < (int)g_ring_i ? RING : (int)g_ring_i);
    unsigned n = g_ring_i < RING ? g_ring_i : RING;
    const char *prev = NULL; int rep = 0;
    for (unsigned k = 0; k < n; k++) {
        const char *s = g_ring[(g_ring_i - n + k) & (RING - 1)];
        if (prev && s == prev) { rep++; continue; }
        if (rep) fprintf(stderr, "    (x%d)\n", rep + 1);
        fprintf(stderr, "  %s\n", s);
        prev = s; rep = 0;
    }
    if (rep) fprintf(stderr, "    (x%d)\n", rep + 1);
    fprintf(stderr, "[trace] cs=%04X ds=%04X es=%04X ss:sp=%04X:%04X ax=%04X bx=%04X cx=%04X dx=%04X\n",
            g_cpu->cs, g_cpu->ds, g_cpu->es, g_cpu->ss, g_cpu->sp, g_cpu->ax, g_cpu->bx, g_cpu->cx, g_cpu->dx);
}

/* ---- stack audit (tools/lift.py --spcheck) ------------------------------------
 * A function is entered with its return address on the guest stack and must
 * leave having popped it: +2 for a near return, +4 for a far one, plus what a
 * `ret n` clears for its caller. Anything else is a function that took stack
 * it did not own, or left some behind, and everything after it runs on a
 * stack that no longer holds what it pushed. */
void recomp_sp_check(unsigned fn, uint16_t sp0, uint16_t ss0, uint16_t bp0, CPU *cpu)
{
    static int reported;
    if (cpu->ss != ss0) return;                       /* switched stacks */
    int d = (int16_t)(uint16_t)(cpu->sp - sp0);
    if (d >= 2 && d <= 64 && !(d & 1) && cpu->bp == bp0) return;
    if (reported++ < 40)
        fprintf(stderr, "[sp] fn_%05X moved SP by %+d (%04X -> %04X), BP %04X -> %04X\n",
                fn, d, sp0, cpu->sp, bp0, cpu->bp);
}
