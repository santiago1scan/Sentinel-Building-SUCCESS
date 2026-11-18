#pragma once

// Este formato debe mantenerse igual al contrato C++ de protocol-contract.
#include <array>
#include <cstdint>

constexpr std::size_t SENTINEL_FRAME_BYTES = 46;

struct SentinelAlert {
  std::array<std::uint8_t, 16> uid;
  std::uint8_t node;
  std::uint8_t sensor;
  std::uint8_t event;
  std::uint32_t sequence;
  std::uint32_t timestamp;
  std::int16_t value_scaled;
  std::int16_t threshold_scaled;
  std::uint16_t battery_mv;
};
