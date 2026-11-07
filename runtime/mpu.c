/* An MPU-401 MIDI interface at port 330h, with a Roland MT-32 behind it: Munt's
 * mt32emu, fed the MIDI bytes the game's MT-32 driver (ADV 2, mt32mpu.adv) writes,
 * rendered into the mixer (audio.c) beside the OPL and the digital sound.
 *
 * The MT-32's two ROMs are the player's own (MT32_CONTROL.ROM and MT32_PCM.ROM, or
 * a CM-32L's), named by their folder in dsun.ini (mt32roms=) or DS_MT32_ROMS: with
 * them the runtime's SOUND.CFG stand-in chooses the MT-32 driver (dos.c); without,
 * the port answers nothing and the game keeps its FM music.
 *
 * The interface runs in UART mode, as Miles's driver puts it: a command on 331h
 * (FFh reset, 3Fh UART) is acknowledged with FEh on 330h; data written to 330h is
 * MIDI. Status (331h): bit 7 clear when a byte waits, bit 6 clear when one may be
 * written. */
#include "runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef DS_MT32
#include <mt32emu/mt32emu.h>
#endif

static int g_mpu_on;                 /* the ROMs loaded: the port answers */
static int g_ack_pending;            /* FEh waiting on the data port */
static unsigned g_msg, g_msg_len, g_msg_need;   /* the MIDI message being assembled */
static unsigned char g_sysex[1024]; static unsigned g_sysex_len; static int g_in_sysex;
static unsigned g_running;           /* running status */
static unsigned long g_bytes, g_msgs, g_sysexes;
#ifdef DS_MT32
static mt32emu_context g_synth;
static int g_rate;
#endif

int mpu_available(void) { return g_mpu_on; }

/* mpu_init: the ROMs from the folder (NULL: none; the port stays dead). */
void mpu_init(const char *rom_dir, int rate)
{
    if (getenv("DS_MT32_PORT")) {                   /* the interface alone, no synthesizer: the driver's MIDI counted (tests) */
        g_mpu_on = 1; (void)rate;
        fprintf(stderr, "[mt32] MPU-401 on port 330h with nothing behind it (DS_MT32_PORT)\n");
        return;
    }
#ifdef DS_MT32
    if (!rom_dir || !*rom_dir) return;
    g_synth = mt32emu_create_context((mt32emu_report_handler_i){ NULL }, NULL);
    static const char *control[] = { "MT32_CONTROL.ROM", "CM32L_CONTROL.ROM", "mt32_control.rom", "cm32l_control.rom", NULL };
    static const char *pcm[] = { "MT32_PCM.ROM", "CM32L_PCM.ROM", "mt32_pcm.rom", "cm32l_pcm.rom", NULL };
    int have_control = 0, have_pcm = 0;
    char path[1200];
    for (int i = 0; control[i] && !have_control; i++) {
        snprintf(path, sizeof path, "%s/%s", rom_dir, control[i]);
        have_control = mt32emu_add_rom_file(g_synth, path) >= 0;
    }
    for (int i = 0; pcm[i] && !have_pcm; i++) {
        snprintf(path, sizeof path, "%s/%s", rom_dir, pcm[i]);
        have_pcm = mt32emu_add_rom_file(g_synth, path) >= 0;
    }
    if (!have_control || !have_pcm) {
        fprintf(stderr, "[mt32] no MT-32 ROMs in %s (MT32_CONTROL.ROM and MT32_PCM.ROM, or a CM-32L's): FM music instead\n", rom_dir);
        mt32emu_free_context(g_synth); g_synth = NULL;
        return;
    }
    mt32emu_set_stereo_output_samplerate(g_synth, rate);
    mt32emu_set_analog_output_mode(g_synth, MT32EMU_AOM_ACCURATE);
    if (mt32emu_open_synth(g_synth) != MT32EMU_RC_OK) {
        fprintf(stderr, "[mt32] the synthesizer did not open with the ROMs in %s: FM music instead\n", rom_dir);
        mt32emu_free_context(g_synth); g_synth = NULL;
        return;
    }
    g_rate = rate;
    g_mpu_on = 1;
    fprintf(stderr, "[mt32] MT-32 (Munt) on port 330h with the ROMs in %s, %u Hz\n", rom_dir, mt32emu_get_actual_stereo_output_samplerate(g_synth));
#else
    (void)rate;
    if (rom_dir && *rom_dir) fprintf(stderr, "[mt32] this build has no MT-32 emulation (built without mt32emu): FM music\n");
#endif
}

static void midi_byte(unsigned b)
{
    g_bytes++;
    if (b >= 0xF8) return;                          /* real-time: nothing to the MT-32 */
    if (g_in_sysex) {
        if (g_sysex_len < sizeof g_sysex) g_sysex[g_sysex_len++] = (unsigned char)b;
        if (b == 0xF7) {
            g_in_sysex = 0; g_sysexes++;
#ifdef DS_MT32
            if (g_synth) mt32emu_play_sysex(g_synth, g_sysex, g_sysex_len);
#endif
        }
        return;
    }
    if (b == 0xF0) { g_in_sysex = 1; g_sysex_len = 0; g_sysex[g_sysex_len++] = 0xF0; return; }
    if (b & 0x80) {                                  /* a status byte */
        if (b >= 0xF0) { g_running = 0; g_msg_need = 0; return; }   /* other system messages: ignored */
        g_running = b; g_msg = b; g_msg_len = 1;
        unsigned hi = b & 0xF0;
        g_msg_need = (hi == 0xC0 || hi == 0xD0) ? 2 : 3;
        return;
    }
    if (!g_running) return;                         /* data with no status */
    if (g_msg_len == 1 && g_msg_need == 0) return;
    if (g_msg_len == 1 || g_msg_len == 2) { g_msg |= b << (8 * g_msg_len); g_msg_len++; }
    if (g_msg_len == g_msg_need) {
        g_msgs++;
#ifdef DS_MT32
        if (g_synth) mt32emu_play_msg(g_synth, g_msg);
#endif
        g_msg = g_running; g_msg_len = 1;           /* running status: the next data bytes make another message */
    }
}

int mpu_port_in(uint16_t port, uint8_t *v)
{
    if (!g_mpu_on || (port != 0x330 && port != 0x331)) return 0;
    if (port == 0x331) { *v = (uint8_t)(g_ack_pending ? 0x00 : 0x80); return 1; }   /* bit 7: no data; bit 6 clear: ready */
    *v = g_ack_pending ? 0xFE : 0xFF; g_ack_pending = 0;
    return 1;
}

int mpu_port_out(uint16_t port, uint8_t val)
{
    if (!g_mpu_on || (port != 0x330 && port != 0x331)) return 0;
    if (port == 0x331) {                             /* a command: reset, UART mode, or another; every one acknowledged */
        g_ack_pending = 1;
        if (val == 0xFF) { g_in_sysex = 0; g_running = 0; g_msg_len = 0; }
        return 1;
    }
    midi_byte(val);
    return 1;
}

/* mpu_sample: the MT-32's next stereo sample for the mixer, rendered in blocks. */
void mpu_sample(unsigned rate, int *l, int *r)
{
    *l = *r = 0;
#ifdef DS_MT32
    (void)rate;
    if (!g_synth) return;
    static int16_t buf[2 * 128]; static unsigned have, pos;
    if (pos >= have) { mt32emu_render_bit16s(g_synth, buf, 128); have = 128; pos = 0; }
    *l = buf[2 * pos]; *r = buf[2 * pos + 1]; pos++;
#else
    (void)rate;
#endif
}

void mpu_report(void)
{
    if (g_bytes) fprintf(stderr, "[mt32] %lu MIDI bytes: %lu messages, %lu SysEx\n", g_bytes, g_msgs, g_sysexes);
}
