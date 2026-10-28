#include "../runtime/gfx/nvn/aoc_stats.h"
#include "../runtime/gfx/nvn/aoc_timing.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mach/mach_time.h>
#include <unistd.h>
static uint64_t native_tick(void) {uint64_t t;__asm__ volatile("mrs %0,cntvct_el0":"=r"(t));return t;}
uint8_t page[256], *dm_fps_state=page;
static int checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"failed line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static float value(unsigned off){float f;memcpy(&f,page+off,4);return f;}
int main(void){
    uint64_t now=1000000000ull;
    CHECK(aoc_stats_snapshot(now).samples==0);
    for(unsigned i=0;i<=120;i++) aoc_stats_frame(now+i*8333333ull,4,120);
    for(unsigned i=0;i<=60;i++) aoc_stats_display(1+i/60.0,now+i*16666666ull);
    AocStats s=aoc_stats_snapshot(now+1000000000ull);
    CHECK(s.active && s.display_active);
    CHECK(fabs(s.game_fps-120)<.001 && fabs(s.display_fps-60)<.001);
    CHECK(fabs(s.p99_ms-8.333333)<.001 && s.gpu_ms==4);
    CHECK(s.samples==120 && s.target==120);
    aoc_stats_resources((AocShaderStats){.inventory=40729,.libraries=223,.pipeline_errors=2});
    s=aoc_stats_snapshot(now+3000000000ull);
    CHECK(!s.active && !s.display_active && s.game_fps==0 && s.display_fps==0);
    CHECK(s.shaders.inventory==40729 && s.shaders.pipeline_errors==2);
    aoc_stats_display(1.1,now); // an out-of-order callback cannot move the clock backwards
    CHECK(!aoc_stats_snapshot(now+3000000000ull).display_active);
    for(unsigned i=121;i<=500;i++) aoc_stats_frame(now+i*8333333ull,3,120);
    CHECK(aoc_stats_snapshot(now+500*8333333ull).samples==AOC_STATS_SAMPLES);
    unsetenv("DM_FPS_TARGET");unsetenv("DM_DYNAMIC_FPS");
    aoc_timing_apply(0);CHECK(value(0)==0 && aoc_timing_dynamic());
    for(int i=0;i<3;i++) {int t=(int[]){30,60,120}[i];aoc_timing_set(t,1);CHECK(value(0)==t && aoc_timing_target()==t);}
    aoc_timing_set(75,0);CHECK(aoc_timing_target()==120 && aoc_timing_dynamic());
    setenv("DM_FPS_TARGET","120",1);setenv("DM_DYNAMIC_FPS","0",1);
    aoc_timing_apply(0);CHECK(aoc_timing_target()==120 && !aoc_timing_dynamic());
    CHECK(fabs(value(AOC_DT)-1.0/120)<1e-7);
    uint64_t counter0=native_tick(),mach0=mach_absolute_time();usleep(10000);
    uint64_t mach1=mach_absolute_time(),counter1=native_tick();
    mach_timebase_info_data_t tb;mach_timebase_info(&tb);
    double actual=(mach1-mach0)*(double)tb.numer/tb.denom/1e9;
    CHECK(fabs((counter1-counter0)*value(AOC_COUNTER_SCALE)/actual-1)<.01);
    setenv("DM_FPS_TARGET","60garbage",1);aoc_timing_apply(0);CHECK(aoc_timing_target()==0);
    printf("performance/timing probe: %d checks passed\n",checks);return 0;
}
