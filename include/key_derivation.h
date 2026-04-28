#pragma once

#include <cstdint>
#include <span>
#include <vector>
#include <string>
#include <expected>

namespace crypter {

struct KeyDerivationParams {
    std::uint32_t ops_limit = 4;
    std::uint32_t mem_limit_kib = 65536;
    std::uint32_t parallelism = 1;
    std::size_t salt_size = 16;
    std::size_t key_size = 32;
    bool deterministic_iv_from_passphrase = false;
};

struct DerivedKeyResult {
    std::vector<std::uint8_t> key;
    std::vector<std::uint8_t> salt;
    std::vector<std::uint8_t> iv;
    KeyDerivationParams params;
};

[[nodiscard]] std::expected<DerivedKeyResult, CrypterError> derive_key_argon2id(
    std::span<const std::uint8_t> passphrase,
    std::span<const std::uint8_t> pepper = {},
    std::span<const std::uint8_t> salt = {},
    KeyDerivationParams params = {}
);

} // namespace crypter
