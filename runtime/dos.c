/*
 * dos.c - INT 21h: files, memory, the clock, and the rest of what DOS does
 * for a game.
 *
 * Files are the game folder's (g_game_dir), found without regard to case so
 * the same build runs on Windows and Linux. Memory is real MCB chains in guest
 * memory, as DOS keeps them, because Borland's start-up and heap read them.
 */
#include "runtime.h"
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <strings.h>

#define MAXF 64
static FILE *g_files[MAXF];
static char g_dta_seg_off_set;
static uint16_t g_dta_seg, g_dta_off;
static uint16_t g_psp;
static uint8_t g_last_error;

static void set_cf(CPU *cpu, int on)
{
    if (on) cpu->flags |= FLAG_CF; else cpu->flags &= ~FLAG_CF;
}

static void fail(CPU *cpu, uint16_t err)
{
    cpu->ax = err;
    g_last_error = (uint8_t)err;
    set_cf(cpu, 1);
}

/* ---- memory control blocks -------------------------------------------------- */
#define FIRST_MCB 0x07DF

static void mcb_set(CPU *cpu, uint16_t seg, char sig, uint16_t owner, uint16_t paras)
{
    cpu->mem[seg * 16] = (uint8_t)sig;
    mem_write16(cpu, seg, 1, owner);
    mem_write16(cpu, seg, 3, paras);
}

static void mcb_merge(CPU *cpu)
{
    uint16_t s = FIRST_MCB;
    for (;;) {
        char sig = (char)cpu->mem[s * 16];
        uint16_t own = mem_read16(cpu, s, 1), sz = mem_read16(cpu, s, 3);
        if (sig == 'Z') return;
        uint16_t n = (uint16_t)(s + sz + 1);
        if (own == 0 && mem_read16(cpu, n, 1) == 0) {
            char nsig = (char)cpu->mem[n * 16];
            mcb_set(cpu, s, nsig, 0, (uint16_t)(sz + 1 + mem_read16(cpu, n, 3)));
            continue;
        }
        s = n;
    }
}

static void mem_alloc(CPU *cpu)
{
    uint16_t want = cpu->bx, best = 0, s = FIRST_MCB, biggest = 0;
    mcb_merge(cpu);
    for (;;) {
        char sig = (char)cpu->mem[s * 16];
        uint16_t own = mem_read16(cpu, s, 1), sz = mem_read16(cpu, s, 3);
        if (own == 0) {
            if (sz >= want && !best) best = s;
            if (sz > biggest) biggest = sz;
        }
        if (sig == 'Z') break;
        s = (uint16_t)(s + sz + 1);
    }
    if (!best) { cpu->bx = biggest; fail(cpu, 8); return; }
    char sig = (char)cpu->mem[best * 16];
    uint16_t sz = mem_read16(cpu, best, 3);
    if (sz > want) {
        mcb_set(cpu, best, 'M', g_psp, want);
        mcb_set(cpu, (uint16_t)(best + want + 1), sig, 0, (uint16_t)(sz - want - 1));
    } else mcb_set(cpu, best, sig, g_psp, sz);
    cpu->ax = (uint16_t)(best + 1);
    set_cf(cpu, 0);
}

static void mem_free(CPU *cpu, uint16_t seg)
{
    mem_write16(cpu, (uint16_t)(seg - 1), 1, 0);
    mcb_merge(cpu);
    set_cf(cpu, 0);
}

static void mem_resize(CPU *cpu)
{
    uint16_t seg = cpu->es, mcb = (uint16_t)(seg - 1), want = cpu->bx;
    mcb_merge(cpu);
    char sig = (char)cpu->mem[mcb * 16];
    uint16_t sz = mem_read16(cpu, mcb, 3);
    if (want <= sz) {
        if (want < sz) {
            mcb_set(cpu, mcb, 'M', mem_read16(cpu, mcb, 1), want);
            mcb_set(cpu, (uint16_t)(mcb + want + 1), sig, 0, (uint16_t)(sz - want - 1));
            mcb_merge(cpu);
        }
        set_cf(cpu, 0);
        return;
    }
    uint16_t n = (uint16_t)(mcb + sz + 1);
    uint16_t avail = sz;
    if (sig != 'Z' && mem_read16(cpu, n, 1) == 0) avail = (uint16_t)(sz + 1 + mem_read16(cpu, n, 3));
    if (avail < want) { cpu->bx = avail; fail(cpu, 8); return; }
    char nsig = sig == 'Z' ? 'Z' : (char)cpu->mem[n * 16];
    if (avail > want) {
        mcb_set(cpu, mcb, 'M', mem_read16(cpu, mcb, 1), want);
        mcb_set(cpu, (uint16_t)(mcb + want + 1), nsig, 0, (uint16_t)(avail - want - 1));
    } else mcb_set(cpu, mcb, nsig, mem_read16(cpu, mcb, 1), avail);
    set_cf(cpu, 0);
}

/* ---- paths -------------------------------------------------------------------------- */
static void guest_str(CPU *cpu, uint16_t seg, uint16_t off, char *out, int n)
{
    int i = 0;
    for (; i < n - 1; i++) {
        char c = (char)mem_read8(cpu, seg, (uint16_t)(off + i));
        if (!c) break;
        out[i] = c;
    }
    out[i] = 0;
}

/* "C:\\DIR\\File.ext" -> a host path inside the game folder, matching case. */
static int host_path(const char *dos, char *out, size_t n, int must_exist)
{
    const char *p = dos;
    if (p[0] && p[1] == ':') p += 2;
    while (*p == '\\' || *p == '/') p++;
    snprintf(out, n, "%s", g_game_dir);
    while (*p) {
        char part[128]; int k = 0;
        while (*p && *p != '\\' && *p != '/' && k < 127) part[k++] = *p++;
        part[k] = 0;
        while (*p == '\\' || *p == '/') p++;
        if (!strcmp(part, ".")) continue;
        char found[128] = {0};
        DIR *d = opendir(out);
        if (d) {
            struct dirent *e;
            while ((e = readdir(d))) if (!strcasecmp(e->d_name, part)) { snprintf(found, sizeof found, "%s", e->d_name); break; }
            closedir(d);
        }
        if (!found[0]) {
            if (*p || must_exist) { if (!*p) return 0; }
            for (char *c = part; *c; c++) *c = (char)toupper((unsigned char)*c);
            snprintf(found, sizeof found, "%s", part);
        }
        size_t l = strlen(out);
        snprintf(out + l, n - l, "/%s", found);
    }
    struct stat st;
    return !must_exist || stat(out, &st) == 0;
}

static int new_handle(FILE *f)
{
    for (int h = 5; h < MAXF; h++) if (!g_files[h]) { g_files[h] = f; return h; }
    return -1;
}

/* ---- find first / next ---------------------------------------------------------------- */
static char g_find_pat[128], g_find_dir[512];
static long g_find_pos;
static uint8_t g_find_attr;

static int wild(const char *pat, const char *name)
{
    /* DOS 8.3 matching: name and extension separately, '?' and '*' */
    char pn[16], pe[8], nn[16], ne[8];
    const char *d;
    d = strchr(pat, '.');
    snprintf(pn, sizeof pn, "%.*s", d ? (int)(d - pat) : (int)strlen(pat), pat);
    snprintf(pe, sizeof pe, "%s", d ? d + 1 : "");
    d = strchr(name, '.');
    snprintf(nn, sizeof nn, "%.*s", d ? (int)(d - name) : (int)strlen(name), name);
    snprintf(ne, sizeof ne, "%s", d ? d + 1 : "");
    const char *ps[2] = {pn, pe}, *ns[2] = {nn, ne};
    for (int part = 0; part < 2; part++) {
        const char *a = ps[part], *b = ns[part];
        for (;;) {
            if (*a == '*') break;
            if (!*a) { if (*b) return 0; break; }
            if (!*b) { if (*a != '?') return 0; a++; continue; }
            if (*a != '?' && toupper((unsigned char)*a) != toupper((unsigned char)*b)) return 0;
            a++; b++;
        }
    }
    return 1;
}

static int find_next(CPU *cpu)
{
    DIR *d = opendir(g_find_dir);
    if (!d) return 0;
    struct dirent *e;
    long i = 0;
    while ((e = readdir(d))) {
        if (i++ < g_find_pos) continue;
        g_find_pos = i;
        if (e->d_name[0] == '.' || strlen(e->d_name) > 12) continue;
        if (!wild(g_find_pat, e->d_name)) continue;
        char full[1024]; struct stat st;
        snprintf(full, sizeof full, "%s/%s", g_find_dir, e->d_name);
        if (stat(full, &st)) continue;
        int dir = S_ISDIR(st.st_mode);
        if (dir && !(g_find_attr & 0x10)) continue;
        uint32_t dta = ((uint32_t)g_dta_seg << 4) + g_dta_off;
        uint8_t *m = cpu->mem + dta;
        m[0x15] = dir ? 0x10 : 0x20;
        struct tm *t = localtime(&st.st_mtime);
        uint16_t ftime = (uint16_t)((t->tm_hour << 11) | (t->tm_min << 5) | (t->tm_sec / 2));
        uint16_t fdate = (uint16_t)(((t->tm_year - 80) << 9) | ((t->tm_mon + 1) << 5) | t->tm_mday);
        m[0x16] = (uint8_t)ftime; m[0x17] = (uint8_t)(ftime >> 8);
        m[0x18] = (uint8_t)fdate; m[0x19] = (uint8_t)(fdate >> 8);
        uint32_t sz = (uint32_t)st.st_size;
        memcpy(m + 0x1A, &sz, 4);
        memset(m + 0x1E, 0, 13);
        for (int k = 0; k < 12 && e->d_name[k]; k++) m[0x1E + k] = (uint8_t)toupper((unsigned char)e->d_name[k]);
        closedir(d);
        return 1;
    }
    closedir(d);
    return 0;
}

/* ---- the service ------------------------------------------------------------------------ */
void dos_init(CPU *cpu)
{
    g_files[0] = stdin; g_files[1] = stdout; g_files[2] = stderr;
    g_files[3] = stderr; g_files[4] = stderr;
    g_psp = 0x0800;
    mcb_set(cpu, FIRST_MCB, 'M', g_psp, 0x1F);                 /* environment */
    mcb_set(cpu, 0x07FF, 'Z', g_psp, (uint16_t)(0xA000 - 0x0800 - 1));
    g_dta_seg = g_psp; g_dta_off = 0x80;
}

void dos_service(CPU *cpu)
{
    char name[256], path[1024];
    uint8_t ah = cpu->ah;
    switch (ah) {
    case 0x02: fputc(cpu->dl, stderr); break;
    case 0x06: if (cpu->dl != 0xFF) fputc(cpu->dl, stderr); else { cpu->flags |= FLAG_ZF; cpu->al = 0; } break;
    case 0x07: case 0x08: { uint16_t w; while (!host_key_pop(&w, 0)) { irq_poll(cpu); host_sleep_us(2000); } cpu->al = (uint8_t)w; break; }
    case 0x09: {
        for (uint16_t o = cpu->dx; ; o++) { char c = (char)mem_read8(cpu, cpu->ds, o); if (c == '$') break; fputc(c, stderr); }
        break; }
    case 0x0B: { uint16_t w; cpu->al = host_key_pop(&w, 1) ? 0xFF : 0; break; }
    case 0x0C: { uint8_t f = cpu->al; uint16_t w; while (host_key_pop(&w, 1)) host_key_pop(&w, 0);
                 if (f) { cpu->ah = f; dos_service(cpu); } break; }
    case 0x0D: break;
    case 0x0E: cpu->al = 3; break;
    case 0x19: cpu->al = 2; break;                              /* C: */
    case 0x1A: g_dta_seg = cpu->ds; g_dta_off = cpu->dx; g_dta_seg_off_set = 1; break;
    case 0x25: mem_write16(cpu, 0, (uint16_t)(cpu->al * 4), cpu->dx);
               mem_write16(cpu, 0, (uint16_t)(cpu->al * 4 + 2), cpu->ds);
               trace("[dos] vector %02X -> %04X:%04X\n", cpu->al, cpu->ds, cpu->dx); break;
    case 0x2A: { time_t t = time(NULL); struct tm *tm = localtime(&t);
                 cpu->cx = (uint16_t)(tm->tm_year + 1900); cpu->dh = (uint8_t)(tm->tm_mon + 1);
                 cpu->dl = (uint8_t)tm->tm_mday; cpu->al = (uint8_t)tm->tm_wday; break; }
    case 0x2C: { uint64_t us = host_us(); time_t t = time(NULL); struct tm *tm = localtime(&t);
                 cpu->ch = (uint8_t)tm->tm_hour; cpu->cl = (uint8_t)tm->tm_min; cpu->dh = (uint8_t)tm->tm_sec;
                 cpu->dl = (uint8_t)((us / 10000) % 100); break; }
    case 0x2F: cpu->es = g_dta_seg; cpu->bx = g_dta_off; break;
    case 0x30: cpu->ax = 0x0005; cpu->bx = 0; cpu->cx = 0; break;   /* DOS 5.0 */
    case 0x33: if (cpu->al == 0 || cpu->al == 2) cpu->dl = 0; else if (cpu->al == 5) cpu->dl = 3; break;
    case 0x35: cpu->bx = mem_read16(cpu, 0, (uint16_t)(cpu->al * 4));
               cpu->es = mem_read16(cpu, 0, (uint16_t)(cpu->al * 4 + 2)); break;
    case 0x36: cpu->ax = 64; cpu->bx = 0x7FFF; cpu->cx = 512; cpu->dx = 0xFFFF; break;
    case 0x3B: set_cf(cpu, 0); break;
    case 0x3C: case 0x5B: {
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        host_path(name, path, sizeof path, 0);
        FILE *f = fopen(path, "w+b");
        trace("[dos] create %s -> %s\n", name, f ? "ok" : "failed");
        int h = f ? new_handle(f) : -1;
        if (h < 0) { if (f) fclose(f); fail(cpu, f ? 4 : 3); break; }
        cpu->ax = (uint16_t)h; set_cf(cpu, 0);
        break; }
    case 0x3D: {
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        int mode = cpu->al & 3;
        if (!strncasecmp(name, "EMMXXXX0", 8) || !strncasecmp(name, "MSCD", 4)) { fail(cpu, 2); break; }
        if (!host_path(name, path, sizeof path, 1)) { trace("[dos] open %s: not found\n", name); fail(cpu, 2); break; }
        FILE *f = fopen(path, mode == 0 ? "rb" : "r+b");
        if (!f && mode) f = fopen(path, "rb");
        trace("[dos] open %s (mode %d) -> %s\n", name, mode, f ? "ok" : "failed");
        int h = f ? new_handle(f) : -1;
        if (h < 0) { if (f) fclose(f); fail(cpu, f ? 4 : 5); break; }
        cpu->ax = (uint16_t)h; set_cf(cpu, 0);
        break; }
    case 0x3E: {
        int h = cpu->bx;
        if (h >= 5 && h < MAXF && g_files[h]) { fclose(g_files[h]); g_files[h] = NULL; }
        set_cf(cpu, 0);
        break; }
    case 0x3F: {
        int h = cpu->bx;
        if (h == 0) { cpu->ax = 0; set_cf(cpu, 0); break; }
        if (h < 0 || h >= MAXF || !g_files[h]) { fail(cpu, 6); break; }
        uint32_t lin = ((uint32_t)cpu->ds << 4) + cpu->dx;
        size_t n = fread(cpu->mem + lin, 1, cpu->cx, g_files[h]);
        if (lin < 0xB0000 && lin + n > 0xA0000) trace("[dos] read into video memory\n");
        cpu->ax = (uint16_t)n; set_cf(cpu, 0);
        break; }
    case 0x40: {
        int h = cpu->bx;
        if (h < 0 || h >= MAXF || !g_files[h]) { fail(cpu, 6); break; }
        uint32_t lin = ((uint32_t)cpu->ds << 4) + cpu->dx;
        if (cpu->cx == 0 && h >= 5) {                    /* truncate here */
            fflush(g_files[h]);
            cpu->ax = 0; set_cf(cpu, 0); break;
        }
        size_t n = fwrite(cpu->mem + lin, 1, cpu->cx, g_files[h]);
        if (h < 5) fflush(g_files[h]);
        cpu->ax = (uint16_t)n; set_cf(cpu, 0);
        break; }
    case 0x41: {
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        if (!host_path(name, path, sizeof path, 1) || remove(path)) { fail(cpu, 2); break; }
        set_cf(cpu, 0);
        break; }
    case 0x42: {
        int h = cpu->bx;
        if (h < 5 || h >= MAXF || !g_files[h]) { if (h < 5) { cpu->ax = cpu->dx = 0; set_cf(cpu, 0); } else fail(cpu, 6); break; }
        long off = (long)(int32_t)(((uint32_t)cpu->cx << 16) | cpu->dx);
        if (cpu->al == 0) off = (long)(((uint32_t)cpu->cx << 16) | cpu->dx);
        fseek(g_files[h], off, cpu->al == 0 ? SEEK_SET : cpu->al == 1 ? SEEK_CUR : SEEK_END);
        long pos = ftell(g_files[h]);
        cpu->ax = (uint16_t)pos; cpu->dx = (uint16_t)(pos >> 16); set_cf(cpu, 0);
        break; }
    case 0x43: {
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        if (!host_path(name, path, sizeof path, 1)) { fail(cpu, 2); break; }
        struct stat st; stat(path, &st);
        cpu->cx = S_ISDIR(st.st_mode) ? 0x10 : 0x20; set_cf(cpu, 0);
        break; }
    case 0x44:
        if (cpu->al == 0x00) {
            int h = cpu->bx;
            cpu->dx = h < 5 ? (h == 0 ? 0x81 : 0x82) | 0x80 : 0x0002;
            if (h >= 5 && (h >= MAXF || !g_files[h])) { fail(cpu, 6); break; }
            set_cf(cpu, 0);
        } else if (cpu->al == 0x08) { cpu->ax = 1; set_cf(cpu, 0); }
        else if (cpu->al == 0x09) { cpu->dx = 0; set_cf(cpu, 0); }
        else fail(cpu, 1);
        break;
    case 0x45: {
        int h = cpu->bx;
        if (h < 5) { cpu->ax = (uint16_t)h; set_cf(cpu, 0); break; }
        if (h >= MAXF || !g_files[h]) { fail(cpu, 6); break; }
        int fd = dup(fileno(g_files[h]));
        FILE *f = fd >= 0 ? fdopen(fd, "r+b") : NULL;
        int nh = f ? new_handle(f) : -1;
        if (nh < 0) { fail(cpu, 4); break; }
        cpu->ax = (uint16_t)nh; set_cf(cpu, 0);
        break; }
    case 0x47: mem_write8(cpu, cpu->ds, cpu->si, 0); set_cf(cpu, 0); break;
    case 0x48: mem_alloc(cpu); break;
    case 0x49: mem_free(cpu, cpu->es); break;
    case 0x4A: mem_resize(cpu); break;
    case 0x4C: case 0x00:
        fprintf(stderr, "[dos] the game exited (code %d)\n", cpu->al);
        { extern void host_exit(int); host_exit(cpu->al); }
        break;
    case 0x4E: {
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        char *slash = strrchr(name, '\\');
        const char *pat = slash ? slash + 1 : (name[1] == ':' ? name + 2 : name);
        if (slash) { *slash = 0; host_path(name, g_find_dir, sizeof g_find_dir, 0); }
        else snprintf(g_find_dir, sizeof g_find_dir, "%s", g_game_dir);
        snprintf(g_find_pat, sizeof g_find_pat, "%s", pat);
        g_find_pos = 0; g_find_attr = cpu->cl;
        if (find_next(cpu)) set_cf(cpu, 0); else fail(cpu, 18);
        break; }
    case 0x4F: if (find_next(cpu)) set_cf(cpu, 0); else fail(cpu, 18); break;
    case 0x50: g_psp = cpu->bx; break;
    case 0x51: case 0x62: cpu->bx = g_psp; break;
    case 0x56: {
        char to[256], pto[1024];
        guest_str(cpu, cpu->ds, cpu->dx, name, sizeof name);
        guest_str(cpu, cpu->es, cpu->di, to, sizeof to);
        if (!host_path(name, path, sizeof path, 1)) { fail(cpu, 2); break; }
        host_path(to, pto, sizeof pto, 0);
        if (rename(path, pto)) fail(cpu, 5); else set_cf(cpu, 0);
        break; }
    case 0x57: if (cpu->al == 0) { cpu->cx = 0; cpu->dx = 0x2121; } set_cf(cpu, 0); break;
    case 0x58: cpu->ax = 0; set_cf(cpu, 0); break;
    case 0x59: cpu->ax = g_last_error; cpu->bh = 1; cpu->bl = 4; cpu->ch = 1; break;
    case 0x68: set_cf(cpu, 0); break;
    default:
        trace("[dos] unhandled INT 21h AH=%02X AL=%02X\n", ah, cpu->al);
        fail(cpu, 1);
        break;
    }
}
