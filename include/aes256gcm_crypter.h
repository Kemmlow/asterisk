#pragma once

#include "crypter_types.h"
#include <memory>

namespace crypter {

class AES256GCM_Crypter : public ICrypter {
public:
    static constexpr std::size_t KeySize = 32;
    static constexpr std::size_t IVSize = 12;
    static constexpr std::size_t TagSize = 16;

    explicit AES256GCM_Crypter(std::span<const std::uint8_t, KeySize> key);
    ~AES256GCM_Crypter() override;

    AES256GCM_Crypter(const AES256GCM_Crypter&) = delete;
    AES256GCM_Crypter& operator=(const AES256GCM_Crypter&) = delete;
    AES256GCM_Crypter(AES256GCM_Crypter&&) noexcept;
    AES256GCM_Crypter& operator=(AES256GCM_Crypter&&) noexcept;

    [[nodiscard]] std::expected<AuthenticatedBlob, CrypterError> encrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> associated_data = {}
    ) override;

    [[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> decrypt(
        const AuthenticatedBlob& blob
    ) override;

    std::string name() const override { return "AES-256-GCM"; }

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace crypter
