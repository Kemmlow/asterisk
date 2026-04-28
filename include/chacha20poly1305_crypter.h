#pragma once

#include "crypter_types.h"
#include <memory>

namespace crypter {

class ChaCha20Poly1305_Crypter : public ICrypter {
public:
    static constexpr std::size_t KeySize = 32;
    static constexpr std::size_t NonceSize = 12;
    static constexpr std::size_t TagSize = 16;

    explicit ChaCha20Poly1305_Crypter(std::span<const std::uint8_t, KeySize> key);
    ~ChaCha20Poly1305_Crypter() override;

    ChaCha20Poly1305_Crypter(const ChaCha20Poly1305_Crypter&) = delete;
    ChaCha20Poly1305_Crypter& operator=(const ChaCha20Poly1305_Crypter&) = delete;
    ChaCha20Poly1305_Crypter(ChaCha20Poly1305_Crypter&&) noexcept;
    ChaCha20Poly1305_Crypter& operator=(ChaCha20Poly1305_Crypter&&) noexcept;

    [[nodiscard]] std::expected<AuthenticatedBlob, CrypterError> encrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> associated_data = {}
    ) override;

    [[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> decrypt(
        const AuthenticatedBlob& blob
    ) override;

    std::string name() const override { return "ChaCha20-Poly1305"; }

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace crypter
