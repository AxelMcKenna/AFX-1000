/* FH01 target adapter. Bench, fuse readback and timing qualification outstanding. */
#define F_CPU 4000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/boot.h>
#include <avr/wdt.h>
#include <util/atomic.h>
#include <util/delay.h>
#include "health.h"

#define HEARTBEAT PA2
#define TACH_L PA3
#define HEALTH PA7
#define TACH_R PB2
#define QUEUE_SIZE 16u

static volatile uint32_t queue_ticks[QUEUE_SIZE];
static volatile uint8_t queue_channels[QUEUE_SIZE];
static volatile uint8_t head, tail, capture_lost;
static volatile uint32_t timer_high;
static volatile uint8_t left_level, right_level;
static uint8_t reset_cause __attribute__((section(".noinit")));

void early_reset(void) __attribute__((naked, section(".init3")));
void early_reset(void) {
    reset_cause = MCUSR;
    MCUSR = 0;
    wdt_disable();
}

static uint32_t ticks(void) {
    uint32_t hi;
    uint16_t lo;
    bool pending;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        hi = timer_high;
        lo = TCNT1;
        pending = (TIFR1 & _BV(TOV1)) != 0;
    }
    return ph_timestamp(hi, lo, pending);
}

ISR(TIM1_OVF_vect) { ++timer_high; }

static void push(uint8_t channel) {
    uint8_t next = (head + 1u) & (QUEUE_SIZE - 1u);
    if (next == tail) { capture_lost = 1; return; }
    queue_ticks[head] = ticks();
    queue_channels[head] = channel;
    head = next; /* Publish the complete event, with interrupts still disabled. */
}

ISR(PCINT0_vect) {
    uint8_t level = (PINA & _BV(TACH_L)) != 0;
    if (level && !left_level) push(0);
    left_level = level;
}

ISR(PCINT1_vect) {
    uint8_t level = (PINB & _BV(TACH_R)) != 0;
    if (level && !right_level) push(1);
    right_level = level;
}

static uint16_t adc(uint8_t channel) {
    ADMUX = channel; /* VCC reference; PA0/PA1 are the only sensor channels. */
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) {}
    (void)ADC; /* Discard after every MUX change. */
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) {}
    return ADC;
}

int main(void) {
    cli();
    PORTA = _BV(PA4) | _BV(PA5) | _BV(PA6); /* ISP pins only; HEALTH/HB default LOW. */
    DDRA = _BV(HEALTH) | _BV(HEARTBEAT);
    DDRB = 0;
    CLKPR = _BV(CLKPCE);
    CLKPR = 0; /* Full external4MHz core; reduce interrupt capture latency. */
    uint8_t lfuse = boot_lock_fuse_bits_get(GET_LOW_FUSE_BITS);
    uint8_t hfuse = boot_lock_fuse_bits_get(GET_HIGH_FUSE_BITS);
    bool unsafe = ((reset_cause & (_BV(WDRF) | _BV(BORF) | _BV(EXTRF))) != 0)
                  && !(reset_cause & _BV(PORF));
    unsafe |= lfuse != 0x7d || hfuse != 0xdd;
    ph_state state;
    TCCR1A = 0;
    TCCR1B = _BV(CS11); /* Raw500kHz; extended then scaled to engine125kHz. */
    TIMSK1 = _BV(TOIE1);
    ADCSRA = _BV(ADEN) | _BV(ADPS2) | _BV(ADPS1); /*4MHz/64=62.5kHz ADC. */
    DIDR0 = _BV(ADC0D) | _BV(ADC1D);
    left_level = (PINA & _BV(TACH_L)) != 0;
    right_level = (PINB & _BV(TACH_R)) != 0;
    PCMSK0 = _BV(PCINT3);
    PCMSK1 = _BV(PCINT10);
    GIMSK = _BV(PCIE0) | _BV(PCIE1);
    sei();
    wdt_enable(WDTO_60MS);
    _delay_ms(20); /* External sensor RC settling; no permission during startup. */
    wdt_reset();
    ph_init(&state, ticks(), unsafe);
    uint32_t last_loop = ticks();
    for (;;) {
        uint32_t now = ticks();
        if (now - last_loop < PH_TICK_HZ / 100u) continue;
        last_loop = now;
        if (capture_lost) ph_fail(&state, PH_CAPTURE);
        while (tail != head) {
            uint8_t index = tail;
            uint32_t tick = queue_ticks[index];
            uint8_t channel = queue_channels[index];
            tail = (index + 1u) & (QUEUE_SIZE - 1u);
            ph_edge(&state, channel, tick);
        }
        uint16_t a = adc(0), b = adc(1);
        bool healthy = ph_step(&state, ticks(), a, b);
        if (healthy) PORTA |= _BV(HEALTH);
        else PORTA &= (uint8_t)~_BV(HEALTH);
        PORTA ^= _BV(HEARTBEAT); /* Software only, after the complete monitor cycle. */
        wdt_reset();
    }
}
