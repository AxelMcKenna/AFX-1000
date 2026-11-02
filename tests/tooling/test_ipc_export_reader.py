"""Witness the IPC reader's units, alias preservation and fail-closed records."""

import unittest

from hardware.fabrication.inspect_rail_monitor_ipc import parse


def record():
    row = [" "] * 80
    row[:3] = "327"
    row[3:8] = "M0000"
    row[20:22] = "R1"
    row[26] = "-"
    row[27] = "1"
    location = "A01X+000100Y-000200"
    row[38:38+len(location)] = location
    return "".join(row)


class IPCExportReader(unittest.TestCase):
    def test_decimil_units_and_original_alias_name_are_preserved(self):
        text = "P  UNITS CUST 0\nP  NNAMEM0000 /A_LONG_SIGNAL_NAME\n"+record()+"\n999\n"
        aliases, rows = parse(text)
        self.assertEqual(aliases, {"M0000": "/A_LONG_SIGNAL_NAME"})
        self.assertEqual((rows[0]["ref"], rows[0]["pin"]), ("R1", "1"))
        self.assertAlmostEqual(rows[0]["x_mm"], 0.254)
        self.assertAlmostEqual(rows[0]["y_mm"], -0.508)

    def test_metric_or_truncated_record_is_rejected(self):
        for text in ["P  UNITS CUST 1\n"+record()+"\n999\n",
                     "P  UNITS CUST 0\n"+record()[:-1]+"\n999\n"]:
            with self.assertRaises(ValueError):
                parse(text)

    def test_duplicate_alias_or_unknown_record_is_rejected(self):
        for text in ["P  UNITS CUST 0\nP  NNAMEM0000 NET1\nP  NNAMEM0000 NET2\n999\n",
                     "P  UNITS CUST 0\n307"+record()[3:]+"\n999\n"]:
            with self.assertRaises(ValueError):
                parse(text)


if __name__ == "__main__":
    unittest.main()
