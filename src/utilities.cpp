#include "utilities.h"
#include <random>
#include <iomanip>
#include <sstream>
#include <cstring>

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")
#else
#include <sys/random.h>
#endif

namespace crypter {

int constant_time_compare(std::span<const std::uint8_t> a, std::span<const std::uint8_t> b) noexcept {
    if (a.size() != b.size()) {
        return 0;
    }
    volatile std::uint8_t result = 0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        result |= a[i] ^ b[i];
    }
    return result == 0 ? 1 : 0;
}

std::vector<std::uint8_t> random_bytes(std::size_t n) {
    std::vector<std::uint8_t> out(n);
#if defined(_WIN32) || defined(_WIN64)
    NTSTATUS status = BCryptGenRandom(nullptr, out.data(), static_cast<ULONG>(n), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (!BCRYPT_SUCCESS(status)) {
        std::fill(out.begin(), out.end(), 0);
        return out;
    }
#else
    if (getrandom(out.data(), n, 0) != static_cast<ssize_t>(n)) {
        std::fill(out.begin(), out.end(), 0);
        return out;
    }
#endif
    return out;
}

std::vector<std::uint8_t> deterministic_iv_from_passphrase(
    std::span<const std::uint8_t> passphrase,
    std::span<const std::uint8_t> salt
) {
    std::vector<std::uint8_t> iv(16);
    // Simple KDF-like derivation for deterministic IV (not for key material)
    std::vector<std::uint8_t> combined;
    combined.reserve(passphrase.size() + salt.size());
    combined.insert(combined.end(), passphrase.begin(), passphrase.end());
    combined.insert(combined.end(), salt.begin(), salt.end());

    std::uint64_t acc = 0xcbf29ce484222325ULL;
    for (std::uint8_t b : combined) {
        acc ^= b;
        acc *= 0x100000001b3ULL;
    }

    for (int i = 0; i < 8; ++i) {
        iv[i] = static_cast<std::uint8_t>((acc >> (i * 8)) & 0xFF);
        iv[i + 8] = static_cast<std::uint8_t>((~acc >> (i * 8)) & 0xFF);
    }

    if (!combined.empty()) {
        std::memset(combined.data(), 0, combined.size());
    }
    return iv;
}

std::string hex_encode(std::span<const std::uint8_t> bytes) {
    static const char* hexchars = "0123456789abcdef";
    std::string out;
    out.reserve(bytes.size() * 2);
    for (std::uint8_t b : bytes) {
        out.push_back(hexchars[(b >> 4) & 0x0F]);
        out.push_back(hexchars[b & 0x0F]);
    }
    return out;
}

std::expected<std::vector<std::uint8_t>, CrypterError> hex_decode(std::string_view hex) {
    if (hex.size() % 2 != 0) {
        return std::unexpected{CrypterError::InvalidParameter};
    }
    std::vector<std::uint8_t> out;
    out.reserve(hex.size() / 2);
    auto hexval = [](char c) -> std::uint8_t {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return 255;
    };
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        std::uint8_t hi = hexval(hex[i]);
        std::uint8_t lo = hexval(hex[i + 1]);
        if (hi > 15 || lo > 15) {
            return std::unexpected{CrypterError::InvalidParameter};
        }
        out.push_back((hi << 4) | lo);
    }
    return out;
}

} // namespace crypter
