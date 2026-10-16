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

#define MAXMISS 4096
static unsigned g_miss[MAXMISS];
static int g_nmiss;
static int g_depth;

static void note_miss(unsigned lin)
{
    for (int i = 0; i < g_nmiss; i++)
        if (g_miss[i] == lin) return;
    if (g_nmiss < MAXMISS) g_miss[g_nmiss++] = lin;
    trace("[dispatch] no function at %05X (ds=%04X ss:sp=%04X:%04X)\n",
          lin, g_cpu->ds, g_cpu->ss, g_cpu->sp);
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
    int lo = 0, hi = g_dispatch_n - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_dispatch[mid].addr == lin) return g_dispatch[mid].fn;
        if (g_dispatch[mid].addr < lin) lo = mid + 1; else hi = mid - 1;
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
    recomp_fn fn = lookup(lin);
    if (!fn) { note_miss(lin); return 0; }
    if (++g_depth > 2000) fatal("dispatch nested %d deep at %05X", g_depth, lin);
    fn(cpu);
    g_depth--;
    return 1;
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
