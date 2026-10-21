/*
 * host.c - the window, the clock and input, through SDL2.
 *
 * The game runs on a thread of its own with a large stack (each guest call is
 * a C call, and the game nests deeply); the main thread owns the window,
 * turns SDL events into PC scancodes and BIOS key words, and shows the VGA's
 * picture 60 times a second.
 *
 * Headless (--headless, or no display): no window, and input can be scripted
 * with --input "2.5:key=ESC 4:click=160,100 6:key=RET" (seconds:action; rclick= for the right button, rdrag=x1,y1,x2,y2 holds it from one point to another), so a
 * run can be tested without anyone at the keyboard. --shots DIR saves the
 * screen once a second.
 */
#include "runtime.h"
#include <SDL.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

static int g_headless;
static SDL_mutex *g_lock;

int host_headless(void) { return g_headless; }

uint64_t host_us(void)
{
    static uint64_t base, freq;
    if (!freq) { freq = SDL_GetPerformanceFrequency(); base = SDL_GetPerformanceCounter(); }
    return (SDL_GetPerformanceCounter() - base) * 1000000ull / freq;
}

void host_sleep_us(unsigned us) { SDL_Delay(us >= 1000 ? us / 1000 : 1); }

void trace(const char *fmt, ...)
{
    static int quiet = -1;
    if (quiet < 0) quiet = getenv("DS_QUIET") != NULL;
    if (quiet) return;
    va_list ap; va_start(ap, fmt);
    fprintf(stderr, "%8.3f ", host_us() / 1e6);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}

void fatal(const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    fprintf(stderr, "fatal: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    extern void host_exit(int);
    host_exit(99);
}

/* ---- keyboard --------------------------------------------------------------- */
typedef struct { uint8_t sc; uint16_t word; } KeyEv;
static KeyEv g_kq[64]; static int g_kq_r, g_kq_w;
static KeyEv g_kcur;
static uint16_t g_kbuf[32]; static int g_kb_r, g_kb_w;

void host_key_event(uint8_t scancode, int down, uint16_t word)
{
    SDL_LockMutex(g_lock);
    int n = (g_kq_w + 1) % 64;
    if (n != g_kq_r) {
        g_kq[g_kq_w].sc = (uint8_t)(scancode | (down ? 0 : 0x80));
        g_kq[g_kq_w].word = down ? word : 0;
        g_kq_w = n;
        irq_raise(1);
    }
    SDL_UnlockMutex(g_lock);
}

uint8_t host_scancode(void)
{
    SDL_LockMutex(g_lock);
    if (g_kq_r != g_kq_w) { g_kcur = g_kq[g_kq_r]; g_kq_r = (g_kq_r + 1) % 64; }
    if (g_kq_r != g_kq_w) irq_raise(1);
    SDL_UnlockMutex(g_lock);
    return g_kcur.sc;
}

void host_key_commit(void)               /* the BIOS's INT 9 */
{
    if (!g_kcur.word) return;
    int n = (g_kb_w + 1) % 32;
    if (n != g_kb_r) { g_kbuf[g_kb_w] = g_kcur.word; g_kb_w = n; }
    g_kcur.word = 0;
}

int host_key_pop(uint16_t *word, int peek)
{
    if (g_kb_r == g_kb_w) return 0;
    *word = g_kbuf[g_kb_r];
    if (!peek) g_kb_r = (g_kb_r + 1) % 32;
    return 1;
}

/* SDL scancode -> PC set 1 scancode, and the ASCII the BIOS would add */
static const struct { SDL_Scancode s; uint8_t pc; uint8_t lo, hi; } KEYS[] = {
    {SDL_SCANCODE_ESCAPE, 0x01, 27, 27}, {SDL_SCANCODE_1, 0x02, '1', '!'}, {SDL_SCANCODE_2, 0x03, '2', '@'},
    {SDL_SCANCODE_3, 0x04, '3', '#'}, {SDL_SCANCODE_4, 0x05, '4', '$'}, {SDL_SCANCODE_5, 0x06, '5', '%'},
    {SDL_SCANCODE_6, 0x07, '6', '^'}, {SDL_SCANCODE_7, 0x08, '7', '&'}, {SDL_SCANCODE_8, 0x09, '8', '*'},
    {SDL_SCANCODE_9, 0x0A, '9', '('}, {SDL_SCANCODE_0, 0x0B, '0', ')'}, {SDL_SCANCODE_MINUS, 0x0C, '-', '_'},
    {SDL_SCANCODE_EQUALS, 0x0D, '=', '+'}, {SDL_SCANCODE_BACKSPACE, 0x0E, 8, 8}, {SDL_SCANCODE_TAB, 0x0F, 9, 0},
    {SDL_SCANCODE_Q, 0x10, 'q', 'Q'}, {SDL_SCANCODE_W, 0x11, 'w', 'W'}, {SDL_SCANCODE_E, 0x12, 'e', 'E'},
    {SDL_SCANCODE_R, 0x13, 'r', 'R'}, {SDL_SCANCODE_T, 0x14, 't', 'T'}, {SDL_SCANCODE_Y, 0x15, 'y', 'Y'},
    {SDL_SCANCODE_U, 0x16, 'u', 'U'}, {SDL_SCANCODE_I, 0x17, 'i', 'I'}, {SDL_SCANCODE_O, 0x18, 'o', 'O'},
    {SDL_SCANCODE_P, 0x19, 'p', 'P'}, {SDL_SCANCODE_LEFTBRACKET, 0x1A, '[', '{'}, {SDL_SCANCODE_RIGHTBRACKET, 0x1B, ']', '}'},
    {SDL_SCANCODE_RETURN, 0x1C, 13, 13}, {SDL_SCANCODE_LCTRL, 0x1D, 0, 0}, {SDL_SCANCODE_A, 0x1E, 'a', 'A'},
    {SDL_SCANCODE_S, 0x1F, 's', 'S'}, {SDL_SCANCODE_D, 0x20, 'd', 'D'}, {SDL_SCANCODE_F, 0x21, 'f', 'F'},
    {SDL_SCANCODE_G, 0x22, 'g', 'G'}, {SDL_SCANCODE_H, 0x23, 'h', 'H'}, {SDL_SCANCODE_J, 0x24, 'j', 'J'},
    {SDL_SCANCODE_K, 0x25, 'k', 'K'}, {SDL_SCANCODE_L, 0x26, 'l', 'L'}, {SDL_SCANCODE_SEMICOLON, 0x27, ';', ':'},
    {SDL_SCANCODE_APOSTROPHE, 0x28, '\'', '"'}, {SDL_SCANCODE_GRAVE, 0x29, '`', '~'}, {SDL_SCANCODE_LSHIFT, 0x2A, 0, 0},
    {SDL_SCANCODE_BACKSLASH, 0x2B, '\\', '|'}, {SDL_SCANCODE_Z, 0x2C, 'z', 'Z'}, {SDL_SCANCODE_X, 0x2D, 'x', 'X'},
    {SDL_SCANCODE_C, 0x2E, 'c', 'C'}, {SDL_SCANCODE_V, 0x2F, 'v', 'V'}, {SDL_SCANCODE_B, 0x30, 'b', 'B'},
    {SDL_SCANCODE_N, 0x31, 'n', 'N'}, {SDL_SCANCODE_M, 0x32, 'm', 'M'}, {SDL_SCANCODE_COMMA, 0x33, ',', '<'},
    {SDL_SCANCODE_PERIOD, 0x34, '.', '>'}, {SDL_SCANCODE_SLASH, 0x35, '/', '?'}, {SDL_SCANCODE_RSHIFT, 0x36, 0, 0},
    {SDL_SCANCODE_LALT, 0x38, 0, 0}, {SDL_SCANCODE_SPACE, 0x39, ' ', ' '},
    {SDL_SCANCODE_F1, 0x3B, 0, 0}, {SDL_SCANCODE_F2, 0x3C, 0, 0}, {SDL_SCANCODE_F3, 0x3D, 0, 0},
    {SDL_SCANCODE_F4, 0x3E, 0, 0}, {SDL_SCANCODE_F5, 0x3F, 0, 0}, {SDL_SCANCODE_F6, 0x40, 0, 0},
    {SDL_SCANCODE_F7, 0x41, 0, 0}, {SDL_SCANCODE_F8, 0x42, 0, 0}, {SDL_SCANCODE_F9, 0x43, 0, 0},
    {SDL_SCANCODE_F10, 0x44, 0, 0}, {SDL_SCANCODE_HOME, 0x47, 0, 0}, {SDL_SCANCODE_UP, 0x48, 0, 0},
    {SDL_SCANCODE_PAGEUP, 0x49, 0, 0}, {SDL_SCANCODE_LEFT, 0x4B, 0, 0}, {SDL_SCANCODE_RIGHT, 0x4D, 0, 0},
    {SDL_SCANCODE_END, 0x4F, 0, 0}, {SDL_SCANCODE_DOWN, 0x50, 0, 0}, {SDL_SCANCODE_PAGEDOWN, 0x51, 0, 0},
    {SDL_SCANCODE_INSERT, 0x52, 0, 0}, {SDL_SCANCODE_DELETE, 0x53, 0, 0},
};

static int g_shift;

static void key(SDL_Scancode s, int down)
{
    for (size_t i = 0; i < sizeof KEYS / sizeof *KEYS; i++) {
        if (KEYS[i].s != s) continue;
        if (KEYS[i].pc == 0x2A || KEYS[i].pc == 0x36) g_shift = down;
        uint8_t a = g_shift ? KEYS[i].hi : KEYS[i].lo;
        host_key_event(KEYS[i].pc, down, (uint16_t)((KEYS[i].pc << 8) | a));
        return;
    }
}

/* ---- mouse ---------------------------------------------------------------------- */
static volatile int g_mx = 160, g_my = 100, g_mb;

void host_mouse(int *x, int *y, int *b) { *x = g_mx; *y = g_my; *b = g_mb; }
void host_mouse_set(int x, int y) { g_mx = x; g_my = y; }

/* ---- scripted input ---------------------------------------------------------------- */
typedef struct { double t; char what[64]; int a, b, c, d; } Act;
static Act g_acts[256]; static int g_nacts, g_next_act;

static void parse_input(const char *s)
{
    while (s && *s && g_nacts < 256) {
        while (*s == ' ') s++;
        Act *a = &g_acts[g_nacts];
        char what[64];
        if (sscanf(s, "%lf:%63[^ ]", &a->t, what) != 2) break;
        if (!strncmp(what, "key=", 4)) { snprintf(a->what, sizeof a->what, "%s", what + 4); a->a = -1; }
        else if (sscanf(what, "click=%d,%d", &a->a, &a->b) == 2) strcpy(a->what, "@click");
        else if (sscanf(what, "rclick=%d,%d", &a->a, &a->b) == 2) strcpy(a->what, "@rclick");
        else if (sscanf(what, "rdrag=%d,%d,%d,%d", &a->a, &a->b, &a->c, &a->d) == 4) strcpy(a->what, "@rdrag");
        else if (sscanf(what, "move=%d,%d", &a->a, &a->b) == 2) strcpy(a->what, "@move");
        g_nacts++;
        s = strchr(s, ' ');
    }
}

static void run_actions(double now)
{
    while (g_next_act < g_nacts && g_acts[g_next_act].t <= now) {
        Act *a = &g_acts[g_next_act++];
        fprintf(stderr, "[input] %.1fs %s\n", now, a->what);
        if (!strcmp(a->what, "@click")) {
            g_mx = a->a; g_my = a->b; g_mb = 1; SDL_Delay(120); g_mb = 0;
        } else if (!strcmp(a->what, "@rclick")) {
            g_mx = a->a; g_my = a->b; g_mb = 2; SDL_Delay(120); g_mb = 0;
        } else if (!strcmp(a->what, "@rdrag")) {         /* the right button held from one point to another: the game's pop-up menus */
            g_mx = a->a; g_my = a->b; g_mb = 2; SDL_Delay(300); g_mx = a->c; g_my = a->d; SDL_Delay(300); g_mb = 0;
        } else if (!strcmp(a->what, "@move")) { g_mx = a->a; g_my = a->b; }
        else {
            /* key=NAME[/HOLD_MS]: SDL's key names, and a few short ones */
            char nm[32]; int hold = 60;
            snprintf(nm, sizeof nm, "%s", a->what);
            char *sl = strchr(nm, '/');
            if (sl) { *sl = 0; hold = atoi(sl + 1); }
            SDL_Scancode s = SDL_GetScancodeFromName(nm);
            if (!strcmp(nm, "ESC")) s = SDL_SCANCODE_ESCAPE;
            if (!strcmp(nm, "RET")) s = SDL_SCANCODE_RETURN;
            if (!strcmp(nm, "SPC")) s = SDL_SCANCODE_SPACE;
            if (!strcmp(nm, "LSHIFT")) s = SDL_SCANCODE_LSHIFT;
            if (!strcmp(nm, "RSHIFT")) s = SDL_SCANCODE_RSHIFT;
            if (!strcmp(nm, "CTRL")) s = SDL_SCANCODE_LCTRL;
            if (!strcmp(nm, "ALT")) s = SDL_SCANCODE_LALT;
            key(s, 1); SDL_Delay(hold); key(s, 0);
        }
    }
}

/* ---- the run --------------------------------------------------------------------- */
static volatile int g_exit_code = -1;
static SDL_Thread *g_game_thread;
extern int game_main(void *arg);

void host_exit(int code)
{
    g_exit_code = code;
    { extern void audio_close(void); audio_close(); }
    { extern void opl_report(void); opl_report(); }
    { extern void ail_report(void); ail_report(); }
    extern void dispatch_dump_misses(const char *);
    extern const char *g_build_dir;
    char p[1024];
    snprintf(p, sizeof p, "%s/misses.txt", g_build_dir);
    dispatch_dump_misses(p);
    if (SDL_ThreadID() == SDL_GetThreadID(g_game_thread)) {
        for (;;) SDL_Delay(1000);              /* the main thread ends the process */
    }
    exit(code);
}

int host_run(int headless, double seconds, const char *shots, const char *input)
{
    g_headless = headless;
    if (headless) SDL_setenv("SDL_VIDEODRIVER", "dummy", 1);
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) != 0) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    g_lock = SDL_CreateMutex();
    parse_input(input);
    SDL_Window *win = NULL; SDL_Renderer *ren = NULL; SDL_Texture *tex = NULL;
    if (!headless) {
        win = SDL_CreateWindow("Dark Sun Recompiled", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                               960, 720, SDL_WINDOW_RESIZABLE);
        ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_PRESENTVSYNC);
        SDL_RenderSetLogicalSize(ren, 320, 240);
        tex = SDL_CreateTexture(ren, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, 320, 240);
        SDL_ShowCursor(SDL_DISABLE);
    }
    g_game_thread = SDL_CreateThreadWithStackSize(game_main, "game", 256u << 20, NULL);
    static uint32_t px[320 * 240];
    double next_shot = 1.0;
    int shot = 0;
    while (g_exit_code < 0) {
        double now = host_us() / 1e6;
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) host_exit(0);
            if (e.type == SDL_KEYDOWN && !e.key.repeat) key(e.key.keysym.scancode, 1);
            if (e.type == SDL_KEYUP) key(e.key.keysym.scancode, 0);
            if (e.type == SDL_MOUSEMOTION) {
                float lx, ly; int wx = e.motion.x, wy = e.motion.y;
                SDL_RenderWindowToLogical(ren, wx, wy, &lx, &ly);
                g_mx = lx < 0 ? 0 : lx > 319 ? 319 : (int)lx;
                g_my = ly < 0 ? 0 : ly > 199 ? 199 : (int)ly;
            }
            if (e.type == SDL_MOUSEBUTTONDOWN) g_mb |= e.button.button == SDL_BUTTON_LEFT ? 1 : 2;
            if (e.type == SDL_MOUSEBUTTONUP) g_mb &= ~(e.button.button == SDL_BUTTON_LEFT ? 1 : 2);
        }
        run_actions(now);
        { extern void audio_pump(void); audio_pump(); }
        if (!headless) {
            int w, h;
            vga_render(px, &w, &h);
            SDL_UpdateTexture(tex, NULL, px, 320 * 4);
            SDL_Rect src = {0, 0, w, h};
            SDL_RenderSetLogicalSize(ren, 320, h == 200 ? 240 : h);   /* 4:3 */
            SDL_RenderClear(ren);
            SDL_RenderCopy(ren, tex, &src, NULL);
            SDL_RenderPresent(ren);
        } else SDL_Delay(16);
        if (shots && now >= next_shot) {
            char p[1024];
            snprintf(p, sizeof p, "%s/shot_%03d.bmp", shots, shot++);
            vga_save_bmp(p);
            next_shot += 1.0;
        }
        if (seconds > 0 && now >= seconds) {
            fprintf(stderr, "[host] %.0f s are up; %lu retraces waited on\n", seconds, g_vga_frames);
            { extern void recomp_trace_dump(const char *); recomp_trace_dump("timeout"); }
            { extern volatile int g_want_backtrace; g_want_backtrace = 1; SDL_Delay(300); }
            if (shots) { char p[1024]; snprintf(p, sizeof p, "%s/final.bmp", shots); vga_save_bmp(p); }
            host_exit(0);
        }
    }
    return g_exit_code;
}
