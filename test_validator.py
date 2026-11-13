"""Regression tests for telemetry record validation."""

import unittest
from typing import Any
from unittest.mock import patch

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

    def test_fail_fast_leaves_remaining_stream_unread(self) -> None:
        first = self._record(device_id="first")
        invalid = self._record(temperature_c="corrupt")
        remaining = self._record(device_id="remaining")
        records = iter([first, invalid, remaining])
        validator = DataStreamValidator()

        with self.assertLogs("telemetry.validator", level="INFO") as logs:
            self.assertFalse(validator.validate(records, fail_fast=True))

        self.assertTrue(validator.circuit_open)
        self.assertIs(next(records), remaining)
        self.assertEqual([entry.levelname for entry in logs.records],
                         ["INFO", "CRITICAL"])

    def test_default_mode_validates_records_after_failure(self) -> None:
        records = iter([self._record(temperature_c="corrupt"), self._record()])
        validator = DataStreamValidator()

        with self.assertLogs("telemetry.validator", level="INFO") as logs:
            self.assertFalse(validator.validate(records))

        self.assertTrue(validator.circuit_open)
        self.assertEqual([entry.levelname for entry in logs.records],
                         ["CRITICAL", "INFO"])
        self.assertEqual(list(records), [])

    def test_fail_fast_stops_after_unexpected_parser_error(self) -> None:
        remaining = self._record(device_id="remaining")
        records = iter([self._record(), remaining])
        validator = DataStreamValidator()

        with patch.object(validator, "_parse_record", side_effect=RuntimeError("parser failed")):
            with self.assertLogs("telemetry.validator", level="ERROR"):
                self.assertFalse(validator.validate(records, fail_fast=True))

        self.assertTrue(validator.circuit_open)
        self.assertIs(next(records), remaining)

    def test_fail_fast_accepts_valid_and_empty_streams(self) -> None:
        for records in ([self._record()], []):
            with self.subTest(records=records):
                validator = DataStreamValidator()
                self.assertTrue(validator.validate(iter(records), fail_fast=True))
                self.assertFalse(validator.circuit_open)


if __name__ == "__main__":
    unittest.main()
