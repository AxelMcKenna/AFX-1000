#include "health.h"
#include <assert.h>
#include <stdio.h>

static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)

static void simulate(ph_state *s, uint32_t origin, uint32_t duration,
                     uint32_t left_period, uint32_t right_period,
                     uint16_t a, uint16_t b) {
    for (uint32_t t = 125; t <= duration; t += 125) {
        if (left_period && t % left_period == 0) ph_edge(s, 0, origin+t);
        if (right_period && t % right_period == 0) ph_edge(s, 1, origin+t);
        if (t % 1250 == 0) (void)ph_step(s,origin+t,a,b);
    }
}

static void ready(ph_state *s,uint32_t origin) {
    ph_init(s,origin,false);
    simulate(s,origin,125000,500,625,512,512); /*7500/6000rpm, one full second. */
    CHECK(s->mode == PH_RUNNING && s->fault == 0);
}

int main(void) {
    ph_state s;
    for (unsigned flags=0; flags<8; ++flags) {
        CHECK(ph_clean_power_reset((flags&1)!=0,(flags&2)!=0,(flags&4)!=0) == (flags==1));
    }
    CHECK(ph_timestamp(12,0,false) == (12UL << 14));
    CHECK(ph_timestamp(12,0,true) == (13UL << 14));
    CHECK(ph_timestamp(12,1,true) == (13UL << 14));
    CHECK(ph_timestamp(12,0xffff,true) == ((12UL << 14) | 0x3fff));
    CHECK(ph_timestamp(12,0x8000,true) == ((12UL << 14) | 0x2000));
    CHECK(ph_timestamp(12,0x7fff,true) == ((13UL << 14) | 0x1fff));
    CHECK(ph_timestamp(0x3ffff,0,true) == 0); /* Full engine32-bit wrap. */
    CHECK(ph_timestamp(0xffff,0,true) == 0x40000000UL); /* Raw32-bit wrap retained. */
    uint32_t sample = 0x12345678UL;
    for (unsigned i=0; i<4096; ++i) {
        sample = sample * 1664525UL + 1013904223UL;
        uint32_t hi = sample;
        uint16_t lo = (uint16_t)(sample >> 9);
        bool pending = (sample & 1) != 0;
        uint32_t corrected = hi + (pending && lo < 0x8000u);
        uint32_t reference = (uint32_t)((((uint64_t)corrected << 16) | lo) >> 2);
        CHECK(ph_timestamp(hi,lo,pending) == reference);
    }
    ph_init(&s,0,false);
    simulate(&s,0,PH_BOOT_TICKS,0,0,512,512);
    CHECK(s.mode==PH_LATCHED && (s.fault & PH_BOOT_TIMEOUT));
    ph_init(&s,0,false);
    ph_edge(&s,0,500); ph_edge(&s,1,500);
    simulate(&s,0,PH_BOOT_TICKS,0,0,512,512);
    CHECK(s.mode==PH_LATCHED); /* StaticHIGH orLOW cannot become permission. */
    ph_init(&s,0,false);
    simulate(&s,0,PH_BOOT_TICKS,500,0,512,512);
    CHECK(s.mode==PH_LATCHED);
    ph_init(&s,0,false);
    simulate(&s,0,PH_BOOT_TICKS,500,1000,512,512);
    CHECK(s.mode==PH_LATCHED); /*3750rpm is not qualified merely for pulsing. */
    ph_init(&s,0,false);
    simulate(&s,0,PH_BOOT_TICKS,250,500,512,512);
    CHECK(s.mode==PH_LATCHED); /*15krpm/noise rejected. */
    ready(&s,0);
    simulate(&s,125000,5000,500,0,512,512);
    CHECK(s.mode==PH_LATCHED && (s.fault & PH_STALE));
    simulate(&s,130000,125000,500,625,512,512);
    CHECK(s.mode==PH_LATCHED); /* Fault cannot be cleared by a fan recovering. */
    ready(&s,0);
    CHECK(!ph_step(&s,126250,185,512) && (s.fault & PH_TEMP));
    ready(&s,0);
    CHECK(!ph_step(&s,126250,0,512) && (s.fault & PH_SENSOR));
    ready(&s,0);
    CHECK(!ph_step(&s,126250,512,1023) && (s.fault & PH_SENSOR));
    /* Sweep both ADC channels, including the exact trip boundaries. */
    for (unsigned channel = 0; channel < 2; ++channel) {
        for (uint16_t value = 0; value <= 1023; ++value) {
            ready(&s,0);
            bool ok = ph_step(&s,126250,channel ? 512 : value,
                             channel ? value : 512);
            bool sensor = value <= PH_ADC_SHORT || value >= PH_ADC_OPEN;
            bool hot = !sensor && value <= PH_ADC_HOT;
            CHECK(ok == (!sensor && !hot));
            CHECK(((s.fault & PH_SENSOR) != 0) == sensor);
            CHECK(((s.fault & PH_TEMP) != 0) == hot);
        }
    }
    ready(&s,0);
    CHECK(!ph_step(&s,130000,512,512) && (s.fault & PH_CLOCK));
    ready(&s,UINT32_MAX-100000u); /* Wrap during startup and running. */
    ph_init(&s,0,true);
    simulate(&s,0,125000,500,625,512,512);
    CHECK(s.mode==PH_LATCHED && (s.fault & PH_RESET));
    ready(&s,0); /* Only an explicitly clean power reset clears the latch. */
    ph_fail(&s,PH_CAPTURE);
    CHECK(!ph_step(&s,126250,512,512) && (s.fault & PH_CAPTURE));
    ph_init(&s,0,false);
    ph_edge(&s,2,100);
    CHECK(s.mode==PH_LATCHED && (s.fault & PH_CAPTURE));
    for (uint32_t period=374;period<=695;++period) {
        ph_init(&s,0,false);
        for(uint32_t i=0;i<10;++i)ph_edge(&s,0,i*period);
        CHECK((s.fan[0].good==PH_PULSES_TO_QUALIFY)==(period>=375 && period<=680));
    }
    printf("FH01 software engine: %u assertions passed\n",checks);
    return 0;
}
