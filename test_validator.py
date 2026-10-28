"""Regression tests for telemetry record validation."""

import unittest
from typing import Any

from validator import DataStreamValidator


class DataStreamValidatorTests(unittest.TestCase):
    @staticmethod
    def _record(**overrides: Any) -> dict[str, Any]:
        record = {
            "device_id": "av-101",
            "timestamp": "2026-09-24T20:00:00Z",
            "temperature_c": 41.2,
            "battery_pct": 92,
        }
        record.update(overrides)
        return record

    def test_rejects_non_finite_temperatures(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                validator = DataStreamValidator()

                self.assertFalse(
                    validator.validate([self._record(temperature_c=value)])
                )
                self.assertTrue(validator.circuit_open)

    def test_accepts_finite_temperature(self) -> None:
        self.assertTrue(DataStreamValidator().validate([self._record()]))

    def test_rejects_non_string_timestamps(self) -> None:
        for value in (None, 1_797_897_600, {"value": "2026-12-25T00:00:00Z"}):
            with self.subTest(value=value):
                validator = DataStreamValidator()

                self.assertFalse(validator.validate([self._record(timestamp=value)]))
                self.assertTrue(validator.circuit_open)

    def test_rejects_timezone_naive_timestamps(self) -> None:
        validator = DataStreamValidator()

        self.assertFalse(
            validator.validate([self._record(timestamp="2026-09-24T20:00:00")])
        )
        self.assertTrue(validator.circuit_open)

    def test_accepts_explicit_timezone_offsets(self) -> None:
        record = self._record(timestamp="2026-09-24T15:00:00-05:00")

        self.assertTrue(DataStreamValidator().validate([record]))

    def test_non_object_records_open_circuit_without_crashing(self) -> None:
        for value in (None, [], "corrupt", 42, True):
            with self.subTest(value=value):
                validator = DataStreamValidator()
                with self.assertLogs("telemetry.validator", level="INFO") as logs:
                    self.assertFalse(validator.validate([value, self._record()]))
                self.assertTrue(validator.circuit_open)
                self.assertEqual([entry.levelname for entry in logs.records],
                                 ["CRITICAL", "INFO"])
                self.assertIn("device_id=unknown", logs.output[0])
                self.assertIn("record must be a JSON object", logs.output[0])
                self.assertIn("record_index=1", logs.output[1])


if __name__ == "__main__":
    unittest.main()
