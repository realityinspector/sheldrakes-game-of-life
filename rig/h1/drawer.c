/*
 * Blind drawer for the human-in-the-loop rig (rig/h1).
 *
 * Draws uniform indices in [0, N) from one entropy source and counts how often each of K
 * candidate indices comes up, in fixed time chunks. It is given the candidates only, never
 * which ones a human worked on. Sources:
 *   rdseed   the CPU's hardware noise source (RDSEED: fresh conditioned entropy per call)
 *   urandom  the kernel CSPRNG (getrandom)
 * No beacon or other mixing: anything that biased the source would reach the counts.
 *
 * Usage: drawer <rdseed|urandom> <N> <seconds> <chunk_seconds> <idx1> ... <idxK>
 * Output: one JSON line per chunk: {"t0":..,"t1":..,"draws":..,"hits":[..]}
 */
#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>

static double now(void) {
  struct timespec ts;
  clock_gettime(CLOCK_REALTIME, &ts);
  return ts.tv_sec + ts.tv_nsec / 1e9;
}

#define BUF 4096
static uint64_t buf[BUF];

static void fill_rdseed(void) {
  for (int i = 0; i < BUF; i++) {
    unsigned long long x;
    while (!_rdseed64_step(&x)) _mm_pause();
    buf[i] = x;
  }
}

static void fill_urandom(void) {
  size_t need = sizeof(buf), got = 0;
  while (got < need) {
    ssize_t r = getrandom((char *)buf + got, need - got, 0);
    if (r > 0) got += (size_t)r;
  }
}

int main(int argc, char **argv) {
  if (argc < 6) {
    fprintf(stderr, "usage: drawer <rdseed|urandom> <N> <seconds> <chunk_seconds> <idx...>\n");
    return 2;
  }
  int use_rdseed = strcmp(argv[1], "rdseed") == 0;
  int N = atoi(argv[2]);
  double seconds = atof(argv[3]), chunk = atof(argv[4]);
  int K = argc - 5;
  if (N < 2 || N > 65536 || K < 1 || K > 64) return 2;
  int16_t slot[65536];
  for (int i = 0; i < 65536; i++) slot[i] = -1;
  uint32_t limit = (65536 / N) * N; /* reject v >= limit, then v % N is uniform */
  for (int k = 0; k < K; k++) {
    int idx = atoi(argv[5 + k]);
    if (idx < 0 || idx >= N) return 2;
    /* every v < limit with v % N == idx maps to slot k */
    for (uint32_t v = (uint32_t)idx; v < limit; v += (uint32_t)N) slot[v] = (int16_t)k;
  }
  double start = now(), end = start + seconds;
  while (now() < end) {
    double t0 = now(), t1 = t0 + chunk;
    unsigned long long draws = 0, hits[64] = {0};
    while (now() < t1) {
      for (int rep = 0; rep < 16; rep++) {
        if (use_rdseed) fill_rdseed(); else fill_urandom();
        const uint16_t *v = (const uint16_t *)buf;
        for (int i = 0; i < BUF * 4; i++) {
          uint16_t x = v[i];
          if (x >= limit) continue;
          draws++;
          int s = slot[x];
          if (s >= 0) hits[s]++;
        }
      }
    }
    printf("{\"t0\":%.3f,\"t1\":%.3f,\"draws\":%llu,\"hits\":[", t0, now(), draws);
    for (int k = 0; k < K; k++) printf(k ? ",%llu" : "%llu", hits[k]);
    printf("]}\n");
    fflush(stdout);
  }
  return 0;
}
