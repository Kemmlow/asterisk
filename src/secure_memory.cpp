#include "secure_memory.h"
#include <cstring>

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#endif

namespace crypter {

SecureMemory::SecureMemory(std::size_t size) : size_(size) {
    if (size_ == 0) {
        return;
    }

#if defined(_WIN32) || defined(_WIN64)
    data_ = static_cast<std::uint8_t*>(VirtualAlloc(nullptr, size_, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE));
    if (!data_) {
        return;
    }
    if (!VirtualLock(data_, size_)) {
        VirtualFree(data_, 0, MEM_RELEASE);
        data_ = nullptr;
        return;
    }
    locked_ = true;
#else
    data_ = static_cast<std::uint8_t*>(mmap(nullptr, size_, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (data_ == MAP_FAILED) {
        data_ = nullptr;
        return;
    }
    if (mlock(data_, size_) != 0) {
        munmap(data_, size_);
        data_ = nullptr;
        return;
    }
    locked_ = true;
#endif
}

SecureMemory::~SecureMemory() {
    zeroize();
    if (data_) {
#if defined(_WIN32) || defined(_WIN64)
        if (locked_) {
            VirtualUnlock(data_, size_);
        }
        VirtualFree(data_, 0, MEM_RELEASE);
#else
        if (locked_) {
            munlock(data_, size_);
        }
        munmap(data_, size_);
#endif
    }
}

SecureMemory::SecureMemory(SecureMemory&& other) noexcept
    : data_(other.data_), size_(other.size_), locked_(other.locked_) {
    other.data_ = nullptr;
    other.size_ = 0;
    other.locked_ = false;
}

SecureMemory& SecureMemory::operator=(SecureMemory&& other) noexcept {
    if (this != &other) {
        zeroize();
        if (data_) {
#if defined(_WIN32) || defined(_WIN64)
            if (locked_) {
                VirtualUnlock(data_, size_);
            }
            VirtualFree(data_, 0, MEM_RELEASE);
#else
            if (locked_) {
                munlock(data_, size_);
            }
            munmap(data_, size_);
#endif
        }
        data_ = other.data_;
        size_ = other.size_;
        locked_ = other.locked_;
        other.data_ = nullptr;
        other.size_ = 0;
        other.locked_ = false;
    }
    return *this;
}

void SecureMemory::zeroize() noexcept {
    if (data_ && size_ > 0) {
#if defined(_WIN32) || defined(_WIN64)
        SecureZeroMemory(data_, size_);
#else
        explicit_bzero(data_, size_);
#endif
    }
}

SecureMemoryPtr make_secure_memory(std::size_t size) {
    return std::make_unique<SecureMemory>(size);
}

} // namespace crypter
