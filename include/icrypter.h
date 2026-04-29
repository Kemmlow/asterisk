#ifndef CRYPTER_ICRYPTER_H
#define CRYPTER_ICRYPTER_H

#include <cstdint>
#include <span>
#include <string>
#include <expected>
#include "crypter_types.h"

namespace crypter {

class ICrypter {
public:
    virtual ~ICrypter() = default;

    ICrypter(const ICrypter&) = delete;
    ICrypter& operator=(const ICrypter&) = delete;
    ICrypter(ICrypter&&) noexcept = default;
    ICrypter& operator=(ICrypter&&) noexcept = default;

    [[nodiscard]] virtual std::expected<AuthenticatedBlob, CrypterError> encrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> associated_data = {}
    ) = 0;

    [[nodiscard]] virtual std::expected<std::vector<std::uint8_t>, CrypterError> decrypt(
        const AuthenticatedBlob& blob
    ) = 0;

    [[nodiscard]] virtual std::string name() const = 0;

protected:
    ICrypter() = default;
};

using CrypterPtr = std::unique_ptr<ICrypter>;

} // namespace crypter

#endif // CRYPTER_ICRYPTER_H
