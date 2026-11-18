import unittest
import uuid

from app.core.lora_protocol import ALERT, LoRaFrame, decode, encode


class LoRaProtocolTest(unittest.TestCase):
    def test_binary_frame_is_46_bytes_and_authenticated(self) -> None:
        key = b"field-test-key"
        frame = LoRaFrame(ALERT, str(uuid.uuid4()), 1, 1, 1, 9, 1700000000, 400, 250, 12000)
        packet = encode(frame, key)
        self.assertEqual(len(packet), 46)
        self.assertEqual(decode(packet, key), frame)

        damaged = bytearray(packet)
        damaged[10] ^= 1
        with self.assertRaisesRegex(ValueError, "HMAC"):
            decode(bytes(damaged), key)


if __name__ == "__main__":
    unittest.main()
