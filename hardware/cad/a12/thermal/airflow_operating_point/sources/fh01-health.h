#ifndef AFX_FAN_HEALTH_H
#define AFX_FAN_HEALTH_H

#include <stdbool.h>
#include <stdint.h>

enum { PH_TICK_HZ = 125000, PH_PULSES_TO_QUALIFY = 8,
       PH_PERIOD_MIN = 375, PH_PERIOD_MAX = 694,
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

void ph_init(ph_state *s, uint32_t now, bool unsafe_reset);
void ph_edge(ph_state *s, uint8_t channel, uint32_t now);
void ph_fail(ph_state *s, uint8_t cause);
bool ph_step(ph_state *s, uint32_t now, uint16_t adc0, uint16_t adc1);

#endif
