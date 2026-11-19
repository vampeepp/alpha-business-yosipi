"""
Schema Contract & Dead Letter Queue (DLQ) Replay Regression Tests.
Verifies backward-compatible schema adaptation, alias mapping, and zero-drop replay for yosipi telemetry.
"""

import unittest
from typing import Dict, Any


def parse_telemetry_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes drifted telemetry payload into unified schema."""
    # Resolve temperature alias
    temp = payload.get("temperature")
    if temp is None and "ambient_temp_c" in payload:
        temp = float(payload["ambient_temp_c"])
    else:
        temp = float(temp) if temp is not None else 0.0

    # Coerce humidity string/float
    humidity = payload.get("humidity")
    if humidity is None and "humidity_raw" in payload:
        humidity = float(payload["humidity_raw"])
    else:
        humidity = float(humidity) if humidity is not None else 0.0

    exec_id = payload.get("X-Devin-Execution-ID", "")
    is_remediation = bool(exec_id and exec_id.startswith("devin-exec-"))

    return {
        "event_id": str(payload.get("event_id", "")),
        "device_id": str(payload.get("device_id", "")),
        "timestamp": str(payload.get("timestamp", "")),
        "temperature": temp,
        "humidity": humidity,
        "firmware_version": str(payload.get("firmware_version", "unknown")),
        "execution_id": exec_id,
        "is_synthetic_remediation": is_remediation,
    }


def get_dlq_malformed_sensor_payload() -> Dict[str, Any]:
    """Simulates a drifted telemetry payload captured in the Kafka/S3 Dead Letter Queue."""
    return {
        "event_id": "dlq-evt-789a2b",
        "device_id": "sensor-grain-silo-04",
        "timestamp": "2026-11-19T14:22:10Z",
        "ambient_temp_c": 24.8,
        "humidity_raw": "62.4",
        "firmware_version": "v2.4.1",
        "X-Devin-Execution-ID": "devin-exec-88f01a",
    }


class TestSchemaContractAndDLQReplay(unittest.TestCase):

    def setUp(self):
        self.payload = get_dlq_malformed_sensor_payload()

    def test_schema_contract_backward_compatibility(self):
        """Verifies that drifted payloads normalize cleanly without validation errors."""
        event = parse_telemetry_event(self.payload)

        self.assertEqual(event["event_id"], "dlq-evt-789a2b")
        self.assertEqual(event["device_id"], "sensor-grain-silo-04")
        self.assertEqual(event["temperature"], 24.8)
        self.assertEqual(event["humidity"], 62.4)
        self.assertIsInstance(event["humidity"], float)
        self.assertTrue(event["is_synthetic_remediation"])

    def test_dlq_replay_batch_consumption(self):
        """Verifies batch consumption and zero error count during synthetic DLQ replay."""
        batch = [self.payload] * 10
        processed = []
        errors = 0

        for item in batch:
            try:
                evt = parse_telemetry_event(item)
                processed.append(evt)
            except Exception:
                errors += 1

        self.assertEqual(len(processed), 10)
        self.assertEqual(errors, 0)


if __name__ == "__main__":
    unittest.main()
