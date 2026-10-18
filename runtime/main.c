/*
 * main.c - start the recompiled game.
 *
 *   dsun [--game DIR] [--build DIR] [--headless] [--seconds N] [--shots DIR]
 *        [--input "SECONDS:ACTION ..."]
 *
 * --game is the folder with the game's data files (default game/ds1), --build
 * the one with image.bin and misses.txt (default build/ds1). The image is the
 * guest's memory as DOS would leave it at the program's first instruction,
 * every overlay already in place (tools/build_image.py).
 */
#include "runtime.h"
#include "layout.h"
#include <stdlib.h>
#include <string.h>

CPU *g_cpu;
const char *g_game_dir = "game/ds1";
const char *g_build_dir = "build/ds1";

int host_run(int headless, double seconds, const char *shots, const char *input);

static CPU g_cpu_state;

int game_main(void *arg)
{
    (void)arg;
    CPU *cpu = g_cpu;
    cpu->ds = cpu->es = GAME_PSP;
    cpu->ss = GAME_SS; cpu->sp = GAME_SP;
    cpu->cs = GAME_ENTRY_CS; cpu->ip = GAME_ENTRY_IP;
    cpu->flags = 0x0202;
    trace("[main] %s from %04X:%04X\n", GAME_EXE, cpu->cs, cpu->ip);
    if (!recomp_dispatch(cpu, GAME_ENTRY_CS, GAME_ENTRY_IP))
        fatal("no function at the entry point");
    fprintf(stderr, "[main] the start-up returned (halted=%d)\n", cpu->halted);
    extern void host_exit(int);
    host_exit(0);
    return 0;
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
