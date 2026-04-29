#include "key_derivation.h"
#include "secure_memory.h"
#include "utilities.h"
#include <cstring>

#ifdef USE_BUNDLED_ARGON2
#include <argon2.h>
#else
extern "C" {
#include <argon2.h>
}
#endif

namespace crypter {

[[nodiscard]] std::expected<DerivedKeyResult, CrypterError> derive_key_argon2id(
    std::span<const std::uint8_t> passphrase,
    std::span<const std::uint8_t> pepper,
    std::span<const std::uint8_t> salt,
    KeyDerivationParams params
) {
    if (passphrase.empty()) {
        return std::unexpected{CrypterError::InvalidParameter};
    }
    if (params.key_size == 0 || params.key_size > 1024) {
        return std::unexpected{CrypterError::InvalidParameter};
    }
    if (params.salt_size == 0 || params.salt_size > 1024) {
        return std::unexpected{CrypterError::InvalidParameter};
    }

    std::vector<std::uint8_t> combined;
    combined.reserve(passphrase.size() + pepper.size());
    combined.insert(combined.end(), passphrase.begin(), passphrase.end());
    combined.insert(combined.end(), pepper.begin(), pepper.end());

    std::vector<std::uint8_t> use_salt;
    if (!salt.empty()) {
        use_salt.assign(salt.begin(), salt.end());
    } else {
        use_salt = random_bytes(params.salt_size);
    }

    std::vector<std::uint8_t> key(params.key_size);
    std::vector<std::uint8_t> iv;

    int rc = argon2id_hash_raw(
        static_cast<std::uint32_t>(params.ops_limit),
        static_cast<std::uint32_t>(params.mem_limit_kib),
        static_cast<std::uint32_t>(params.parallelism),
        combined.data(), combined.size(),
        use_salt.data(), use_salt.size(),
        key.data(), key.size()
    );

    if (rc != ARGON2_OK) {
        return std::unexpected{CrypterError::KeyDerivationFailed};
    }

    if (params.deterministic_iv_from_passphrase) {
        iv = deterministic_iv_from_passphrase(passphrase, use_salt);
    } else {
        iv = random_bytes(16);
    }

    // Secure wipe of sensitive intermediate data
    if (!combined.empty()) {
        std::memset(combined.data(), 0, combined.size());
    }

    return DerivedKeyResult{std::move(key), std::move(use_salt), std::move(iv), params};
}

} // namespace crypter
