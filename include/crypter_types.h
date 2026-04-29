#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <system_error>
#include <expected>
#include <memory>

namespace crypter {

enum class CrypterError {
    Success = 0,
    InvalidKey,
    InvalidNonce,
    InvalidTag,
    InvalidCiphertext,
    InvalidAssociatedData,
    EncryptionFailed,
    DecryptionFailed,
    KeyDerivationFailed,
    MemoryLockFailed,
    InvalidParameter,
    NotImplemented,
    InternalError
};

std::error_code make_error_code(CrypterError e);

struct AuthenticatedBlob {
    std::vector<std::uint8_t> ciphertext;
    std::vector<std::uint8_t> iv;
    std::vector<std::uint8_t> tag;
    std::vector<std::uint8_t> associated_data;

    AuthenticatedBlob() = default;
    AuthenticatedBlob(
        std::vector<std::uint8_t> ct,
        std::vector<std::uint8_t> iv_,
        std::vector<std::uint8_t> tag_,
        std::vector<std::uint8_t> ad = {}
    ) : ciphertext(std::move(ct)), iv(std::move(iv_)), tag(std::move(tag_)), associated_data(std::move(ad)) {}
};

class ICrypter {
public:
    virtual ~ICrypter() = default;

    [[nodiscard]] virtual std::expected<AuthenticatedBlob, CrypterError> encrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> associated_data = {}
    ) = 0;

    [[nodiscard]] virtual std::expected<std::vector<std::uint8_t>, CrypterError> decrypt(
        const AuthenticatedBlob& blob
    ) = 0;

    virtual std::string name() const = 0;
};

using CrypterPtr = std::unique_ptr<ICrypter>;

} // namespace crypter

namespace std {
template<>
struct is_error_code_enum<crypter::CrypterError> : true_type {};
}
