"""Strict structural replay with a four-ULP allowance ONLY for five-term sums.

All five summands must match exactly and be finite nonnegative binary64. Each
recorded total is also checked against the exactly summed rational terms, then
rounded to binary64. This does not round source values or loosen any receiving
limit; booleans, identities, hashes, geometry and all other numbers are exact.
"""

import math
import struct
from fractions import Fraction

MAX_ULP_STEPS = 4


def positive_ulp_steps(a, b):
    if (
        type(a) is not float
        or type(b) is not float
        or not (math.isfinite(a) and math.isfinite(b))
        or min(a, b) < 0
    ):
        raise ValueError("Finite nonnegative binary64 floats required")
    return abs(struct.unpack(">Q", struct.pack(">d", a))[0] - struct.unpack(">Q", struct.pack(">d", b))[0])


def allowed_total_path(path):
    if (
        len(path) == 6
        and path[0:2] == ("selection", "rows")
        and isinstance(path[2], int)
        and path[3] == "planning_error_scenarios"
        and isinstance(path[4], int)
        and path[5] == "total_fraction"
    ):
        return True
    if (
        path[0:2] == ("lifetime", "ordinary_TNPW")
        and len(path) == 5
        and path[2] in {"R92", "R93", "R94", "R97"}
        and path[3] in {"1000", "8000", "225000"}
        and path[4] == "total_fraction"
    ):
        return True
    return path in {
        ("lifetime", "R93_concrete_alternative", "planning_8000h", "total_fraction"),
        ("lifetime", "CRCW402_1000h", "total_fraction"),
        ("lifetime", "PRG402_1000h_option", "total_fraction"),
    }


def exact_rounded_sum(terms):
    if len(terms) != 5 or any(type(v) is not float or not math.isfinite(v) or v < 0 for v in terms.values()):
        raise ValueError("Exactly five finite nonnegative float summands required")
    return float(sum((Fraction.from_float(v) for v in terms.values()), Fraction(0)))


def compare(stored, replayed, path=(), parent_pair=None):
    errors, accepted = [], []
    if type(stored) is not type(replayed):
        return [dict(path=list(path), reason="Type mismatch")], []
    if isinstance(stored, dict):
        if stored.keys() != replayed.keys():
            return [dict(path=list(path), reason="Key mismatch")], []
        for key in stored:
            e, a = compare(stored[key], replayed[key], path + (key,), (stored, replayed))
            errors.extend(e)
            accepted.extend(a)
    elif isinstance(stored, list):
        if len(stored) != len(replayed):
            return [dict(path=list(path), reason="Length mismatch")], []
        for i, (s, r) in enumerate(zip(stored, replayed)):
            e, a = compare(s, r, path + (i,), (stored, replayed))
            errors.extend(e)
            accepted.extend(a)
    elif type(stored) is float:
        if not (math.isfinite(stored) and math.isfinite(replayed)):
            errors.append(dict(path=list(path), reason="Nonfinite float"))
        elif allowed_total_path(path):
            before, after = parent_pair
            if before.get("terms") != after.get("terms"):
                errors.append(dict(path=list(path), reason="Summands changed"))
            else:
                try:
                    correct = exact_rounded_sum(before["terms"])
                    distances = [
                        positive_ulp_steps(stored, replayed),
                        positive_ulp_steps(stored, correct),
                        positive_ulp_steps(replayed, correct),
                    ]
                    if max(distances) > MAX_ULP_STEPS:
                        errors.append(
                            dict(
                                path=list(path),
                                reason="Five-term sum exceeds four ULP steps",
                                distances=distances,
                            )
                        )
                    elif stored != replayed:
                        accepted.append(
                            dict(
                                path=list(path),
                                stored=stored,
                                replayed=replayed,
                                exact_rational_sum_rounded_binary64=correct,
                                ulp_distances=distances,
                                absolute_difference=abs(stored - replayed),
                            )
                        )
                except (ValueError, KeyError) as ex:
                    errors.append(dict(path=list(path), reason=str(ex)))
        elif stored != replayed:
            errors.append(
                dict(path=list(path), reason="Exact float mismatch", stored=stored, replayed=replayed)
            )
    elif stored != replayed:
        errors.append(dict(path=list(path), reason="Exact value mismatch"))
    return errors, accepted
