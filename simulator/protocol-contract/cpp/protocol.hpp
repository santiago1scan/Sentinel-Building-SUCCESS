#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace sentinel {

constexpr std::size_t kBodyBytes = 38;
constexpr std::size_t kAuthBytes = 8;
constexpr std::size_t kFrameBytes = kBodyBytes + kAuthBytes;

enum class FrameType : std::uint8_t {
  Alert = 1,
  RadioAck = 2,
  HumanAck = 3,
  Heartbeat = 4,
};

struct AlertFrame {
  FrameType type;
  std::array<std::uint8_t, 16> message_uid;
  std::uint8_t node;
  std::uint8_t sensor;
  std::uint8_t event;
  std::uint32_t sequence;
  std::uint32_t timestamp;
  std::int16_t value_scaled;
  std::int16_t threshold_scaled;
  std::uint16_t battery_mv;
};

// Serializo campo por campo en orden de red. No envío la memoria directa de
// la estructura porque el relleno puede cambiar entre compiladores.
bool decode_and_authenticate(
    const std::array<std::uint8_t, kFrameBytes>& packet,
    const std::uint8_t* key,
    std::size_t key_size,
    AlertFrame& result);

}  // namespace sentinel
