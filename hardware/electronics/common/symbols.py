"""Shared schematic symbol geometry."""


def graphic_line(points, dash=False):
    return (
        "(polyline (pts "
        + "".join(f"(xy {x} {y})" for x, y in points)
        + f") (stroke (width .254) (type {'dash' if dash else 'default'})) (fill (type none)))"
    )


def pin(number, name, x, y, angle, kind="passive"):
    return (str(number), name, x, y, angle, kind)


def symbol_units(name):
    if name == "DualAmp":
        shape = graphic_line([(-5.08, 5.08), (-5.08, -5.08), (5.08, 0), (-5.08, 5.08)])
        shape += "".join(
            graphic_line(p)
            for p in [
                [(-4.445, 2.54), (-3.175, 2.54)],
                [(-3.81, 1.905), (-3.81, 3.175)],
                [(-4.445, -2.54), (-3.175, -2.54)],
            ]
        )
        return [
            (
                1,
                shape,
                [
                    pin(3, "+", -7.62, 2.54, 0, "input"),
                    pin(2, "-", -7.62, -2.54, 0, "input"),
                    pin(1, "OUT", 7.62, 0, 180, "output"),
                ],
            ),
            (
                2,
                shape,
                [
                    pin(5, "+", -7.62, 2.54, 0, "input"),
                    pin(6, "-", -7.62, -2.54, 0, "input"),
                    pin(7, "OUT", 7.62, 0, 180, "output"),
                ],
            ),
            (
                3,
                "(rectangle (start -5.08 3.81) (end 5.08 -3.81) (stroke (width .254) (type default)) (fill (type none)))",
                [pin(8, "V+", -7.62, 2.54, 0, "power_in"), pin(4, "V-", -7.62, -2.54, 0, "power_in")],
            ),
        ]
    if name.startswith(("R", "C")) and name in ("RH", "RV", "CH"):
        if name == "CH":
            shape = "".join(
                graphic_line(p)
                for p in [
                    [(-2.54, 0), (-1.27, 0)],
                    [(-1.27, -3.81), (-1.27, 3.81)],
                    [(1.27, -3.81), (1.27, 3.81)],
                    [(1.27, 0), (2.54, 0)],
                ]
            )
        else:
            a, b = (-1.27, 2.54), (1.27, -2.54) if name == "RV" else (2.54, -1.27)
            if name == "RH":
                a = (-2.54, 1.27)
            shape = f"(rectangle (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width .254) (type default)) (fill (type none)))"
        return [
            (
                1,
                shape,
                [pin(1, "~", 0, 5.08, 270), pin(2, "~", 0, -5.08, 90)]
                if name == "RV"
                else [pin(1, "~", -5.08, 0, 0), pin(2, "~", 5.08, 0, 180)],
            )
        ]
    if name.startswith("Header"):
        count = int(name[6:])
        half = count * 2.54
        shape = f"(rectangle (start -2.54 {half}) (end 2.54 {-half}) (stroke (width .254) (type default)) (fill (type none)))"
        return [
            (
                1,
                shape,
                [pin(i + 1, str(i + 1), -5.08, (count - 1) * 2.54 - i * 5.08, 0) for i in range(count)],
            )
        ]
    if name == "Relay":
        shape = "(rectangle (start -11.43 2.54) (end -8.89 -2.54) (stroke (width .254) (type default)) (fill (type none)))"
        shape += "".join(
            graphic_line(p)
            for p in [
                [(-17.78, 5.08), (-10.16, 5.08), (-10.16, 2.54)],
                [(-17.78, -5.08), (-10.16, -5.08), (-10.16, -2.54)],
                [(-2.54, 10.16), (0, 10.16), (10.16, 15.24), (12.7, 15.24)],
                [(10.16, 5.08), (12.7, 5.08)],
                [(-2.54, -10.16), (0, -10.16), (10.16, -5.08), (12.7, -5.08)],
                [(10.16, -15.24), (12.7, -15.24)],
            ]
        )
        shape += graphic_line([(-8.89, 0), (2.54, 0)], True) + graphic_line(
            [(2.54, 11.43), (2.54, -8.89)], True
        )
        return [
            (
                1,
                shape,
                [
                    pin(1, "COIL+", -20.32, 5.08, 0),
                    pin(8, "COIL-", -20.32, -5.08, 0),
                    pin(3, "L_COM", -5.08, -10.16, 0),
                    pin(2, "L_NC", 15.24, -5.08, 180),
                    pin(4, "L_NO", 15.24, -15.24, 180),
                    pin(6, "R_COM", -5.08, 10.16, 0),
                    pin(7, "R_NC", 15.24, 15.24, 180),
                    pin(5, "R_NO", 15.24, 5.08, 180),
                ],
            )
        ]
    if name == "SupplyFlag":
        return [(1, "", [pin(1, "~", 0, 0, 90, "power_out")])]
    raise ValueError(name)
