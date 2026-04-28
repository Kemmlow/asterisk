#include "crypter_types.h"
#include <system_error>
#include <cerrno>

namespace crypter {

namespace {

class CrypterErrorCategory : public std::error_category {
public:
    const char* name() const noexcept override { return "crypter"; }
    std::string message(int ev) const override {
        switch (static_cast<CrypterError>(ev)) {
            case CrypterError::Success: return "Success";
            case CrypterError::InvalidKey: return "Invalid key";
            case CrypterError::InvalidNonce: return "Invalid nonce";
            case CrypterError::InvalidTag: return "Invalid tag";
            case CrypterError::InvalidCiphertext: return "Invalid ciphertext";
            case CrypterError::InvalidAssociatedData: return "Invalid associated data";
            case CrypterError::EncryptionFailed: return "Encryption failed";
            case CrypterError::DecryptionFailed: return "Decryption failed";
            case CrypterError::KeyDerivationFailed: return "Key derivation failed";
            case CrypterError::MemoryLockFailed: return "Memory lock failed";
            case CrypterError::InvalidParameter: return "Invalid parameter";
            case CrypterError::NotImplemented: return "Not implemented";
            case CrypterError::InternalError: return "Internal error";
            default: return "Unknown error";
        }
    }
};

const CrypterErrorCategory category{};

} // namespace

std::error_code make_error_code(CrypterError e) {
    return {static_cast<int>(e), category};
}

} // namespace crypter
