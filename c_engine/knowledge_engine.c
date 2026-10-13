#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

static int parse_count(const char *text, int *value) {
    char *end = NULL;
    errno = 0;
    long parsed = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed < 0 || parsed > 1000000) {
        return 0;
    }
    *value = (int)parsed;
    return 1;
}

int main(int argc, char **argv) {
    int note_count = 0;
    int subject_count = 0;
    if (argc != 3 || !parse_count(argv[1], &note_count) || !parse_count(argv[2], &subject_count)) {
        fprintf(stderr, "Expected non-negative note and subject counts.\n");
        return 2;
    }

    long score = (long)note_count * 3 + (long)subject_count * 8;
    if (score > 100) {
        score = 100;
    }
    printf("%d\n", (int)score);
    return 0;
}
