/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * WordStats - a console tool in C: counts lines, words and characters of text files and lists the most
 * frequent words, like a small "wc" + word frequency.
 *
 *     WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]
 *     WordStats --help
 *
 * Without files it reads sample.txt next to the program (so F5 in the IDE shows a result).
 * Exit codes: 0 = OK, 1 = wrong arguments, 2 = a file could not be read, 3 = the report could not be written.
 * A project without forms whose module has main() is a console application in RAD IDE: F5 runs it in the
 * Output window, Build > Publish makes a native console exe.
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_WORDS 5000
#define MAX_WORD 48

typedef struct {
    char word[MAX_WORD];
    int count;
} Entry;

static Entry words[MAX_WORDS];
static int nwords = 0;

static void add_word(const char *w)
{
    int i;
    for (i = 0; i < nwords; i++)
        if (strcmp(words[i].word, w) == 0) { words[i].count++; return; }
    if (nwords < MAX_WORDS) {
        strncpy(words[nwords].word, w, MAX_WORD - 1);
        words[nwords].count = 1;
        nwords++;
    }
}

static int by_count(const void *a, const void *b)
{
    const Entry *x = (const Entry *)a, *y = (const Entry *)b;
    if (y->count != x->count) return y->count - x->count;
    return strcmp(x->word, y->word);
}

/* count one file; returns 0 or -1 when it cannot be opened */
static int count_file(const char *path, long *lines, long *nw, long *chars, FILE *out)
{
    FILE *f = fopen(path, "rb");
    char w[MAX_WORD];
    int c, len = 0;
    long l = 0, n = 0, ch = 0, last = '\n';
    if (!f) return -1;
    while ((c = fgetc(f)) != EOF) {
        if ((c & 0xC0) != 0x80) ch++;                 /* UTF-8: count characters, not bytes */
        if (c == '\n') l++;
        if (isalnum(c) || c >= 0x80 || c == '\'') {
            if (len < MAX_WORD - 1) w[len++] = (char)tolower(c);
        } else if (len) {
            w[len] = 0;
            add_word(w);
            n++;
            len = 0;
        }
        last = c;
    }
    if (len) { w[len] = 0; add_word(w); n++; }
    if (last != '\n') l++;                            /* last line without a line break */
    fclose(f);
    fprintf(out, "%8ld %8ld %8ld  %s\n", l, n, ch, path);
    *lines += l;
    *nw += n;
    *chars += ch;
    return 0;
}

static void usage(FILE *f)
{
    fprintf(f, "usage: WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]\n");
}

int main(int argc, char **argv)
{
    const char *files[64], *out_path = NULL;
    int nfiles = 0, top = 10, i, failed = 0;
    long lines = 0, nw = 0, chars = 0;
    FILE *out = stdout;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) { usage(stdout); return 0; }
        if (strcmp(argv[i], "--top") == 0 && i + 1 < argc) {
            top = atoi(argv[++i]);
            if (top <= 0) { fprintf(stderr, "--top needs a positive number\n"); return 1; }
        } else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
            out_path = argv[++i];
        } else if (argv[i][0] == '-') {
            fprintf(stderr, "unknown option %s\n", argv[i]);
            usage(stderr);
            return 1;
        } else if (nfiles < 64) {
            files[nfiles++] = argv[i];
        }
    }
    if (nfiles == 0) files[nfiles++] = "sample.txt";
    if (out_path && !(out = fopen(out_path, "w"))) {
        fprintf(stderr, "cannot write %s\n", out_path);
        return 3;
    }
    fprintf(out, "   lines    words    chars  file\n");
    for (i = 0; i < nfiles; i++) {
        if (count_file(files[i], &lines, &nw, &chars, out) != 0) {
            fprintf(stderr, "cannot read %s\n", files[i]);
            failed = 1;
        }
    }
    if (nfiles > 1) fprintf(out, "%8ld %8ld %8ld  total\n", lines, nw, chars);
    qsort(words, (size_t)nwords, sizeof(Entry), by_count);
    fprintf(out, "\nTop %d words:\n", top);
    for (i = 0; i < nwords && i < top; i++) fprintf(out, "%4d. %-20s %d\n", i + 1, words[i].word, words[i].count);
    if (out != stdout) {
        fclose(out);
        printf("report written to %s\n", out_path);
    }
    return failed ? 2 : 0;
}
