# streaming-data-validator

A lightweight Python module demonstrating robust, object-oriented data validation frameworks, production logging, and defensive error-handling circuit breakers for streaming pipelines.

## Run tests

Run the validation tests with:

```bash
python -m unittest -v
```

## Stop on the first invalid record

Pass `fail_fast=True` when a caller must stop reading its telemetry stream as
soon as validation fails:

```python
from validator import DataStreamValidator, generate_mock_records

records = iter(generate_mock_records())
validator = DataStreamValidator()
is_valid = validator.validate(records, fail_fast=True)
# False: the invalid record was consumed, but subsequent records remain unread.
```

The default (`fail_fast=False`) checks every record and returns `False` if any
record fails. Both modes accept iterables without buffering the entire stream.
Each call resets the circuit state; this is not a persistent service-level
circuit breaker. An empty input returns `True`.
