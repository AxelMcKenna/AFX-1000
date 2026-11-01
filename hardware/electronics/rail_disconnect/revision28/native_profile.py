"""Require explicit native check coverage as well as zero reported findings."""


def summarize(drc, erc):
    counts = {key: len(drc[key]) for key in ("violations", "unconnected_items", "schematic_parity")}
    counts["erc"] = sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", []))
    ignored = drc.get("ignored_checks")
    erc_ignored = erc.get("ignored_checks")
    drc_coverage_explicit = isinstance(ignored, list)
    erc_coverage_explicit = isinstance(erc_ignored, list)
    coverage_explicit = drc_coverage_explicit and erc_coverage_explicit
    drc_enabled = drc_coverage_explicit and not ignored
    erc_enabled = erc_coverage_explicit and not erc_ignored
    all_checks_enabled = drc_enabled and erc_enabled
    return {
        "counts": counts,
        "ignored_checks": ignored,
        "erc_ignored_checks": erc_ignored,
        "native_DRC_check_coverage_explicit": drc_coverage_explicit,
        "native_ERC_check_coverage_explicit": erc_coverage_explicit,
        "native_check_coverage_explicit": coverage_explicit,
        "all_native_DRC_rule_checks_enabled": drc_enabled,
        "all_native_ERC_rule_checks_enabled": erc_enabled,
        "all_native_rule_checks_enabled": all_checks_enabled,
        "native_closed": not any(counts.values()) and all_checks_enabled,
    }
