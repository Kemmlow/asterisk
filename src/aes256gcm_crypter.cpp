#include "aes256gcm_crypter.h"
#include "secure_memory.h"
#include "utilities.h"
#include <openssl/evp.h>
#include <openssl/err.h>
#include <cstring>
#include <system_error>

namespace crypter {

struct AES256GCM_Crypter::Impl {
    std::vector<std::uint8_t> key;

    explicit Impl(std::span<const std::uint8_t, KeySize> k) : key(k.begin(), k.end()) {}
};

AES256GCM_Crypter::AES256GCM_Crypter(std::span<const std::uint8_t, KeySize> key)
    : pimpl_(std::make_unique<Impl>(key)) {}

AES256GCM_Crypter::~AES256GCM_Crypter() = default;

AES256GCM_Crypter::AES256GCM_Crypter(AES256GCM_Crypter&&) noexcept = default;
AES256GCM_Crypter& AES256GCM_Crypter::operator=(AES256GCM_Crypter&&) noexcept = default;

[[nodiscard]] std::expected<AuthenticatedBlob, CrypterError> AES256GCM_Crypter::encrypt(
    std::span<const std::uint8_t> plaintext,
    std::span<const std::uint8_t> associated_data
) {
    if (pimpl_->key.size() != KeySize) {
        return std::unexpected{CrypterError::InvalidKey};
    }

    auto iv = random_bytes(IVSize);
    std::vector<std::uint8_t> tag(TagSize);
    std::vector<std::uint8_t> ciphertext(plaintext.size());

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }

    auto cleanup = [](EVP_CIPHER_CTX* c) {
        if (c) {
            EVP_CIPHER_CTX_free(c);
        }
    };
    std::unique_ptr<EVP_CIPHER_CTX, decltype(cleanup)> guard(ctx, cleanup);

    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(IVSize), nullptr) != 1) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }

    if (EVP_EncryptInit_ex(ctx, nullptr, nullptr, pimpl_->key.data(), iv.data()) != 1) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }

    if (!associated_data.empty()) {
        int len = 0;
        if (EVP_EncryptUpdate(ctx, nullptr, &len, associated_data.data(), static_cast<int>(associated_data.size())) != 1) {
            return std::unexpected{CrypterError::EncryptionFailed};
        }
    }

    int len = 0;
    if (!plaintext.empty()) {
        if (EVP_EncryptUpdate(ctx, ciphertext.data(), &len, plaintext.data(), static_cast<int>(plaintext.size())) != 1) {
            return std::unexpected{CrypterError::EncryptionFailed};
        }
    }

    int ciphertext_len = len;
    if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len) != 1) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }
    ciphertext_len += len;

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, static_cast<int>(TagSize), tag.data()) != 1) {
        return std::unexpected{CrypterError::EncryptionFailed};
    }

    ciphertext.resize(static_cast<std::size_t>(ciphertext_len));
    return AuthenticatedBlob{std::move(ciphertext), std::move(iv), std::move(tag),
        std::vector<std::uint8_t>(associated_data.begin(), associated_data.end())};
}

[[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> AES256GCM_Crypter::decrypt(
    const AuthenticatedBlob& blob
) {
    if (pimpl_->key.size() != KeySize) {
        return std::unexpected{CrypterError::InvalidKey};
    }
    if (blob.iv.size() != IVSize) {
        return std::unexpected{CrypterError::InvalidNonce};
    }
    if (blob.tag.size() != TagSize) {
        return std::unexpected{CrypterError::InvalidTag};
    }

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        return std::unexpected{CrypterError::DecryptionFailed};
    }

    auto cleanup = [](EVP_CIPHER_CTX* c) {
        if (c) {
            EVP_CIPHER_CTX_free(c);
        }
    };
    std::unique_ptr<EVP_CIPHER_CTX, decltype(cleanup)> guard(ctx, cleanup);

    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1) {
        return std::unexpected{CrypterError::DecryptionFailed};
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(IVSize), nullptr) != 1) {
        return std::unexpected{CrypterError::DecryptionFailed};
    }

    if (EVP_DecryptInit_ex(ctx, nullptr, nullptr, pimpl_->key.data(), blob.iv.data()) != 1) {
        return std::unexpected{CrypterError::DecryptionFailed};
    }

    if (!blob.associated_data.empty()) {
        int len = 0;
        if (EVP_DecryptUpdate(ctx, nullptr, &len, blob.associated_data.data(), static_cast<int>(blob.associated_data.size())) != 1) {
            return std::unexpected{CrypterError::DecryptionFailed};
        }
    }

    std::vector<std::uint8_t> plaintext(blob.ciphertext.size());
    int len = 0;
    if (!blob.ciphertext.empty()) {
        if (EVP_DecryptUpdate(ctx, plaintext.data(), &len, blob.ciphertext.data(), static_cast<int>(blob.ciphertext.size())) != 1) {
            return std::unexpected{CrypterError::DecryptionFailed};
        }
    }

    int plaintext_len = len;
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, static_cast<int>(TagSize), const_cast<std::uint8_t*>(blob.tag.data())) != 1) {
        return std::unexpected{CrypterError::InvalidTag};
    }

    if (EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len) != 1) {
        return std::unexpected{CrypterError::DecryptionFailed};
    }
    plaintext_len += len;
    plaintext.resize(static_cast<std::size_t>(plaintext_len));
    return plaintext;
}

} // namespace crypter
