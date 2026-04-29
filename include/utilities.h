#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <span>

namespace crypter {

[[nodiscard]] int constant_time_compare(std::span<const std::uint8_t> a, std::span<const std::uint8_t> b) noexcept;

[[nodiscard]] std::vector<std::uint8_t> random_bytes(std::size_t n);

[[nodiscard]] std::vector<std::uint8_t> deterministic_iv_from_passphrase(
    std::span<const std::uint8_t> passphrase,
    std::span<const std::uint8_t> salt
);

[[nodiscard]] std::string hex_encode(std::span<const std::uint8_t> bytes);
[[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> hex_decode(std::string_view hex);

} // namespace crypter
