#include "crypter.hpp"

#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <system_error>

#if defined(_WIN32)
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")
#else
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#endif

namespace hyper_crypt
{

namespace
{

class openssl_initializer final
{
public:
    openssl_initializer()
    {
#if !defined(_WIN32)
        // OpenSSL 3.0+ does not require explicit init in most cases,
        // but we ensure algorithms are available.
        if (EVP_get_cipherbyname("aes-256-gcm") == nullptr)
        {
            throw std::runtime_error("AES-256-GCM cipher not available in OpenSSL");
        }
#endif
    }

    ~openssl_initializer() = default;

    openssl_initializer(const openssl_initializer&) = delete;
    openssl_initializer(openssl_initializer&&) = delete;
    auto operator=(const openssl_initializer&) -> openssl_initializer& = delete;
    auto operator=(openssl_initializer&&) -> openssl_initializer& = delete;
};

const openssl_initializer g_openssl_initializer;

void secure_memzero(void* ptr, std::size_t size) noexcept
{
    if (ptr == nullptr || size == 0)
    {
        return;
    }
    volatile unsigned char* p = static_cast<volatile unsigned char*>(ptr);
    while (size--)
    {
        *p++ = 0;
    }
}

class sha256_hasher final
{
public:
    static constexpr std::size_t digest_size = 32;

    sha256_hasher()
    {
#if defined(_WIN32)
        NTSTATUS status = BCryptOpenAlgorithmProvider(&m_algorithm_handle, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
        if (!BCRYPT_SUCCESS(status))
        {
            throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to open SHA256 algorithm");
        }

        status = BCryptCreateHash(m_algorithm_handle, &m_hash_handle, nullptr, 0, nullptr, 0, 0);
        if (!BCRYPT_SUCCESS(status))
        {
            BCryptCloseAlgorithmProvider(m_algorithm_handle, 0);
            throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to create SHA256 hash");
        }
#else
        m_context = EVP_MD_CTX_new();
        if (m_context == nullptr)
        {
            throw std::runtime_error("Failed to allocate SHA256 context");
        }

        if (EVP_DigestInit_ex(m_context, EVP_sha256(), nullptr) != 1)
        {
            EVP_MD_CTX_free(m_context);
            throw std::runtime_error("Failed to initialize SHA256 digest");
        }
#endif
    }

    ~sha256_hasher()
    {
#if defined(_WIN32)
        if (m_hash_handle != nullptr)
        {
            BCryptDestroyHash(m_hash_handle);
        }
        if (m_algorithm_handle != nullptr)
        {
            BCryptCloseAlgorithmProvider(m_algorithm_handle, 0);
        }
#else
        if (m_context != nullptr)
        {
            EVP_MD_CTX_free(m_context);
        }
#endif
    }

    sha256_hasher(const sha256_hasher&) = delete;
    sha256_hasher(sha256_hasher&&) = delete;
    auto operator=(const sha256_hasher&) -> sha256_hasher& = delete;
    auto operator=(sha256_hasher&&) -> sha256_hasher& = delete;

    void update(std::span<const std::uint8_t> data)
    {
#if defined(_WIN32)
        NTSTATUS status = BCryptHashData(m_hash_handle, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(data.data())),
                                         static_cast<ULONG>(data.size()), 0);
        if (!BCRYPT_SUCCESS(status))
        {
            throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to update SHA256 hash");
        }
#else
        if (EVP_DigestUpdate(m_context, data.data(), data.size()) != 1)
        {
            throw std::runtime_error("Failed to update SHA256 digest");
        }
#endif
    }

    void finalize(std::span<std::uint8_t, digest_size> output)
    {
#if defined(_WIN32)
        NTSTATUS status = BCryptFinishHash(m_hash_handle, output.data(), static_cast<ULONG>(output.size()), 0);
        if (!BCRYPT_SUCCESS(status))
        {
            throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to finalize SHA256 hash");
        }
#else
        unsigned int written = 0;
        if (EVP_DigestFinal_ex(m_context, output.data(), &written) != 1)
        {
            throw std::runtime_error("Failed to finalize SHA256 digest");
        }
        if (written != digest_size)
        {
            throw std::runtime_error("SHA256 digest size mismatch");
        }
#endif
    }

private:
#if defined(_WIN32)
    BCRYPT_ALG_HANDLE m_algorithm_handle = nullptr;
    BCRYPT_HASH_HANDLE m_hash_handle = nullptr;
#else
    EVP_MD_CTX* m_context = nullptr;
#endif
};

} // namespace

secure_memory_block::secure_memory_block(std::size_t size)
    : m_ptr(secure_allocate(size), &secure_memory_block::secure_deallocate), m_size(size)
{
    if (size > 0 && m_ptr == nullptr)
    {
        throw std::bad_alloc();
    }
}

secure_memory_block::secure_memory_block(const void* data, std::size_t size)
    : secure_memory_block(size)
{
    if (data != nullptr && size > 0)
    {
        std::memcpy(m_ptr.get(), data, size);
    }
}

secure_memory_block::secure_memory_block(secure_memory_block&& other) noexcept
    : m_ptr(std::move(other.m_ptr)), m_size(other.m_size)
{
    other.m_size = 0;
}

auto secure_memory_block::operator=(secure_memory_block&& other) noexcept -> secure_memory_block&
{
    if (this != &other)
    {
        m_ptr = std::move(other.m_ptr);
        m_size = other.m_size;
        other.m_size = 0;
    }
    return *this;
}

secure_memory_block::~secure_memory_block()
{
    zeroize();
}

auto secure_memory_block::data() noexcept -> void*
{
    return m_ptr.get();
}

auto secure_memory_block::data() const noexcept -> const void*
{
    return m_ptr.get();
}

auto secure_memory_block::size() const noexcept -> std::size_t
{
    return m_size;
}

auto secure_memory_block::span() noexcept -> std::span<std::uint8_t>
{
    return std::span<std::uint8_t>(m_ptr.get(), m_size);
}

auto secure_memory_block::span() const noexcept -> std::span<const std::uint8_t>
{
    return std::span<const std::uint8_t>(m_ptr.get(), m_size);
}

void secure_memory_block::zeroize() noexcept
{
    if (m_ptr != nullptr)
    {
        secure_memzero(m_ptr.get(), m_size);
    }
}

void secure_memory_block::resize(std::size_t new_size)
{
    if (new_size == m_size)
    {
        return;
    }

    auto new_ptr = std::unique_ptr<std::uint8_t[], decltype(&secure_memory_block::secure_deallocate)>(
        secure_allocate(new_size), &secure_memory_block::secure_deallocate);

    if (new_ptr == nullptr)
    {
        throw std::bad_alloc();
    }

    const std::size_t copy_size = std::min(m_size, new_size);
    if (copy_size > 0)
    {
        std::memcpy(new_ptr.get(), m_ptr.get(), copy_size);
    }

    zeroize();
    m_ptr = std::move(new_ptr);
    m_size = new_size;
}

auto secure_memory_block::secure_allocate(std::size_t size) -> std::uint8_t*
{
    if (size == 0)
    {
        return nullptr;
    }

#if defined(_WIN32)
    auto* ptr = static_cast<std::uint8_t*>(HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, size));
    if (ptr == nullptr)
    {
        throw std::bad_alloc();
    }

    // Lock memory to prevent paging to disk
    if (VirtualLock(ptr, size) == 0)
    {
        HeapFree(GetProcessHeap(), 0, ptr);
        throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), "Failed to lock memory");
    }

    return ptr;
#else
    // Use mlock to prevent paging to disk on POSIX systems
    auto* ptr = static_cast<std::uint8_t*>(std::aligned_alloc(64, size));
    if (ptr == nullptr)
    {
        throw std::bad_alloc();
    }

    if (mlock(ptr, size) != 0)
    {
        std::free(ptr);
        throw std::system_error(errno, std::system_category(), "Failed to lock memory");
    }

    // Explicitly zero the memory
    secure_memzero(ptr, size);
    return ptr;
#endif
}

void secure_memory_block::secure_deallocate(std::uint8_t* ptr) noexcept
{
    if (ptr == nullptr)
    {
        return;
    }

#if defined(_WIN32)
    SecureZeroMemory(ptr, 0); // Size unknown at deallocation, rely on prior zeroization
    HeapFree(GetProcessHeap(), 0, ptr);
#else
    munlock(ptr, 0); // Size should be tracked separately; zeroization done in destructor
    std::free(ptr);
#endif
}

aes_256_gcm_engine::encryption_result aes_256_gcm_engine::encrypt(std::span<const std::uint8_t> plaintext,
                                                                  std::span<const std::uint8_t> password)
{
    if (plaintext.empty())
    {
        throw std::invalid_argument("Plaintext cannot be empty");
    }

    if (password.size() < 8)
    {
        throw std::invalid_argument("Password must be at least 8 bytes");
    }

    encryption_result result;
    result.initialization_vector = generate_random_bytes(iv_size);
    result.salt = generate_random_bytes(salt_size);

    const auto derived_key = derive_key(password, result.salt.span());

#if defined(_WIN32)
    BCRYPT_ALG_HANDLE algorithm_handle = nullptr;
    BCRYPT_KEY_HANDLE key_handle = nullptr;
    NTSTATUS status = BCryptOpenAlgorithmProvider(&algorithm_handle, BCRYPT_AES_ALGORITHM, nullptr, 0);
    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to open AES algorithm");
    }

    status = BCryptSetProperty(algorithm_handle, BCRYPT_CHAINING_MODE, reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_GCM)),
                               sizeof(BCRYPT_CHAIN_MODE_GCM), 0);
    if (!BCRYPT_SUCCESS(status))
    {
        BCryptCloseAlgorithmProvider(algorithm_handle, 0);
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to set chaining mode");
    }

    status = BCryptGenerateSymmetricKey(algorithm_handle, &key_handle, nullptr, 0, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(derived_key.data())),
                                        static_cast<ULONG>(derived_key.size()), 0);
    if (!BCRYPT_SUCCESS(status))
    {
        BCryptCloseAlgorithmProvider(algorithm_handle, 0);
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to generate symmetric key");
    }

    result.ciphertext.resize(plaintext.size());
    result.authentication_tag.resize(tag_size);

    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth_info;
    BCRYPT_INIT_AUTH_MODE_INFO(auth_info);
    auth_info.pbNonce = const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(result.initialization_vector.data()));
    auth_info.cbNonce = static_cast<ULONG>(result.initialization_vector.size());
    auth_info.pbTag = result.authentication_tag.data();
    auth_info.cbTag = static_cast<ULONG>(result.authentication_tag.size());
    auth_info.pbMacContext = nullptr;
    auth_info.cbMacContext = 0;
    auth_info.dwFlags = 0;

    ULONG bytes_written = 0;
    status = BCryptEncrypt(key_handle, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(plaintext.data())),
                           static_cast<ULONG>(plaintext.size()), &auth_info, nullptr, 0, result.ciphertext.data(),
                           static_cast<ULONG>(result.ciphertext.size()), &bytes_written, 0);

    BCryptDestroyKey(key_handle);
    BCryptCloseAlgorithmProvider(algorithm_handle, 0);

    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Encryption failed");
    }

    if (bytes_written != plaintext.size())
    {
        throw std::runtime_error("Encryption output size mismatch");
    }

#else
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (ctx == nullptr)
    {
        throw std::runtime_error("Failed to create cipher context");
    }

    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to initialize encryption");
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(iv_size), nullptr) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to set IV length");
    }

    if (EVP_EncryptInit_ex(ctx, nullptr, nullptr, derived_key.data(), result.initialization_vector.data()) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to set key and IV");
    }

    result.ciphertext.resize(plaintext.size());
    result.authentication_tag.resize(tag_size);

    int out_len = 0;
    int tmp_len = 0;

    if (EVP_EncryptUpdate(ctx, result.ciphertext.data(), &out_len, plaintext.data(), static_cast<int>(plaintext.size())) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Encryption update failed");
    }

    if (EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + out_len, &tmp_len) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Encryption finalization failed");
    }

    out_len += tmp_len;

    if (static_cast<std::size_t>(out_len) != plaintext.size())
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Encryption output size mismatch");
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, static_cast<int>(tag_size), result.authentication_tag.data()) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to get authentication tag");
    }

    EVP_CIPHER_CTX_free(ctx);
#endif

    return result;
}

aes_256_gcm_engine::decryption_result aes_256_gcm_engine::decrypt(std::span<const std::uint8_t> ciphertext,
                                                                  std::span<const std::uint8_t> authentication_tag,
                                                                  std::span<const std::uint8_t> initialization_vector,
                                                                  std::span<const std::uint8_t> salt,
                                                                  std::span<const std::uint8_t> password)
{
    if (ciphertext.empty())
    {
        throw std::invalid_argument("Ciphertext cannot be empty");
    }

    if (authentication_tag.size() != tag_size)
    {
        throw std::invalid_argument("Invalid authentication tag size");
    }

    if (initialization_vector.size() != iv_size)
    {
        throw std::invalid_argument("Invalid initialization vector size");
    }

    if (salt.size() != salt_size)
    {
        throw std::invalid_argument("Invalid salt size");
    }

    if (password.size() < 8)
    {
        throw std::invalid_argument("Password must be at least 8 bytes");
    }

    const auto derived_key = derive_key(password, salt);

#if defined(_WIN32)
    BCRYPT_ALG_HANDLE algorithm_handle = nullptr;
    BCRYPT_KEY_HANDLE key_handle = nullptr;
    NTSTATUS status = BCryptOpenAlgorithmProvider(&algorithm_handle, BCRYPT_AES_ALGORITHM, nullptr, 0);
    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to open AES algorithm");
    }

    status = BCryptSetProperty(algorithm_handle, BCRYPT_CHAINING_MODE, reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_GCM)),
                               sizeof(BCRYPT_CHAIN_MODE_GCM), 0);
    if (!BCRYPT_SUCCESS(status))
    {
        BCryptCloseAlgorithmProvider(algorithm_handle, 0);
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to set chaining mode");
    }

    status = BCryptGenerateSymmetricKey(algorithm_handle, &key_handle, nullptr, 0, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(derived_key.data())),
                                        static_cast<ULONG>(derived_key.size()), 0);
    if (!BCRYPT_SUCCESS(status))
    {
        BCryptCloseAlgorithmProvider(algorithm_handle, 0);
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to generate symmetric key");
    }

    decryption_result result;
    result.plaintext.resize(ciphertext.size());

    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth_info;
    BCRYPT_INIT_AUTH_MODE_INFO(auth_info);
    auth_info.pbNonce = const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(initialization_vector.data()));
    auth_info.cbNonce = static_cast<ULONG>(initialization_vector.size());
    auth_info.pbTag = const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(authentication_tag.data()));
    auth_info.cbTag = static_cast<ULONG>(authentication_tag.size());
    auth_info.pbMacContext = nullptr;
    auth_info.cbMacContext = 0;
    auth_info.dwFlags = 0;

    ULONG bytes_written = 0;
    status = BCryptDecrypt(key_handle, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(ciphertext.data())),
                           static_cast<ULONG>(ciphertext.size()), &auth_info, nullptr, 0, result.plaintext.data(),
                           static_cast<ULONG>(result.plaintext.size()), &bytes_written, 0);

    BCryptDestroyKey(key_handle);
    BCryptCloseAlgorithmProvider(algorithm_handle, 0);

    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Decryption failed - authentication likely failed");
    }

    if (bytes_written != ciphertext.size())
    {
        throw std::runtime_error("Decryption output size mismatch");
    }

#else
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (ctx == nullptr)
    {
        throw std::runtime_error("Failed to create cipher context");
    }

    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to initialize decryption");
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, static_cast<int>(iv_size), nullptr) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to set IV length");
    }

    if (EVP_DecryptInit_ex(ctx, nullptr, nullptr, derived_key.data(), initialization_vector.data()) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to set key and IV");
    }

    decryption_result result;
    result.plaintext.resize(ciphertext.size());

    int out_len = 0;
    int tmp_len = 0;

    if (EVP_DecryptUpdate(ctx, result.plaintext.data(), &out_len, ciphertext.data(), static_cast<int>(ciphertext.size())) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Decryption update failed");
    }

    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, static_cast<int>(tag_size), const_cast<void*>(static_cast<const void*>(authentication_tag.data()))) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to set authentication tag");
    }

    if (EVP_DecryptFinal_ex(ctx, result.plaintext.data() + out_len, &tmp_len) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Decryption finalization failed - authentication tag mismatch");
    }

    out_len += tmp_len;

    if (static_cast<std::size_t>(out_len) != ciphertext.size())
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Decryption output size mismatch");
    }

    EVP_CIPHER_CTX_free(ctx);
#endif

    return result;
}

auto aes_256_gcm_engine::derive_key(std::span<const std::uint8_t> password, std::span<const std::uint8_t> salt) const -> secure_memory_block
{
    secure_memory_block key(key_size);

#if defined(_WIN32)
    BCRYPT_ALG_HANDLE algorithm_handle = nullptr;
    NTSTATUS status = BCryptOpenAlgorithmProvider(&algorithm_handle, BCRYPT_SHA256_ALGORITHM, nullptr, BCRYPT_ALG_HANDLE_HMAC_FLAG);
    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to open SHA256 algorithm for PBKDF2");
    }

    status = BCryptDeriveKeyPBKDF2(algorithm_handle, const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(password.data())),
                                   static_cast<ULONG>(password.size()), const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(salt.data())),
                                   static_cast<ULONG>(salt.size()), iterations, key.data(), static_cast<ULONG>(key.size()), 0);

    BCryptCloseAlgorithmProvider(algorithm_handle, 0);

    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "PBKDF2 key derivation failed");
    }

#else
    if (PKCS5_PBKDF2_HMAC(reinterpret_cast<const char*>(password.data()), static_cast<int>(password.size()),
                          salt.data(), static_cast<int>(salt.size()), static_cast<int>(iterations),
                          EVP_sha256(), static_cast<int>(key_size), key.data()) != 1)
    {
        throw std::runtime_error("PBKDF2 key derivation failed");
    }
#endif

    return key;
}

auto aes_256_gcm_engine::generate_random_bytes(std::size_t count) -> secure_memory_block
{
    secure_memory_block result(count);

#if defined(_WIN32)
    NTSTATUS status = BCryptGenRandom(nullptr, result.data(), static_cast<ULONG>(result.size()), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (!BCRYPT_SUCCESS(status))
    {
        throw std::system_error(static_cast<int>(status), std::system_category(), "Failed to generate random bytes");
    }
#else
    if (RAND_bytes(result.data(), static_cast<int>(result.size())) != 1)
    {
        throw std::runtime_error("Failed to generate random bytes");
    }
#endif

    return result;
}

auto crypter::encrypt_data(std::span<const std::uint8_t> data, std::span<const std::uint8_t> password) -> secure_memory_block
{
    const auto result = m_engine.encrypt(data, password);
    return serialize_package(result);
}

auto crypter::decrypt_data(std::span<const std::uint8_t> encrypted_package, std::span<const std::uint8_t> password) -> secure_memory_block
{
    const auto result = deserialize_package(encrypted_package);
    const auto decryption_result = m_engine.decrypt(result.ciphertext.span(), result.authentication_tag.span(),
                                                     result.initialization_vector.span(), result.salt.span(), password);
    return decryption_result.plaintext;
}

auto crypter::serialize_package(const aes_256_gcm_engine::encryption_result& result) -> secure_memory_block
{
    package_header header;
    header.magic = format_magic;
    header.version = format_version;
    header.reserved = 0;
    header.iv_size = result.initialization_vector.size();
    header.tag_size = result.authentication_tag.size();
    header.salt_size = result.salt.size();
    header.ciphertext_size = result.ciphertext.size();

    const std::size_t total_size = sizeof(package_header) + result.initialization_vector.size() +
                                   result.authentication_tag.size() + result.salt.size() + result.ciphertext.size();

    secure_memory_block package(total_size);
    std::uint8_t* ptr = package.data();

    std::memcpy(ptr, &header, sizeof(package_header));
    ptr += sizeof(package_header);

    std::memcpy(ptr, result.initialization_vector.data(), result.initialization_vector.size());
    ptr += result.initialization_vector.size();

    std::memcpy(ptr, result.authentication_tag.data(), result.authentication_tag.size());
    ptr += result.authentication_tag.size();

    std::memcpy(ptr, result.salt.data(), result.salt.size());
    ptr += result.salt.size();

    std::memcpy(ptr, result.ciphertext.data(), result.ciphertext.size());

    return package;
}

auto crypter::deserialize_package(std::span<const std::uint8_t> package) -> aes_256_gcm_engine::encryption_result
{
    if (package.size() < sizeof(package_header))
    {
        throw std::invalid_argument("Package too small to contain header");
    }

    const package_header* header = reinterpret_cast<const package_header*>(package.data());

    if (header->magic != format_magic)
    {
        throw std::invalid_argument("Invalid package magic number");
    }

    if (header->version != format_version)
    {
        throw std::invalid_argument("Unsupported package version");
    }

    const std::size_t expected_size = sizeof(package_header) + header->iv_size + header->tag_size + header->salt_size + header->ciphertext_size;

    if (package.size() < expected_size)
    {
        throw std::invalid_argument("Package truncated");
    }

    aes_256_gcm_engine::encryption_result result;

    const std::uint8_t* ptr = package.data() + sizeof(package_header);

    result.initialization_vector = secure_memory_block(ptr, header->iv_size);
    ptr += header->iv_size;

    result.authentication_tag = secure_memory_block(ptr, header->tag_size);
    ptr += header->tag_size;

    result.salt = secure_memory_block(ptr, header->salt_size);
    ptr += header->salt_size;

    result.ciphertext = secure_memory_block(ptr, header->ciphertext_size);

    return result;
}

} // namespace hyper_crypt
