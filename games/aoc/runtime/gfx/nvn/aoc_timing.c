#include "aoc_timing.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern uint8_t *dm_fps_state __attribute__((weak));
static _Atomic int target_fps, dynamic_step = 1;
static uint8_t *state(void) { return &dm_fps_state ? dm_fps_state : NULL; }
int aoc_timing_valid(int t) { return t == 0 || t == 30 || t == 60 || t == 120; }
int aoc_timing_target(void) { return atomic_load(&target_fps); }
int aoc_timing_dynamic(void) { return atomic_load(&dynamic_step); }
static void put_float(uint8_t *p, float f) {
    uint32_t bits; memcpy(&bits, &f, 4); __atomic_store_n((uint32_t *)p, bits, __ATOMIC_RELEASE);
}
void aoc_timing_set(int target, int dynamic) {
    if (!aoc_timing_valid(target)) return;
    uint8_t *p = state();
    if (p) {
        __atomic_store_n((uint32_t *)(p + AOC_DYNAMIC), !!dynamic, __ATOMIC_RELAXED);
        __atomic_store_n((uint64_t *)(p+AOC_SCENE_TICKS),0,__ATOMIC_RELAXED);
        __atomic_store_n((uint32_t *)(p+AOC_SCENE_ACTIVE),0,__ATOMIC_RELAXED);
        put_float(p, (float)target);
    }
    atomic_store(&dynamic_step, !!dynamic); atomic_store(&target_fps, target);
}
void aoc_timing_apply(int profile_target) {
    int t = profile_target;
    const char *e = getenv("DM_FPS_TARGET");
    if (e) {
        char *end; long n = strtol(e, &end, 10);
        t = *e && !*end && n >= 0 && n <= 120 && aoc_timing_valid((int)n) ? (int)n : 0;
        if (!(*e && !*end && n == t)) fprintf(stderr, "[dm] invalid DM_FPS_TARGET; using original 30 fps\n");
    }
    int dynamic = 1; e = getenv("DM_DYNAMIC_FPS");
    if (e) dynamic = strcmp(e, "0") && strcmp(e, "off");
    uint8_t *p = state();
    if (p) { uint64_t frequency; __asm__ volatile("mrs %0,cntfrq_el0":"=r"(frequency));
        put_float(p+AOC_COUNTER_SCALE,1.0f/(float)frequency); put_float(p + AOC_DT, 1.0f / (t ? t : 30)); put_float(p + AOC_MAX_DT, .1f); put_float(p + AOC_MIN_DT, .001f); }
    aoc_timing_set(t, dynamic);
    fprintf(stderr, "[dm] AoC timing: %d fps target, %s step; long gaps capped at 100 ms\n", t ? t : 30, t && dynamic ? "measured" : "fixed");
}
void aoc_timing_clock(double *seconds, uint64_t *updates) {
    uint8_t *p = state(); uint64_t bits = p ? __atomic_load_n((uint64_t *)(p + AOC_SECONDS), __ATOMIC_RELAXED) : 0;
    memcpy(seconds, &bits, 8);
    *updates = p ? __atomic_load_n((uint64_t *)(p + AOC_UPDATES), __ATOMIC_RELAXED) : 0;
}

void aoc_timing_scene_clock(double *seconds, uint64_t *updates) {
    uint8_t *p = state(); uint64_t bits=p?__atomic_load_n((uint64_t *)(p+AOC_SCENE_SECONDS),__ATOMIC_RELAXED):0;
    memcpy(seconds,&bits,8); *updates=p?__atomic_load_n((uint64_t *)(p+AOC_SCENE_UPDATES),__ATOMIC_RELAXED):0;
}
