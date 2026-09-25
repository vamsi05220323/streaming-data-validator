"""Validate device telemetry before it reaches downstream consumers."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Mapping


LOGGER = logging.getLogger("telemetry.validator")


class DataStreamValidator:
    """Validate telemetry records and open a circuit on malformed input."""

    REQUIRED_FIELDS = ("device_id", "timestamp", "temperature_c", "battery_pct")

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER
        self.circuit_open = False

    def validate(self, records: list[Mapping[str, Any]]) -> bool:
        """Validate a batch; return True only when every record is valid."""
        self.circuit_open = False
        for index, record in enumerate(records):
            try:
                parsed = self._parse_record(record)
            except (KeyError, TypeError, ValueError) as error:
                self._trigger_circuit_breaker(index, record, str(error))
                continue
            except Exception as error:  # Defensive boundary for malformed sources.
                self._logger.exception(
                    "Unexpected validation failure", extra={"record_index": index}
                )
                self._trigger_circuit_breaker(index, record, type(error).__name__)
                continue

            self._logger.info(
                "event=record_validated record_index=%d device_id=%s",
                index,
                parsed["device_id"],
            )
        return not self.circuit_open

    def _parse_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(record, Mapping):
            raise TypeError("record must be a JSON object")
        missing = [field for field in self.REQUIRED_FIELDS if field not in record]
        if missing:
            raise KeyError(f"missing required fields: {', '.join(missing)}")
        if not isinstance(record["device_id"], str) or not record["device_id"].strip():
            raise TypeError("device_id must be a non-empty string")
        if isinstance(record["temperature_c"], bool) or not isinstance(
            record["temperature_c"], (int, float)
        ):
            raise TypeError("temperature_c must be numeric")
        if not isinstance(record["battery_pct"], int) or isinstance(record["battery_pct"], bool):
            raise TypeError("battery_pct must be an integer")
        if not 0 <= record["battery_pct"] <= 100:
            raise ValueError("battery_pct must be between 0 and 100")
        datetime.fromisoformat(str(record["timestamp"]).replace("Z", "+00:00"))
        return dict(record)

    def _trigger_circuit_breaker(
        self, index: int, record: Mapping[str, Any], reason: str
    ) -> None:
        self.circuit_open = True
        self._logger.critical(
            "event=circuit_breaker_opened record_index=%d device_id=%s reason=%r",
            index,
            record.get("device_id", "unknown"),
            reason,
        )


def generate_mock_records() -> list[dict[str, Any]]:
    """Return representative telemetry, including two intentionally bad records."""
    return [
        {"device_id": "av-101", "timestamp": "2026-09-24T20:00:00Z", "temperature_c": 41.2, "battery_pct": 92},
        {"device_id": "av-102", "timestamp": "2026-09-24T20:00:01Z", "temperature_c": 39.8, "battery_pct": 87},
        {"timestamp": "2026-09-24T20:00:02Z", "temperature_c": 40.1, "battery_pct": 81},
        {"device_id": "av-104", "timestamp": "2026-09-24T20:00:03Z", "temperature_c": "corrupt", "battery_pct": 76},
        {"device_id": "av-105", "timestamp": "2026-09-24T20:00:04Z", "temperature_c": 42.0, "battery_pct": 68},
        {"device_id": "av-106", "timestamp": "2026-09-24T20:00:05Z", "temperature_c": 38.7, "battery_pct": 95},
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s")
    records = generate_mock_records()
    validator = DataStreamValidator()
    is_valid = validator.validate(records)
    LOGGER.info("event=batch_validation_complete valid=%s", is_valid)
