"""Regression tests for telemetry record validation."""

import unittest

from validator import DataStreamValidator


class DataStreamValidatorTests(unittest.TestCase):
    def test_rejects_non_finite_temperatures(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                record = {
                    "device_id": "av-101",
                    "timestamp": "2026-09-24T20:00:00Z",
                    "temperature_c": value,
                    "battery_pct": 92,
                }
                validator = DataStreamValidator()

                self.assertFalse(validator.validate([record]))
                self.assertTrue(validator.circuit_open)

    def test_accepts_finite_temperature(self) -> None:
        record = {
            "device_id": "av-101",
            "timestamp": "2026-09-24T20:00:00Z",
            "temperature_c": 41.2,
            "battery_pct": 92,
        }

        self.assertTrue(DataStreamValidator().validate([record]))


if __name__ == "__main__":
    unittest.main()
