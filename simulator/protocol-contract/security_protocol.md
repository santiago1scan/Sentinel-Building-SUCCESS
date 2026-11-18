# Security contract

- HMAC-SHA256 authentication, truncated to 8 bytes for the Beta frame.
- Constant-time tag comparison.
- UUID deduplication.
- Monotonic sequence validation per node.
- Timestamp acceptance window in physical firmware.
- ACK frames are authenticated with the same contract.
- Development keys may come from environment variables.
- Production keys must be unique per installation, excluded from Git, provisioned securely and rotatable.
- HMAC authenticates but does not encrypt. Use AES-GCM or LoRaWAN when confidentiality is required.
