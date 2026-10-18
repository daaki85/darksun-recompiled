/*
 * cd.c - the CD-ROM's audio side: MSCDEX device requests and Red Book playback.
 *
 * Wake of the Ravager's music is 40 CD audio tracks, which GOG ships as
 * MUSIC/TrackNN.ogg beside the data track image. The game talks to the CD
 * through MSCDEX's "send device request" (INT 2Fh AX=1510h): IOCTL reads for
 * the disc's table of contents and the drive's status, PLAY AUDIO with a Red
 * Book start and length, STOP, RESUME. The table of contents is built from
 * the OGG files' lengths (track 1 is the data image); playback decodes the
 * track with stb_vorbis and is mixed in by audio.c's render loop.
 */
#include "runtime.h"
#include <stdlib.h>
#include <string.h>
#include <SDL.h>

#define STB_VORBIS_NO_PUSHDATA_API
#define STB_VORBIS_NO_INTEGER_CONVERSION
#include "stb_vorbis.c"

#define MAXTRACK 100
#define FPS 75                      /* frames per second on a CD */
#define PREGAP 150                  /* the two seconds before track 1 in Red Book */

static struct { char path[1024]; unsigned start, frames; int data; } g_tr[MAXTRACK];
static int g_ntr, g_first = 1, g_last;
static unsigned g_leadout;

/* playback (shared with the audio thread) */
static SDL_mutex *g_lock;
static stb_vorbis *g_v;
static int g_vrate, g_vch, g_playing, g_paused, g_track;
static unsigned g_play_start, g_play_end, g_pos_frames; /* in CD frames, absolute */
static double g_pos_samples;                            /* within the track */
static float g_buf[4096 * 2]; static int g_bufn, g_bufi;
static double g_step_acc;
static float g_last_l, g_last_r;

int dos_host_path(const char *dos, char *out, size_t n, int must_exist);

static unsigned redbook(unsigned f)         /* frame -> 00:MM:SS:FF */
{
    return ((f / (60 * FPS)) << 16) | (((f / FPS) % 60) << 8) | (f % FPS);
}
static unsigned from_redbook(unsigned r)
{
    return (r >> 16 & 0xFF) * 60 * FPS + (r >> 8 & 0xFF) * FPS + (r & 0xFF);
}

void cd_init(void)
{
    extern const char *g_cd_dir;
    if (!g_cd_dir) return;
    g_lock = SDL_CreateMutex();
    char path[1024];
    unsigned at = PREGAP;
    /* track 1: the data image, if it is still beside the game */
    g_tr[1].data = 1; g_tr[1].start = at;
    g_tr[1].frames = 1;
    if (dos_host_path("C:\\game.gog", path, sizeof path, 1)) {
        FILE *f = fopen(path, "rb");
        if (f) { fseek(f, 0, SEEK_END); long n = ftell(f); fclose(f); if (n > 0) g_tr[1].frames = (unsigned)(n / 2352); }
    }
    at += g_tr[1].frames;
    g_last = 1;
    for (int t = 2; t < MAXTRACK; t++) {
        char dos[64];
        snprintf(dos, sizeof dos, "C:\\MUSIC\\Track%02d.ogg", t);
        if (!dos_host_path(dos, path, sizeof path, 1)) break;
        int err = 0;
        stb_vorbis *v = stb_vorbis_open_filename(path, &err, NULL);
        if (!v) { fprintf(stderr, "[cd] cannot read %s (stb_vorbis error %d)\n", path, err); break; }
        stb_vorbis_info info = stb_vorbis_get_info(v);
        unsigned samples = stb_vorbis_stream_length_in_samples(v);
        stb_vorbis_close(v);
        snprintf(g_tr[t].path, sizeof g_tr[t].path, "%s", path);
        g_tr[t].start = at;
        g_tr[t].frames = (unsigned)((uint64_t)samples * FPS / info.sample_rate) + 1;
        at += g_tr[t].frames;
        g_last = t;
    }
    g_leadout = at;
    g_ntr = g_last;
    if (getenv("DS_TRACE_CD"))
        for (int t = 1; t <= g_last; t++) fprintf(stderr, "[cd] track %2d at %6u (%02u:%02u:%02u) %6u frames\n", t, g_tr[t].start,
                                                  g_tr[t].start / 4500, g_tr[t].start / 75 % 60, g_tr[t].start % 75, g_tr[t].frames);
    trace("[cd] %d tracks, %u frames (%u:%02u)\n", g_last, g_leadout, g_leadout / (60 * FPS), (g_leadout / FPS) % 60);
}

static int track_of(unsigned frame)
{
    for (int t = g_last; t >= 1; t--) if (frame >= g_tr[t].start) return t;
    return 1;
}

static void stop_locked(void)
{
    if (g_v) { stb_vorbis_close(g_v); g_v = NULL; }
    g_playing = 0; g_paused = 0; g_bufn = g_bufi = 0;
}

static void play_from(unsigned frame, unsigned end)
{
    SDL_LockMutex(g_lock);
    stop_locked();
    int t = track_of(frame);
    g_track = t; g_play_start = frame; g_play_end = end; g_pos_frames = frame;
    if (!g_tr[t].data && g_tr[t].path[0]) {
        int err = 0;
        g_v = stb_vorbis_open_filename(g_tr[t].path, &err, NULL);
        if (g_v) {
            stb_vorbis_info info = stb_vorbis_get_info(g_v);
            g_vrate = info.sample_rate; g_vch = info.channels;
            unsigned off = (unsigned)((uint64_t)(frame - g_tr[t].start) * g_vrate / FPS);
            if (off) stb_vorbis_seek(g_v, off);
            g_pos_samples = off;
            g_playing = 1;
        }
    }
    SDL_UnlockMutex(g_lock);
    trace("[cd] play track %d from %u for %u frames%s\n", t, frame, end - frame, g_v ? "" : " (no audio file)");
}

/* One stereo sample at the mixer's rate; silence when nothing plays. */
void cd_sample(unsigned rate, int *l, int *r)
{
    *l = *r = 0;
    if (!g_playing || g_paused) return;
    if (SDL_TryLockMutex(g_lock) != 0) { *l = (int)g_last_l; *r = (int)g_last_r; return; }
    if (g_v) {
        g_step_acc += (double)g_vrate / rate;
        while (g_step_acc >= 1.0) {
            g_step_acc -= 1.0;
            if (g_bufi >= g_bufn) {
                g_bufn = stb_vorbis_get_samples_float_interleaved(g_v, 2, g_buf, 4096 * 2) ;
                g_bufi = 0;
                if (g_bufn <= 0) { g_bufn = 0; g_last_l = g_last_r = 0; break; }
            }
            g_last_l = g_buf[2 * g_bufi] * 28000.0f; g_last_r = g_buf[2 * g_bufi + 1] * 28000.0f;
            g_bufi++; g_pos_samples += 1;
        }
        g_pos_frames = g_tr[g_track].start + (unsigned)(g_pos_samples * FPS / g_vrate);
        int ended = (g_bufn == 0 && g_bufi >= g_bufn && g_pos_frames + 1 >= g_tr[g_track].start + g_tr[g_track].frames) || g_pos_frames >= g_play_end;
        if (ended) {
            /* a play spanning several tracks goes on into the next */
            unsigned next = g_tr[g_track].start + g_tr[g_track].frames;
            int t = track_of(next);
            if (next < g_play_end && t > g_track && !g_tr[t].data && g_tr[t].path[0]) {
                stb_vorbis_close(g_v); g_v = NULL;
                int err = 0;
                g_v = stb_vorbis_open_filename(g_tr[t].path, &err, NULL);
                g_track = t; g_pos_samples = 0; g_pos_frames = next; g_bufn = g_bufi = 0;
                if (g_v) { stb_vorbis_info info = stb_vorbis_get_info(g_v); g_vrate = info.sample_rate; }
                else g_playing = 0;
            } else {
                stop_locked();
                g_pos_frames = g_play_end;
            }
        }
    }
    *l = (int)g_last_l; *r = (int)g_last_r;
    SDL_UnlockMutex(g_lock);
}

/* ---- MSCDEX INT 2Fh AX=1510h: a device request block at ES:BX ------------------ */
static void cd_put32(CPU *cpu, unsigned lin, unsigned v) { for (int i = 0; i < 4; i++) cpu->mem[lin + i] = (uint8_t)(v >> (8 * i)); }
static unsigned cd_get32(CPU *cpu, unsigned lin) { return cpu->mem[lin] | cpu->mem[lin + 1] << 8 | cpu->mem[lin + 2] << 16 | (unsigned)cpu->mem[lin + 3] << 24; }

void cd_device_request(CPU *cpu)
{
    unsigned hdr = ((cpu->es & 0xFFFF) << 4) + cpu->bx;
    int cmd = cpu->mem[hdr + 2];
    unsigned status = 0x0100;                         /* done */
    static int verbose = -1;
    if (verbose < 0) verbose = getenv("DS_TRACE_CD") != NULL;
    if (verbose) {
        fprintf(stderr, "[cd] request cmd %d", cmd);
        if (cmd == 3 || cmd == 12) { unsigned tb = cd_get32(cpu, hdr + 14); unsigned ctl = ((tb >> 16) << 4) + (tb & 0xFFFF);
            fprintf(stderr, " ioctl code %02X arg %02X", cpu->mem[ctl], cpu->mem[ctl + 1]); }
        if (cmd == 132) fprintf(stderr, " mode %d start %08X n %u", cpu->mem[hdr + 13], cd_get32(cpu, hdr + 14), cd_get32(cpu, hdr + 18));
        fprintf(stderr, "\n");
    }
    switch (cmd) {
    case 3: case 12: {                                /* IOCTL input / output */
        unsigned tb = cd_get32(cpu, hdr + 14);
        unsigned ctl = ((tb >> 16) << 4) + (tb & 0xFFFF);
        int code = cpu->mem[ctl];
        if (cmd == 3) switch (code) {
        case 0: cd_put32(cpu, ctl + 1, (unsigned)BIOS_SEG << 16 | 0x0000); break;   /* device header: somewhere in the BIOS */
        case 1: { cpu->mem[ctl + 1] = 1; unsigned f = g_pos_frames; cd_put32(cpu, ctl + 2, redbook(f)); break; }   /* head location (Red Book) */
        case 6: cd_put32(cpu, ctl + 1, 0x00000210); break;          /* audio and Red Book addressing supported; door closed */
        case 7: cpu->mem[ctl + 1] = 0; cpu->mem[ctl + 2] = 0x00; cpu->mem[ctl + 3] = 0x08; break;   /* 2048-byte sectors */
        case 8: cd_put32(cpu, ctl + 1, g_leadout); break;
        case 9: cpu->mem[ctl + 1] = 1; break;                    /* media not changed */
        case 0x0A: cpu->mem[ctl + 1] = (uint8_t)g_first; cpu->mem[ctl + 2] = (uint8_t)g_last; cd_put32(cpu, ctl + 3, redbook(g_leadout)); break;
        case 0x0B: { int t = cpu->mem[ctl + 1];
            if (t >= 1 && t <= g_last) { cd_put32(cpu, ctl + 2, redbook(g_tr[t].start)); cpu->mem[ctl + 6] = g_tr[t].data ? 0x40 : 0x00; }
            else status = 0x810C; break; }
        case 0x0C: { unsigned f = g_pos_frames; int t = track_of(f);
            cpu->mem[ctl + 1] = g_tr[t].data ? 0x41 : 0x01; cpu->mem[ctl + 2] = (uint8_t)(((t / 10) << 4) | (t % 10)); cpu->mem[ctl + 3] = 1;
            unsigned rel = f - g_tr[t].start;
            cpu->mem[ctl + 4] = (uint8_t)(rel / (60 * FPS)); cpu->mem[ctl + 5] = (uint8_t)((rel / FPS) % 60); cpu->mem[ctl + 6] = (uint8_t)(rel % FPS);
            cpu->mem[ctl + 7] = 0;
            cpu->mem[ctl + 8] = (uint8_t)(f / (60 * FPS)); cpu->mem[ctl + 9] = (uint8_t)((f / FPS) % 60); cpu->mem[ctl + 10] = (uint8_t)(f % FPS);
            break; }
        case 0x0F: { cpu->mem[ctl + 1] = (uint8_t)(g_paused ? 1 : 0); cpu->mem[ctl + 2] = 0;
            cd_put32(cpu, ctl + 3, redbook(g_play_start)); cd_put32(cpu, ctl + 7, redbook(g_play_end)); break; }
        default: trace("[cd] IOCTL input code %02X not answered\n", code); status = 0x8103; break;
        } else switch (code) {
        case 0: case 1: case 2: case 3: break;        /* eject, lock, reset, close: nothing to do */
        default: trace("[cd] IOCTL output code %02X ignored\n", code); break;
        }
        if (g_playing && !g_paused) status |= 0x0200;              /* busy */
        break; }
    case 132: {                                       /* play audio */
        int mode = cpu->mem[hdr + 13];
        unsigned start = cd_get32(cpu, hdr + 14), n = cd_get32(cpu, hdr + 18);
        /* HSG sectors count from the data; Red Book from two seconds before it */
        if (mode == 1) start = from_redbook(start); else start += PREGAP;
        if (n == 0) { SDL_LockMutex(g_lock); stop_locked(); SDL_UnlockMutex(g_lock); }
        else play_from(start, start + n);
        break; }
    case 133:                                         /* stop audio (pause if playing) */
        SDL_LockMutex(g_lock);
        if (g_playing) g_paused = 1; else stop_locked();
        SDL_UnlockMutex(g_lock);
        break;
    case 136:                                         /* resume */
        SDL_LockMutex(g_lock);
        if (g_playing) g_paused = 0;
        SDL_UnlockMutex(g_lock);
        break;
    case 128: case 130: case 131: case 134: case 135: /* reads and seeks: the files come through DOS */
        break;
    default:
        trace("[cd] device command %d not answered\n", cmd);
        status = 0x8103;
        break;
    }
    if (g_playing && !g_paused && cmd != 3 && cmd != 12) status |= 0x0200;
    cpu->mem[hdr + 3] = (uint8_t)status; cpu->mem[hdr + 4] = (uint8_t)(status >> 8);
}

void cd_report(void) {}
