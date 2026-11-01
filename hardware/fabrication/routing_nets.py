"""Explicit logic-net selection shared by host geometry and Linux exporters."""

LOGIC_TOKENS = ("FAULT", "READY", "VALID", "COMPLETE", "PERMIT", "ARM_", "START", "SAFE", "WDO", "WD_", "PCLR", "MASTER", "CLAMPS_RELEASE", "SUPPLY_ENABLE", "CONTROLLER_ON")


def is_logic_net(net):
    excluded = ("_CT", "_SENSE", "_REF", "_RMID", "_HOST5", "_GATE", "_SOURCE", "_VIN", "_INTVCC")
    return any(token in net for token in LOGIC_TOKENS) and not net.endswith(excluded)
