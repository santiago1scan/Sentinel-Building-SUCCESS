# Sentinel LoRa frame v1

Network byte order (big endian). Total: 46 bytes.

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 2 | Magic `SB` |
| 2 | 1 | Version |
| 3 | 1 | Frame type |
| 4 | 16 | Message UUID |
| 20 | 1 | Node code |
| 21 | 1 | Sensor code |
| 22 | 1 | Event code |
| 23 | 1 | Reserved |
| 24 | 4 | Sequence |
| 28 | 4 | Unix timestamp |
| 32 | 2 | Scaled value, signed |
| 34 | 2 | Scaled threshold, signed |
| 36 | 2 | Battery millivolts |
| 38 | 8 | Truncated HMAC-SHA256 |

Frame types: alert `1`, radio ACK `2`, human ACK `3`, heartbeat `4`.

The HMAC covers bytes 0–37. LoRa acknowledgement never marks the JSON 2.0 payload as delivered to the backend.
