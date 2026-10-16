/*
 * audio.c - the sound card's output: an OPL3 (Nuked OPL3) behind the FM
 * registers the translated music driver writes, mixed to the host through
 * SDL.
 *
 * The driver writes registers from the game's 120 Hz timer; each write is
 * queued with its time, and the audio callback renders the chip up to each
 * write's moment before applying it, so what is heard keeps the timing the
 * driver gave it. The render clock runs a little behind real time (the
 * latency below), which is what makes that possible.
 */
#include "runtime.h"
#include "opl3.h"
#include <SDL.h>
#include <string.h>

#define RATE 49716                 /* the OPL3's own sample rate */
#define LATENCY_US 60000
#define QUEUE 8192

typedef struct { uint64_t t; uint16_t reg; uint8_t val; } RegWrite;
static RegWrite g_q[QUEUE];
static volatile unsigned g_qr, g_qw;
static opl3_chip g_chip;
static SDL_AudioDeviceID g_dev;
static uint64_t g_render_t;        /* host time the rendering has reached */
static int g_on;

void audio_opl_write(int bank, uint8_t reg, uint8_t val)
{
    unsigned w = g_qw, n = (w + 1) % QUEUE;
    if (n == g_qr) return;                      /* no listener: drop */
    g_q[w].t = host_us();
    g_q[w].reg = (uint16_t)((bank << 8) | reg);
    g_q[w].val = val;
    g_qw = n;
}

static void render(int16_t *out, int frames)
{
    uint64_t now = host_us();
    if (!g_render_t) g_render_t = now > LATENCY_US ? now - LATENCY_US : 0;
    for (int i = 0; i < frames; i++) {
        uint64_t t = g_render_t + (uint64_t)i * 1000000u / RATE;
        while (g_qr != g_qw && g_q[g_qr].t <= t) {
            OPL3_WriteRegBuffered(&g_chip, g_q[g_qr].reg, g_q[g_qr].val);
            g_qr = (g_qr + 1) % QUEUE;
        }
        OPL3_Generate(&g_chip, out + 2 * i);
    }
    g_render_t += (uint64_t)frames * 1000000u / RATE;
    /* never fall further behind than two latencies: skip ahead */
    if (now > g_render_t + 2 * LATENCY_US) g_render_t = now - LATENCY_US;
}

static void callback(void *ud, Uint8 *stream, int len)
{
    (void)ud;
    render((int16_t *)stream, len / 4);
}

/* --wav FILE: the output goes to a file as well (or instead, with no device),
 * rendered from the host loop. The WAV header is finished on exit. */
static FILE *g_wav;
static uint32_t g_wav_bytes;

static void wav_header(FILE *f, uint32_t bytes)
{
    uint8_t h[44] = "RIFF\0\0\0\0WAVEfmt \x10\0\0\0\x01\0\x02\0";
    uint32_t v;
    v = 36 + bytes; memcpy(h + 4, &v, 4);
    v = RATE; memcpy(h + 24, &v, 4);
    v = RATE * 4; memcpy(h + 28, &v, 4);
    h[32] = 4; h[34] = 16; memcpy(h + 36, "data", 4); memcpy(h + 40, &bytes, 4);
    fseek(f, 0, SEEK_SET); fwrite(h, 1, 44, f);
}

int audio_wav_open(const char *path)
{
    g_wav = fopen(path, "wb");
    if (!g_wav) return 0;
    wav_header(g_wav, 0);
    if (!g_on) { OPL3_Reset(&g_chip, RATE); g_on = 2; }
    return 1;
}

void audio_pump(void)
{
    if (!g_wav || g_on != 2) return;             /* a device renders on its own */
    uint64_t now = host_us();
    if (!g_render_t) g_render_t = now > LATENCY_US ? now - LATENCY_US : 0;
    int64_t behind = (int64_t)now - (int64_t)LATENCY_US - (int64_t)g_render_t;
    int64_t due = behind > 0 ? behind * RATE / 1000000 : 0;
    static int16_t buf[4096 * 2];
    while (due > 0) {
        int n = due > 4096 ? 4096 : (int)due;
        if (g_dev) SDL_LockAudioDevice(g_dev);
        render(buf, n);
        if (g_dev) SDL_UnlockAudioDevice(g_dev);
        fwrite(buf, 4, (size_t)n, g_wav);
        g_wav_bytes += (uint32_t)n * 4;
        due -= n;
    }
}

void audio_close(void)
{
    if (!g_wav) return;
    wav_header(g_wav, g_wav_bytes);
    fclose(g_wav);
    g_wav = NULL;
}

int audio_init(void)
{
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
        trace("[audio] no audio: %s\n", SDL_GetError());
        return 0;
    }
    OPL3_Reset(&g_chip, RATE);
    SDL_AudioSpec want = {0}, have;
    want.freq = RATE; want.format = AUDIO_S16SYS; want.channels = 2;
    want.samples = 1024; want.callback = callback;
    g_dev = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (!g_dev) { trace("[audio] cannot open a device: %s\n", SDL_GetError()); return 0; }
    SDL_PauseAudioDevice(g_dev, 0);
    g_on = 1;
    trace("[audio] OPL3 at %d Hz, %d-frame buffer\n", have.freq, have.samples);
    return 1;
}

int audio_on(void) { return g_on; }
