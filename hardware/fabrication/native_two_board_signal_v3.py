"""Run the full signal circuit/PCB audit after power-flag stub cleanup."""
from hardware.fabrication import native_two_board_signal_v2 as native

if __name__ == "__main__":
    native.SOURCE = native.STAGING / "two-board-signal-integration-03"
    native.OUT = native.STAGING / "two-board-signal-native-03"
    native.run()
