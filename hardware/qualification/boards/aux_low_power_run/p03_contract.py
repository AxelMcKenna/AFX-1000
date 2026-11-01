"""End-to-end pin contract for the integrated source and actual E28 receiver."""

import math

from hardware.electronics.common.netlists import number


def interface(source_parts, source, receiver_parts, receiver):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(source["R113"] == {"1": "V2V5_AUX", "2": "SWITCH_SUPPLY"}
            and number(source_parts["R113"].findtext("value")) == 3300, "Original PG/switch pullup changed")
    require(source["U102"]["3"] == source["J104"]["2"] == source["U201"]["1"] == "POWER_RUN",
            "Internal RUN must retain its PG/switch path and supervisor sense input")
    require(source["U201"] == {"1": "POWER_RUN", "2": "AGND", "3": "V2V5_AUX",
            "4": "V2V5_AUX", "5": "AX03_SOURCE_CT", "6": "AX03_SOURCE_RESET"}, "Supervisor physical pin contract")
    require(source["U202"]["1"].startswith("unconnected-") and
            {p: source["U202"][p] for p in ("2", "3", "4", "5")} ==
            {"2": "AX03_SOURCE_RESET", "3": "AGND", "4": "AX03_RUN_DRIVE", "5": "V2V5_AUX"},
            "Source DCK Schmitt pin contract")
    require(source_parts["U201"].findtext("value") == "TPS389001DSET" and
            source_parts["U202"].findtext("value") == "SN74AUP1G17DCKR", "Selected source ICs changed")
    require(source["J106"] == {"1": "V2V5_AUX", "2": "AGND", "3": "POWER_RUN_E28_LEAF", "4": "P03_ALL_SOURCES_READY"},
            "J106 must carry the buffered leaf, not raw RUN")
    require(source["R403"] == {"1": "AX03_RUN_DRIVE", "2": "POWER_RUN_E28_LEAF"}
            and number(source_parts["R403"].findtext("value")) == 1000, "Output current-limit resistor changed")
    require(source["R401"] == {"1": "V2V5_AUX", "2": "AX03_SOURCE_RESET"}
            and source["R402"] == {"1": "AX03_SOURCE_RESET", "2": "AGND"}
            and number(source_parts["R401"].findtext("value")) == 100000
            and number(source_parts["R402"].findtext("value")) == 10000000, "Explicit RESET bias network changed")
    for cap in ("C401", "C402"):
        require(source[cap] == {"1": "V2V5_AUX", "2": "AGND"}
                and math.isclose(number(source_parts[cap].findtext("value")), 100e-9, rel_tol=1e-12), "Local bypass changed")
    require(source["C403"] == {"1": "AX03_SOURCE_CT", "2": "AGND"}
            and math.isclose(number(source_parts["C403"].findtext("value")), 10e-9, rel_tol=1e-12), "Supervisor timing capacitor changed")
    require(receiver["J5"] == {"1": "V2V5_AUX", "2": "AGND", "3": "POWER_RUN"}, "E28 raw-RUN connector mapping")
    require(receiver["J9"]["2"] == "P03_SOURCES_READY", "READY must reach the independent E28 READY input")
    require({p: receiver["U43"][p] for p in ("2", "3", "4", "5")} ==
            {"2": "POWER_RUN", "3": "AGND", "4": "RUN_BUFFERED", "5": "V2V5_AUX"}
            and receiver["U28"]["1"] == "RUN_BUFFERED", "E28 receiver must isolate the original U28 input")
    require(receiver_parts["U43"].findtext("value") == "SN74AUP1G17DCKR" and
            receiver["R93"] == {"1": "POWER_RUN", "2": "AGND"} and
            number(receiver_parts["R93"].findtext("value")) == 200000, "E28 high-impedance receiver changed")
    return [dict(signal=name, P03=f"J106.{pin}", E28=target, source_net=source["J106"][pin],
                 receiver_net=receiver[connector][receiver_pin])
            for name, pin, target, connector, receiver_pin in (
                ("AUX", "1", "J5.1", "J5", "1"), ("AGND", "2", "J5.2", "J5", "2"),
                ("buffered RUN", "3", "J5.3", "J5", "3"), ("independent READY", "4", "J9.2", "J9", "2"))]
