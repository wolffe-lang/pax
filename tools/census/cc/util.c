#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include "util.h"

size_t util_count(const char *s, char c) {
    size_t n = 0;
    for (; *s; s++) n += (*s == c);
    return n;
}

char *util_upper(const char *s) {
    size_t len = strlen(s);
    char *out = malloc(len + 1);
    if (!out) return NULL;
    for (size_t i = 0; i <= len; i++) out[i] = (char)toupper((unsigned char)s[i]);
    return out;
}
