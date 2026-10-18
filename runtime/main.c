/*
 * main.c - start the recompiled game.
 *
 *   dsun [--game DIR] [--build DIR] [--headless] [--seconds N] [--shots DIR]
 *        [--input "SECONDS:ACTION ..."]
 *
 * --game is the folder with the game's data files; the game is recognised by
 * the size of its DSUN.EXE. --build is the folder with image.bin and
 * misses.txt (default build/<tag>, beside the current folder or the program).
 * Without --game, game/ds1 and game/ds2 are looked for in the same places and
 * a message box asks when both are there. The image is the guest's memory as
 * DOS would leave it at the program's first instruction, every overlay already
 * in place (tools/build_image.py).
 */
#include "runtime.h"
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <SDL.h>

CPU *g_cpu;
const GameDesc *g_game;
const char *g_game_dir = NULL;
const char *g_build_dir = NULL;

int host_run(int headless, double seconds, const char *shots, const char *input);

static CPU g_cpu_state;

int game_main(void *arg)
{
    (void)arg;
    CPU *cpu = g_cpu;
    cpu->ds = cpu->es = g_game->psp;
    cpu->ss = g_game->ss; cpu->sp = g_game->sp;
    cpu->cs = g_game->entry_cs; cpu->ip = g_game->entry_ip;
    cpu->flags = 0x0202;
    trace("[main] %s (%s) from %04X:%04X\n", g_game->exe, g_game->title, cpu->cs, cpu->ip);
    if (!recomp_dispatch(cpu, g_game->entry_cs, g_game->entry_ip))
        fatal("no function at the entry point");
    fprintf(stderr, "[main] the start-up returned (halted=%d)\n", cpu->halted);
    extern void host_exit(int);
    host_exit(0);
    return 0;
}

/* ---- which game ----------------------------------------------------------------
 * A game folder is recognised by the size of its DSUN.EXE. Without --game the
 * program looks for game/<tag> beside the current folder and beside itself,
 * and asks when it finds more than one. */
static long file_size(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 ? (long)st.st_size : -1;
}

static const GameDesc *game_in(const char *dir)
{
    static const char *names[] = { "DSUN.EXE", "dsun.exe", "Dsun.exe" };
    char path[1200];
    for (size_t i = 0; i < sizeof names / sizeof *names; i++) {
        snprintf(path, sizeof path, "%s/%s", dir, names[i]);
        long n = file_size(path);
        if (n < 0) continue;
        for (int g = 0; g < g_ngames; g++)
            if ((long)g_games[g]->exe_size == n) return g_games[g];
        fprintf(stderr, "%s is %ld bytes: not a DSUN.EXE this program was built from\n", path, n);
        return NULL;
    }
    return NULL;
}

static char g_base[1024];                      /* the folder the program is in */

static const char *find_dir(const char *rel)   /* rel, or rel beside the program, if it exists */
{
    static char buf[2200];
    struct stat st;
    if (stat(rel, &st) == 0) return rel;
    snprintf(buf, sizeof buf, "%s%s", g_base, rel);
    if (stat(buf, &st) == 0) return buf;
    return NULL;
}

static const GameDesc *choose_game(int headless)
{
    const GameDesc *found[8]; const char *dirs[8]; int n = 0;
    for (int g = 0; g < g_ngames && n < 8; g++) {
        char rel[64];
        snprintf(rel, sizeof rel, "game/%s", g_games[g]->tag);
        const char *d = find_dir(rel);
        if (d && game_in(d) == g_games[g]) { found[n] = g_games[g]; dirs[n++] = strdup(d); }
    }
    if (n == 0) {
        fprintf(stderr, "No game found. Give the folder of your GOG install with --game <folder>; this program has:\n");
        for (int g = 0; g < g_ngames; g++) fprintf(stderr, "  %s (%s, %u bytes)\n", g_games[g]->title, g_games[g]->exe, g_games[g]->exe_size);
        return NULL;
    }
    int pick = 0;
    const char *want = getenv("DS_GAME");
    if (want) for (int i = 0; i < n; i++) if (!strcmp(found[i]->tag, want)) pick = i;
    if (n > 1 && !want && !headless) {
        SDL_MessageBoxButtonData buttons[8];
        for (int i = 0; i < n; i++) {
            buttons[i].flags = i == 0 ? SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT : 0;
            buttons[i].buttonid = i; buttons[i].text = found[i]->title;
        }
        SDL_MessageBoxData box = { SDL_MESSAGEBOX_INFORMATION, NULL, "Dark Sun Recompiled", "Which game?", n, buttons, NULL };
        int id = 0;
        SDL_Init(SDL_INIT_VIDEO);
        if (SDL_ShowMessageBox(&box, &id) == 0 && id >= 0 && id < n) pick = id;
    }
    g_game_dir = dirs[pick];
    return found[pick];
}

int main(int argc, char **argv)
{
#ifdef _WIN32
    freopen("dsun.log", "w", stderr);        /* no terminal: the log goes to a file */
    setvbuf(stderr, NULL, _IOLBF, 0);
#endif
    int headless = 0;
    double seconds = 0;
    const char *shots = NULL, *input = NULL, *wav = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--game") && i + 1 < argc) g_game_dir = argv[++i];
        else if (!strcmp(argv[i], "--build") && i + 1 < argc) g_build_dir = argv[++i];
        else if (!strcmp(argv[i], "--headless")) headless = 1;
        else if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atof(argv[++i]);
        else if (!strcmp(argv[i], "--shots") && i + 1 < argc) shots = argv[++i];
        else if (!strcmp(argv[i], "--input") && i + 1 < argc) input = argv[++i];
        else if (!strcmp(argv[i], "--wav") && i + 1 < argc) wav = argv[++i];
        else if (!strcmp(argv[i], "--cd") && i + 1 < argc) { extern const char *g_cd_dir; g_cd_dir = argv[++i]; }
        else { fprintf(stderr, "unknown argument %s\n", argv[i]); return 2; }
    }
    if (!getenv("DISPLAY") && !getenv("WAYLAND_DISPLAY")) {
#ifndef _WIN32
        headless = 1;
#endif
    }
    { char *b = SDL_GetBasePath(); if (b) { snprintf(g_base, sizeof g_base, "%s", b); SDL_free(b); } }
    if (g_game_dir) g_game = game_in(g_game_dir);
    else g_game = choose_game(headless);
    if (!g_game) return 1;
    char build_rel[64], cd_rel[1200];
    if (!g_build_dir) {
        snprintf(build_rel, sizeof build_rel, "build/%s", g_game->tag);
        g_build_dir = find_dir(build_rel);
        if (!g_build_dir) { fprintf(stderr, "cannot find %s (the folder with image.bin from tools/build_image.py)\n", build_rel); return 1; }
    }
    { extern const char *g_cd_dir;
      if (!g_cd_dir && g_game->cd_sub[0]) {
          snprintf(cd_rel, sizeof cd_rel, "%s/%s", g_game_dir, g_game->cd_sub);
          struct stat st;
          if (stat(cd_rel, &st) == 0) g_cd_dir = cd_rel;
          else fprintf(stderr, "[main] no %s: the CD's files are missing (tools/cd_extract.py)\n", cd_rel);
      } }
    fprintf(stderr, "[main] %s: game %s, build %s\n", g_game->title, g_game_dir, g_build_dir);
    g_cpu = &g_cpu_state;
    cpu_init(g_cpu);
    if (cpu_alloc_mem(g_cpu)) return 1;
    char path[1024];
    snprintf(path, sizeof path, "%s/image.bin", g_build_dir);
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open %s (run tools/build_image.py)\n", path); return 1; }
    size_t n = fread(g_cpu->mem, 1, MEM_SIZE, f);
    fclose(f);
    if (n != MEM_SIZE) { fprintf(stderr, "%s is short\n", path); return 1; }
    bios_init(g_cpu);
    dos_init(g_cpu);
    vga_init();
    { extern void cd_init(void); cd_init(); }
    { extern int audio_init(void); extern int audio_wav_open(const char *);
      if (!getenv("DS_NO_AUDIO")) audio_init();
      if (wav && !audio_wav_open(wav)) fprintf(stderr, "cannot write %s\n", wav); }
    return host_run(headless, seconds, shots, input);
}

int cpu_alloc_mem(CPU *cpu)
{
    cpu->mem = calloc(1, MEM_SIZE);
    return cpu->mem ? 0 : -1;
}
