#pragma once

#include <cstddef>
#include <memory>
#include <vector>

namespace crypter {

class SecureMemory {
public:
    explicit SecureMemory(std::size_t size);
    ~SecureMemory();

    SecureMemory(const SecureMemory&) = delete;
    SecureMemory& operator=(const SecureMemory&) = delete;
    SecureMemory(SecureMemory&&) noexcept;
    SecureMemory& operator=(SecureMemory&&) noexcept;

    [[nodiscard]] std::uint8_t* data() noexcept { return data_; }
    [[nodiscard]] const std::uint8_t* data() const noexcept { return data_; }
    [[nodiscard]] std::size_t size() const noexcept { return size_; }

    void zeroize() noexcept;

private:
    std::uint8_t* data_ = nullptr;
    std::size_t size_ = 0;
    bool locked_ = false;
};

using SecureMemoryPtr = std::unique_ptr<SecureMemory>;

SecureMemoryPtr make_secure_memory(std::size_t size);

} // namespace crypter
