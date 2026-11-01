#ifndef AFX_FAN_HEALTH_H
#define AFX_FAN_HEALTH_H

#include <stdbool.h>
#include <stdint.h>

enum { PH_TICK_HZ = 125000, PH_PULSES_TO_QUALIFY = 8,
       PH_PERIOD_MIN = 375, PH_PERIOD_MAX = 680,
       PH_FRESH_TICKS = 2500, PH_HOLD_TICKS = 62500,
       PH_BOOT_TICKS = 625000, PH_STEP_MAX = 3125,
       PH_ADC_SHORT = 8, PH_ADC_OPEN = 1000, PH_ADC_HOT = 186 };
typedef enum { PH_BOOT, PH_RUNNING, PH_LATCHED } ph_mode;
enum { PH_TEMP = 1, PH_SENSOR = 2, PH_SPEED = 4, PH_STALE = 8,
       PH_BOOT_TIMEOUT = 16, PH_RESET = 32, PH_CLOCK = 64, PH_CAPTURE = 128 };
typedef struct { uint32_t last; uint8_t good; bool seen; } ph_fan;
typedef struct {
    ph_fan fan[2];
    uint32_t boot, last_step, qualified_since;
    ph_mode mode;
    uint8_t fault;
    bool qualifying;
} ph_state;

static inline bool ph_clean_power_reset(bool power_on, bool external, bool watchdog) {
    return power_on && !external && !watchdog;
}

/* Caller holds interrupts off while sampling hi, lo, then the pending flag.
   Pending overflow with a high lo belongs AFTER that sampled counter value.
   Requires no unserviced overflow older than half a timer cycle. */
static inline uint32_t ph_timestamp(uint32_t hi, uint16_t lo, bool pending) {
    if (pending && lo < 0x8000u) ++hi;
    /* Raw500kHz -> engine125kHz. Retain upper bits across raw32-bit wrap. */
    /* Volatile byte results prevent GCC7 recombining this into long32-bit
       shift loops. The same arithmetic is exercised by the host tests. */
    uint8_t r0 = (uint8_t)lo, r1 = (uint8_t)(lo >> 8);
    uint8_t r2 = (uint8_t)hi, r3 = (uint8_t)(hi >> 8), r4 = (uint8_t)(hi >> 16);
    volatile uint8_t b0 = (uint8_t)((r0 >> 2) | (r1 << 6));
    volatile uint8_t b1 = (uint8_t)((r1 >> 2) | (r2 << 6));
    volatile uint8_t b2 = (uint8_t)((r2 >> 2) | (r3 << 6));
    volatile uint8_t b3 = (uint8_t)((r3 >> 2) | (r4 << 6));
    return (uint32_t)b0 | ((uint32_t)b1 << 8) |
           ((uint32_t)b2 << 16) | ((uint32_t)b3 << 24);
}

void ph_init(ph_state *s, uint32_t now, bool unsafe_reset);
void ph_edge(ph_state *s, uint8_t channel, uint32_t now);
void ph_fail(ph_state *s, uint8_t cause);
bool ph_step(ph_state *s, uint32_t now, uint16_t adc0, uint16_t adc1);

#endif
