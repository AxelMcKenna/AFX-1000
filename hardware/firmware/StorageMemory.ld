/* Supplement the pinned BOOT_SRAM linker script without changing its regions. */
SECTIONS
{
  .sdmmc_bss (NOLOAD) : ALIGN(32)
  {
    __sdmmc_start__ = .;
    KEEP(*(.sdmmc_bss))
    . = ALIGN(32);
    __sdmmc_end__ = .;
  } > SRAM
}
ASSERT(__sdmmc_start__ >= 0x24000000 && __sdmmc_end__ <= 0x24078000,
       "SDMMC DMA storage must fit in AXI SRAM")
