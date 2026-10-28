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
#include <setjmp.h>
#include <ctype.h>
#define SDL_MAIN_HANDLED          /* our main stays main; SDL must not rename it */
#include <SDL.h>

CPU *g_cpu;
const GameDesc *g_game;
const char *g_game_dir = NULL;
const char *g_build_dir = NULL;

int host_run(int headless, double seconds, const char *shots, const char *input);

static CPU g_cpu_state;

static jmp_buf g_tsr_jmp;
static int g_tsr_running;

void host_tsr_done(void)                   /* INT 21h AH=31h: the helper stays, the game may start */
{
    if (g_tsr_running) longjmp(g_tsr_jmp, 1);
    extern void host_exit(int);
    host_exit(0);
}

int game_main(void *arg)
{
    (void)arg;
    CPU *cpu = g_cpu;
    if (g_game->tsr_cs) {
        /* the mod's helper first, as `lh dsclog.exe` would run it */
        g_tsr_running = 1;
        dos_set_psp(g_game->tsr_psp);
        if (setjmp(g_tsr_jmp) == 0) {
            cpu->ds = cpu->es = g_game->tsr_psp;
            cpu->ss = g_game->tsr_ss; cpu->sp = g_game->tsr_sp;
            cpu->cs = g_game->tsr_cs; cpu->ip = g_game->tsr_ip;
            cpu->flags = 0x0202;
            trace("[main] helper from %04X:%04X\n", cpu->cs, cpu->ip);
            if (!recomp_dispatch(cpu, g_game->tsr_cs, g_game->tsr_ip))
                fatal("no function at the helper's entry point");
            fprintf(stderr, "[main] the helper returned without staying resident\n");
        }
        g_tsr_running = 0;
        dispatch_reset_depth();
        dos_set_psp(g_game->psp);
    }
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
 * then where it found the games before, then where GOG installs them, then
 * asks with a folder picker; and asks which game when it finds more than one. */
static long file_size(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 ? (long)st.st_size : -1;
}

static int is_game(const GameDesc *g) { return !strcmp(g->exe, "DSUN.EXE"); }   /* not the transfer utility */

static long exe_size_in(const char *dir, const char *exe)   /* the size of dir/exe, in any case */
{
    char path[1200], lower[64], cap[64];
    snprintf(lower, sizeof lower, "%s", exe); snprintf(cap, sizeof cap, "%s", exe);
    for (char *c = lower; *c; c++) *c = (char)tolower((unsigned char)*c);
    for (char *c = cap + 1; *c; c++) *c = (char)tolower((unsigned char)*c);
    const char *names[] = { exe, lower, cap };
    for (size_t i = 0; i < 3; i++) {
        snprintf(path, sizeof path, "%s/%s", dir, names[i]);
        long n = file_size(path);
        if (n >= 0) return n;
    }
    return -1;
}

static const GameDesc *game_in(const char *dir)
{
    long n = exe_size_in(dir, "DSUN.EXE");
    if (n < 0) return NULL;
    for (int g = 0; g < g_ngames; g++)
        if (is_game(g_games[g]) && (long)g_games[g]->exe_size == n) return g_games[g];
    fprintf(stderr, "%s/DSUN.EXE is %ld bytes: not a DSUN.EXE this program was built from\n", dir, n);
    return NULL;
}

static const GameDesc *by_tag(const char *tag)
{
    for (int g = 0; g < g_ngames; g++) if (!strcmp(g_games[g]->tag, tag)) return g_games[g];
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

/* ---- finding the games without being told -------------------------------------
 * In this order: game/<tag> beside the program or the current folder; the
 * folders remembered in dsun.ini beside the program (one line per game,
 * `ds1=<folder>`); GOG's usual install folders; and, with a display, a folder
 * picker. A folder found by the last two is remembered in dsun.ini. */
static const char *GOG_NAMES[] = { "Dark Sun Shattered Lands", "Dark Sun Wake of the Ravager" };
#ifdef _WIN32
static const char *GOG_ROOTS[] = { "GOG Games", "Program Files (x86)\\GOG Galaxy\\Games", "Program Files\\GOG Galaxy\\Games",
                                   "GOG Galaxy\\Games", "Games" };
#else
static const char *GOG_ROOTS[] = { "GOG Games", ".wine/drive_c/GOG Games", "Games", ".local/share/games" };
#endif

static void ini_path(char *out, size_t n) { snprintf(out, n, "%sdsun.ini", g_base); }

static const char *remembered(const char *tag)         /* dsun.ini's folder for a game, if any */
{
    static char line[1200];
    char path[1100]; ini_path(path, sizeof path);
    FILE *f = fopen(path, "r");
    if (!f) return NULL;
    const char *hit = NULL;
    while (fgets(line, sizeof line, f)) {
        size_t l = strlen(line);
        while (l && (line[l - 1] == '\n' || line[l - 1] == '\r' || line[l - 1] == ' ')) line[--l] = 0;
        size_t t = strlen(tag);
        if (!strncmp(line, tag, t) && line[t] == '=' && line[t + 1]) { hit = line + t + 1; break; }
    }
    fclose(f);
    return hit;
}

static void remember(const char *tag, const char *dir)   /* dsun.ini: this game's folder (the others' lines kept) */
{
    char path[1100]; ini_path(path, sizeof path);
    char keep[8][1200]; int nk = 0;
    FILE *f = fopen(path, "r");
    if (f) {
        char line[1200];
        while (fgets(line, sizeof line, f) && nk < 8)
            if (strncmp(line, tag, strlen(tag)) || line[strlen(tag)] != '=') snprintf(keep[nk++], sizeof keep[0], "%s", line);
        fclose(f);
    }
    f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "# Dark Sun Recompiled: where each game is (written when a game was found; edit or delete freely)\n");
    for (int i = 0; i < nk; i++) if (keep[i][0] != '#') fputs(keep[i], f);
    fprintf(f, "%s=%s\n", tag, dir);
    fclose(f);
    fprintf(stderr, "[main] %s remembered in %s\n", dir, path);
}

static const char *gog_folder(const GameDesc *g)       /* the game in one of GOG's usual places */
{
    static char buf[1300];
    const char *name = !strcmp(g->tag, "ds2") ? GOG_NAMES[1] : GOG_NAMES[0];
    for (size_t r = 0; r < sizeof GOG_ROOTS / sizeof *GOG_ROOTS; r++) {
#ifdef _WIN32
        for (char drive = 'C'; drive <= 'H'; drive++) {
            snprintf(buf, sizeof buf, "%c:\\%s\\%s", drive, GOG_ROOTS[r], name);
            if (game_in(buf) == g) return buf;
        }
#else
        const char *home = getenv("HOME");
        if (!home) continue;
        snprintf(buf, sizeof buf, "%s/%s/%s", home, GOG_ROOTS[r], name);
        if (game_in(buf) == g) return buf;
#endif
    }
    return NULL;
}

#ifdef _WIN32
#include <windows.h>
#include <shlobj.h>
static const char *pick_folder(void)
{
    static char path[MAX_PATH];
    CoInitialize(NULL);
    BROWSEINFOA bi = {0};
    bi.lpszTitle = "Where is Dark Sun installed? Pick the GOG folder with DSUN.EXE in it.";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    LPITEMIDLIST idl = SHBrowseForFolderA(&bi);
    if (!idl || !SHGetPathFromIDListA(idl, path)) return NULL;
    return path;
}
#else
static const char *pick_folder(void)                   /* zenity or kdialog, when one is installed */
{
    static char path[1200];
    const char *cmds[] = {
        "zenity --file-selection --directory --title='Where is Dark Sun installed? Pick the GOG folder with DSUN.EXE in it.' 2>/dev/null",
        "kdialog --getexistingdirectory \"$HOME\" --title 'Where is Dark Sun installed?' 2>/dev/null" };
    for (size_t i = 0; i < sizeof cmds / sizeof *cmds; i++) {
        FILE *p = popen(cmds[i], "r");
        if (!p) continue;
        char *got = fgets(path, sizeof path, p);
        int rc = pclose(p);
        if (got && rc == 0) {
            size_t l = strlen(path);
            while (l && (path[l - 1] == '\n' || path[l - 1] == '/')) path[--l] = 0;
            return path;
        }
        if (rc != 127 * 256) return NULL;                /* the dialog ran and was cancelled */
    }
    return NULL;
}
#endif

static void say(int headless, const char *text)
{
    fputs(text, stderr); fputc('\n', stderr);
    if (!headless) { SDL_Init(SDL_INIT_VIDEO); SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION, "Dark Sun Recompiled", text, NULL); }
}

static const char *locate(const GameDesc *g)           /* the game's folder, by the search order above */
{
    char rel[64];
    snprintf(rel, sizeof rel, "game/%s", g->tag);
    const char *d = find_dir(rel);
    if (d && game_in(d) == g) return strdup(d);
    d = remembered(g->tag);
    if (d && game_in(d) == g) return strdup(d);
    d = gog_folder(g);
    if (d) { remember(g->tag, d); return strdup(d); }
    return NULL;
}

/* The character transfer utility (CHARTRAN.EXE, in Wake of the Ravager's
 * folder, built in as "ct"): it wants both games, as C:\DSUN and C:\RAVAGER,
 * and writes the party it makes into Wake of the Ravager's CHARSAVE.GFF. */
static const GameDesc *transfer_setup(const char *ds1, const char *ds2, int headless)
{
    const GameDesc *ct = by_tag("ct");
    if (!ct) { say(headless, "This program was built without the character transfer utility (build/ct)."); return NULL; }
    const GameDesc *g1 = by_tag("ds1"), *g2 = by_tag("ds2");
    if (!ds1 && g1) ds1 = locate(g1);
    if (!ds2 && g2) ds2 = locate(g2);
    if (!ds1 || !ds2) {
        say(headless, "The character transfer needs both games: Shattered Lands (--ds1 <folder>) and Wake of the Ravager (--ds2 <folder>), or both installed where this program finds them.");
        return NULL;
    }
    if (exe_size_in(ds2, ct->exe) != (long)ct->exe_size) {
        char msg[1500];
        snprintf(msg, sizeof msg, "%s has no %s of %u bytes (GOG's): the transfer utility this program was built from.", ds2, ct->exe, ct->exe_size);
        say(headless, msg);
        return NULL;
    }
    g_game_dir = ds2;
    dos_mount("DSUN", ds1);
    dos_mount("RAVAGER", ds2);
    fprintf(stderr, "[main] character transfer: C:\\DSUN is %s, C:\\RAVAGER is %s\n", ds1, ds2);
    return ct;
}

static const GameDesc *choose_game(int headless)
{
    const GameDesc *found[8]; const char *dirs[8]; int n = 0;
    for (int g = 0; g < g_ngames && n < 8; g++) {
        if (!is_game(g_games[g])) continue;
        const char *d = locate(g_games[g]);
        if (d) { found[n] = g_games[g]; dirs[n++] = d; }
    }
    if (n == 0 && !headless) {
        const char *d = pick_folder();
        if (d) {
            const GameDesc *g = game_in(d);
            if (g) { remember(g->tag, d); found[n] = g; dirs[n++] = strdup(d); }
            else {
                char msg[1500];
                snprintf(msg, sizeof msg, "%s has no DSUN.EXE this program knows. Pick the GOG folder of Dark Sun: Shattered Lands or Wake of the Ravager, the one with DSUN.EXE in it.", d);
                say(headless, msg);
                return NULL;
            }
        }
    }
    if (n == 0) {
        char msg[2000];
        int k = snprintf(msg, sizeof msg, "No game found. Install Dark Sun from GOG, or start this program with --game <folder> (the folder with DSUN.EXE), or put the game in game/ds1 (Shattered Lands) or game/ds2 (Wake of the Ravager) beside it. This program has:\n");
        for (int g = 0; g < g_ngames && k < (int)sizeof msg - 100; g++)
            k += snprintf(msg + k, sizeof msg - k, "  %s (%s, %u bytes)\n", g_games[g]->title, g_games[g]->exe, g_games[g]->exe_size);
        say(headless, msg);
        return NULL;
    }
    int pick = 0;
    const char *want = getenv("DS_GAME");
    if (want) for (int i = 0; i < n; i++) if (!strcmp(found[i]->tag, want)) pick = i;
    if (want && !strcmp(want, "ct")) return transfer_setup(NULL, NULL, headless);
    if (n > 1 && !want && !headless) {
        /* both games there: the transfer utility is offered too, when built in */
        int nb = n + (by_tag("ct") != NULL);
        SDL_MessageBoxButtonData buttons[9];
        for (int i = 0; i < nb; i++) {
            buttons[i].flags = i == 0 ? SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT : 0;
            buttons[i].buttonid = i; buttons[i].text = i < n ? found[i]->title : "Transfer a party (Shattered Lands to Wake)";
        }
        SDL_MessageBoxData box = { SDL_MESSAGEBOX_INFORMATION, NULL, "Dark Sun Recompiled", "Which game?", nb, buttons, NULL };
        int id = 0;
        SDL_Init(SDL_INIT_VIDEO);
        if (SDL_ShowMessageBox(&box, &id) == 0 && id >= 0 && id < nb) pick = id;
        if (pick == n) return transfer_setup(NULL, NULL, headless);
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
    int transfer = 0; const char *ds1 = NULL, *ds2 = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--game") && i + 1 < argc) g_game_dir = argv[++i];
        else if (!strcmp(argv[i], "--transfer")) transfer = 1;
        else if (!strcmp(argv[i], "--ds1") && i + 1 < argc) { ds1 = argv[++i]; transfer = 1; }
        else if (!strcmp(argv[i], "--ds2") && i + 1 < argc) { ds2 = argv[++i]; transfer = 1; }
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
    if (transfer) g_game = transfer_setup(ds1, ds2, headless);
    else if (g_game_dir) g_game = game_in(g_game_dir);
    else g_game = choose_game(headless);
    if (!g_game) return 1;
    char build_rel[64], cd_rel[1200];
    if (!g_build_dir) {
        snprintf(build_rel, sizeof build_rel, "build/%s", g_game->build);
        g_build_dir = find_dir(build_rel);
        if (!g_build_dir) { fprintf(stderr, "cannot find %s (the folder with image.bin from tools/build_image.py)\n", build_rel); return 1; }
    }
    { extern const char *g_cd_dir;
      if (!g_cd_dir && g_game->cd_sub[0]) {
          snprintf(cd_rel, sizeof cd_rel, "%s/%s", g_game_dir, g_game->cd_sub);
          struct stat st;
          if (stat(cd_rel, &st) != 0) {
              /* the CD's files are not unpacked yet: do it from GOG's image (once; a minute or so) */
              extern int iso_extract(const char *, const char *);
              char gog[1200]; snprintf(gog, sizeof gog, "%s/game.gog", g_game_dir);
              if (stat(gog, &st) == 0) {
                  fprintf(stderr, "[main] unpacking the CD's files from %s into %s (once)\n", gog, cd_rel);
                  int n = iso_extract(gog, cd_rel);
                  if (n > 0) fprintf(stderr, "[main] %d files unpacked\n", n);
              } else fprintf(stderr, "[main] no %s and no game.gog: the CD's files are missing\n", cd_rel);
          }
          if (stat(cd_rel, &st) == 0) g_cd_dir = cd_rel;
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
