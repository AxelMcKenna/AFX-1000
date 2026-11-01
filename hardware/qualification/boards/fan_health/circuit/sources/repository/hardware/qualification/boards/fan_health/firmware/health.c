#include "health.h"
#include <string.h>

void ph_fail(ph_state *s, uint8_t cause) {
    s->fault |= cause;
    s->mode = PH_LATCHED;
}

void ph_init(ph_state *s, uint32_t now, bool unsafe_reset) {
    memset(s, 0, sizeof(*s));
    s->boot = s->last_step = now;
    s->mode = PH_BOOT;
    if (unsafe_reset) ph_fail(s, PH_RESET);
}

void ph_edge(ph_state *s, uint8_t channel, uint32_t now) {
    if (channel > 1) { ph_fail(s, PH_CAPTURE); return; }
    ph_fan *f = &s->fan[channel];
    uint32_t delta = now - f->last;
    if (f->seen && delta >= PH_PERIOD_MIN && delta <= PH_PERIOD_MAX) {
        if (f->good < PH_PULSES_TO_QUALIFY) ++f->good;
    } else {
        f->good = 0;
    }
    f->seen = true;
    f->last = now;
}

bool ph_step(ph_state *s, uint32_t now, uint16_t adc0, uint16_t adc1) {
    if (now - s->last_step > PH_STEP_MAX) ph_fail(s, PH_CLOCK);
    s->last_step = now;
    const uint16_t adc[2] = {adc0, adc1};
    uint8_t bad = 0;
    for (uint8_t i = 0; i < 2; ++i) {
        if (adc[i] <= PH_ADC_SHORT || adc[i] >= PH_ADC_OPEN) bad |= PH_SENSOR;
        else if (adc[i] <= PH_ADC_HOT) bad |= PH_TEMP;
    }
    if (bad) ph_fail(s, bad);
    for (uint8_t i = 0; i < 2; ++i) {
        const ph_fan *f = &s->fan[i];
        if (!f->seen || now - f->last > PH_FRESH_TICKS) bad |= PH_STALE;
        if (f->good < PH_PULSES_TO_QUALIFY) bad |= PH_SPEED;
    }
    if (s->mode == PH_RUNNING && bad) ph_fail(s, bad);
    if (s->mode == PH_BOOT) {
        if (bad) s->qualifying = false;
        else if (!s->qualifying) {
            s->qualifying = true;
            s->qualified_since = now;
        } else if (now - s->qualified_since >= PH_HOLD_TICKS) {
            s->mode = PH_RUNNING;
        }
        if (s->mode == PH_BOOT && now - s->boot >= PH_BOOT_TICKS)
            ph_fail(s, PH_BOOT_TIMEOUT | bad);
    }
    return s->mode == PH_RUNNING && s->fault == 0;
}
