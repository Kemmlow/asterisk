#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace hyper_crypt
{

class secure_memory_block final
{
public:
    explicit secure_memory_block(std::size_t size);
    secure_memory_block(const void* data, std::size_t size);
    secure_memory_block(const secure_memory_block&) = delete;
    secure_memory_block(secure_memory_block&& other) noexcept;
    auto operator=(const secure_memory_block&) -> secure_memory_block& = delete;
    auto operator=(secure_memory_block&& other) noexcept -> secure_memory_block&;
    ~secure_memory_block();

    [[nodiscard]] auto data() noexcept -> void*;
    [[nodiscard]] auto data() const noexcept -> const void*;
    [[nodiscard]] auto size() const noexcept -> std::size_t;
    [[nodiscard]] auto span() noexcept -> std::span<std::uint8_t>;
    [[nodiscard]] auto span() const noexcept -> std::span<const std::uint8_t>;

    void zeroize() noexcept;
    void resize(std::size_t new_size);

private:
    std::unique_ptr<std::uint8_t[], decltype(&secure_memory_block::secure_deallocate)> m_ptr;
    std::size_t m_size;

    static auto secure_allocate(std::size_t size) -> std::uint8_t*;
    static void secure_deallocate(std::uint8_t* ptr) noexcept;
};

class aes_256_gcm_engine final
{
public:
    static constexpr std::size_t key_size = 32;
    static constexpr std::size_t iv_size = 12;
    static constexpr std::size_t tag_size = 16;
    static constexpr std::size_t salt_size = 16;
    static constexpr std::size_t iterations = 100000;

    struct encryption_result
    {
        secure_memory_block ciphertext;
        secure_memory_block authentication_tag;
        secure_memory_block initialization_vector;
        secure_memory_block salt;
    };

    struct decryption_result
    {
        secure_memory_block plaintext;
    };

    aes_256_gcm_engine() = default;
    aes_256_gcm_engine(const aes_256_gcm_engine&) = delete;
    aes_256_gcm_engine(aes_256_gcm_engine&&) noexcept = default;
    auto operator=(const aes_256_gcm_engine&) -> aes_256_gcm_engine& = delete;
    auto operator=(aes_256_gcm_engine&&) noexcept -> aes_256_gcm_engine& = default;
    ~aes_256_gcm_engine() = default;

    [[nodiscard]] auto encrypt(std::span<const std::uint8_t> plaintext,
                               std::span<const std::uint8_t> password) -> encryption_result;

    [[nodiscard]] auto decrypt(std::span<const std::uint8_t> ciphertext,
                               std::span<const std::uint8_t> authentication_tag,
                               std::span<const std::uint8_t> initialization_vector,
                               std::span<const std::uint8_t> salt,
                               std::span<const std::uint8_t> password) -> decryption_result;

private:
    [[nodiscard]] auto derive_key(std::span<const std::uint8_t> password,
                                  std::span<const std::uint8_t> salt) const -> secure_memory_block;

    [[nodiscard]] static auto generate_random_bytes(std::size_t count) -> secure_memory_block;
};

class crypter final
{
public:
    crypter() = default;
    crypter(const crypter&) = delete;
    crypter(crypter&&) noexcept = default;
    auto operator=(const crypter&) -> crypter& = delete;
    auto operator=(crypter&&) noexcept -> crypter& = default;
    ~crypter() = default;

    [[nodiscard]] auto encrypt_data(std::span<const std::uint8_t> data,
                                    std::span<const std::uint8_t> password) -> secure_memory_block;

    [[nodiscard]] auto decrypt_data(std::span<const std::uint8_t> encrypted_package,
                                    std::span<const std::uint8_t> password) -> secure_memory_block;

private:
    aes_256_gcm_engine m_engine;

    static constexpr std::uint32_t format_magic = 0x43525950; // 'CRYP'
    static constexpr std::uint16_t format_version = 1;

    struct package_header
    {
        std::uint32_t magic;
        std::uint16_t version;
        std::uint16_t reserved;
        std::uint64_t iv_size;
        std::uint64_t tag_size;
        std::uint64_t salt_size;
        std::uint64_t ciphertext_size;
    };

    [[nodiscard]] static auto serialize_package(const aes_256_gcm_engine::encryption_result& result) -> secure_memory_block;
    [[nodiscard]] static auto deserialize_package(std::span<const std::uint8_t> package) -> aes_256_gcm_engine::encryption_result;
};

} // namespace hyper_crypt
