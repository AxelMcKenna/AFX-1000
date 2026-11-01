/* Runs before BSS initialization; intentionally falls through to .init4. */
#include <avr/io.h>
#include <avr/wdt.h>
#include <stdint.h>

uint8_t ph_reset_cause __attribute__((section(".noinit")));

void early_reset(void) __attribute__((naked, section(".init3")));
void early_reset(void) {
    ph_reset_cause = MCUSR;
    MCUSR = 0;
    wdt_disable();
}
