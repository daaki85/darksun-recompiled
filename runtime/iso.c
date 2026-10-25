/*
 * iso.c - unpack GOG's CD image (game.gog) into a folder, once.
 *
 * Wake of the Ravager reads its data from a CD. GOG ships it as game.gog,
 * one raw MODE2/2352 data track: each 2,352-byte sector carries 2,048 bytes
 * of data at offset 24 (12 bytes sync, 4 header, 8 subheader). The data
 * sectors are a plain ISO 9660 image: the primary volume descriptor at
 * sector 16 names the root directory, and every directory is a list of
 * records (length, extent, size, flags, name). The files are written to
 * <game>/cd, which the program then serves as drive D:. Names are written
 * as the image spells them (upper case), without the ";1" version.
 */
#include "runtime.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#define MKDIR(p) _mkdir(p)
#else
#define MKDIR(p) mkdir(p, 0755)
#endif

#define RAW 2352
#define DATA 2048
#define SKIP 24

static FILE *g_f;
static long g_sectors;

static int read_sector(unsigned lba, uint8_t *out)
{
    if ((long)lba >= g_sectors) return 0;
    if (fseek(g_f, (long)lba * RAW + SKIP, SEEK_SET) != 0) return 0;
    return fread(out, 1, DATA, g_f) == DATA;
}

static uint32_t le32(const uint8_t *p) { return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24); }

static int write_file(unsigned lba, uint32_t size, const char *path)
{
    FILE *o = fopen(path, "wb");
    if (!o) { fprintf(stderr, "[cd] cannot write %s: %s\n", path, strerror(errno)); return 0; }
    uint8_t buf[DATA];
    while (size) {
        if (!read_sector(lba++, buf)) { fclose(o); return 0; }
        size_t n = size < DATA ? size : DATA;
        if (fwrite(buf, 1, n, o) != n) { fclose(o); return 0; }
        size -= (uint32_t)n;
    }
    fclose(o);
    return 1;
}

static int walk(unsigned lba, uint32_t size, const char *out, int depth, int *files)
{
    if (depth > 8) return 0;
    uint8_t *dir = malloc(size + DATA);
    if (!dir) return 0;
    for (uint32_t off = 0, s = lba; off < size; off += DATA, s++)
        if (!read_sector(s, dir + off)) { free(dir); return 0; }
    for (uint32_t p = 0; p < size; ) {
        uint8_t len = dir[p];
        if (!len) { p = (p / DATA + 1) * DATA; continue; }    /* records never cross a sector: pad to the next */
        const uint8_t *r = dir + p;
        uint32_t extent = le32(r + 2), fsize = le32(r + 10);
        uint8_t flags = r[25], nlen = r[32];
        char name[256];
        memcpy(name, r + 33, nlen); name[nlen] = 0;
        char *semi = strchr(name, ';'); if (semi) *semi = 0;
        size_t l = strlen(name); if (l && name[l - 1] == '.') name[l - 1] = 0;
        p += len;
        if (nlen == 1 && (name[0] == 0 || name[0] == 1)) continue;   /* . and .. */
        char path[1200];
        snprintf(path, sizeof path, "%s/%s", out, name);
        if (flags & 2) {
            MKDIR(path);
            if (!walk(extent, fsize, path, depth + 1, files)) { free(dir); return 0; }
        } else {
            if (!write_file(extent, fsize, path)) { free(dir); return 0; }
            (*files)++;
        }
    }
    free(dir);
    return 1;
}

/* Unpack image_path into out_dir (made if missing). Returns the number of
 * files written, or -1. */
int iso_extract(const char *image_path, const char *out_dir)
{
    g_f = fopen(image_path, "rb");
    if (!g_f) return -1;
    fseek(g_f, 0, SEEK_END); g_sectors = ftell(g_f) / RAW;
    uint8_t pvd[DATA];
    if (!read_sector(16, pvd) || memcmp(pvd + 1, "CD001", 5) != 0 || pvd[0] != 1) {
        fprintf(stderr, "[cd] %s: no ISO 9660 primary volume descriptor at sector 16\n", image_path);
        fclose(g_f); return -1;
    }
    const uint8_t *root = pvd + 156;
    unsigned lba = le32(root + 2); uint32_t size = le32(root + 10);
    MKDIR(out_dir);
    int files = 0;
    int ok = walk(lba, size, out_dir, 0, &files);
    fclose(g_f);
    if (!ok) { fprintf(stderr, "[cd] unpacking %s stopped after %d files\n", image_path, files); return -1; }
    return files;
}
