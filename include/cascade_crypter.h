#pragma once

#include "crypter_types.h"
#include <memory>
#include <vector>

namespace crypter {

class CascadeCrypter : public ICrypter {
public:
    CascadeCrypter(CrypterPtr first, CrypterPtr second);
    ~CascadeCrypter() override = default;

    CascadeCrypter(const CascadeCrypter&) = delete;
    CascadeCrypter& operator=(const CascadeCrypter&) = delete;
    CascadeCrypter(CascadeCrypter&&) noexcept = default;
    CascadeCrypter& operator=(CascadeCrypter&&) noexcept = default;

    [[nodiscard]] std::expected<AuthenticatedBlob, CrypterError> encrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> associated_data = {}
    ) override;

    [[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> decrypt(
        const AuthenticatedBlob& blob
    ) override;

    std::string name() const override { return "Cascade"; }

private:
    CrypterPtr first_;
    CrypterPtr second_;
};

} // namespace crypter
