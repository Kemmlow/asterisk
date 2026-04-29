#include "cascade_crypter.h"
#include "crypter_types.h"
#include <sstream>
#include <cstdint>
#include <algorithm>

namespace crypter {

namespace {

void write_length_prefix(std::vector<std::uint8_t>& out, std::size_t value) {
    for (int i = 0; i < 4; ++i) {
        out.push_back(static_cast<std::uint8_t>((value >> (i * 8)) & 0xFF));
    }
}

std::expected<std::size_t, CrypterError> read_length_prefix(std::span<const std::uint8_t>& data) {
    if (data.size() < 4) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }
    std::size_t value = 0;
    for (int i = 0; i < 4; ++i) {
        value |= static_cast<std::size_t>(data[i]) << (i * 8);
    }
    data = data.subspan(4);
    return value;
}

} // namespace

CascadeCrypter::CascadeCrypter(CrypterPtr first, CrypterPtr second)
    : first_(std::move(first)), second_(std::move(second)) {
    if (!first_ || !second_) {
        throw std::invalid_argument("CascadeCrypter requires two valid crypters");
    }
}

[[nodiscard]] std::expected<AuthenticatedBlob, CrypterError> CascadeCrypter::encrypt(
    std::span<const std::uint8_t> plaintext,
    std::span<const std::uint8_t> associated_data
) {
    auto first_result = first_->encrypt(plaintext, associated_data);
    if (!first_result) {
        return std::unexpected{first_result.error()};
    }

    auto& first_blob = first_result.value();
    std::vector<std::uint8_t> combined_iv;
    write_length_prefix(combined_iv, first_blob.iv.size());
    combined_iv.insert(combined_iv.end(), first_blob.iv.begin(), first_blob.iv.end());

    std::vector<std::uint8_t> combined_tag;
    write_length_prefix(combined_tag, first_blob.tag.size());
    combined_tag.insert(combined_tag.end(), first_blob.tag.begin(), first_blob.tag.end());

    AuthenticatedBlob first_as_blob{std::move(first_blob.ciphertext), std::move(combined_iv),
        std::move(combined_tag), std::vector<std::uint8_t>(associated_data.begin(), associated_data.end())};

    auto second_result = second_->encrypt(first_as_blob.ciphertext, first_as_blob.associated_data);
    if (!second_result) {
        return std::unexpected{second_result.error()};
    }

    auto& second_blob = second_result.value();
    write_length_prefix(second_blob.iv, first_as_blob.iv.size());
    second_blob.iv.insert(second_blob.iv.end(), first_as_blob.iv.begin(), first_as_blob.iv.end());

    write_length_prefix(second_blob.tag, first_as_blob.tag.size());
    second_blob.tag.insert(second_blob.tag.end(), first_as_blob.tag.begin(), first_as_blob.tag.end());

    return AuthenticatedBlob{std::move(second_blob.ciphertext), std::move(second_blob.iv),
        std::move(second_blob.tag), std::move(second_blob.associated_data)};
}

[[nodiscard]] std::expected<std::vector<std::uint8_t>, CrypterError> CascadeCrypter::decrypt(
    const AuthenticatedBlob& blob
) {
    if (blob.iv.size() < 4 || blob.tag.size() < 4) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }

    std::span<const std::uint8_t> iv_span = blob.iv;
    auto inner_iv_len = read_length_prefix(iv_span);
    if (!inner_iv_len) {
        return std::unexpected{inner_iv_len.error()};
    }
    if (iv_span.size() < *inner_iv_len) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }
    std::vector<std::uint8_t> second_iv(iv_span.begin(), iv_span.begin() + static_cast<std::ptrdiff_t>(*inner_iv_len));
    iv_span = iv_span.subspan(*inner_iv_len);

    auto outer_iv_len = read_length_prefix(iv_span);
    if (!outer_iv_len) {
        return std::unexpected{outer_iv_len.error()};
    }
    if (iv_span.size() < *outer_iv_len) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }
    std::vector<std::uint8_t> first_iv(iv_span.begin(), iv_span.begin() + static_cast<std::ptrdiff_t>(*outer_iv_len));

    std::span<const std::uint8_t> tag_span = blob.tag;
    auto inner_tag_len = read_length_prefix(tag_span);
    if (!inner_tag_len) {
        return std::unexpected{inner_tag_len.error()};
    }
    if (tag_span.size() < *inner_tag_len) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }
    std::vector<std::uint8_t> second_tag(tag_span.begin(), tag_span.begin() + static_cast<std::ptrdiff_t>(*inner_tag_len));
    tag_span = tag_span.subspan(*inner_tag_len);

    auto outer_tag_len = read_length_prefix(tag_span);
    if (!outer_tag_len) {
        return std::unexpected{outer_tag_len.error()};
    }
    if (tag_span.size() < *outer_tag_len) {
        return std::unexpected{CrypterError::InvalidCiphertext};
    }
    std::vector<std::uint8_t> first_tag(tag_span.begin(), tag_span.begin() + static_cast<std::ptrdiff_t>(*outer_tag_len));

    AuthenticatedBlob second_blob{std::vector<std::uint8_t>(blob.ciphertext), std::move(second_iv), std::move(second_tag),
        std::vector<std::uint8_t>(blob.associated_data)};

    auto second_plain = second_->decrypt(second_blob);
    if (!second_plain) {
        return std::unexpected{second_plain.error()};
    }

    AuthenticatedBlob first_blob{std::move(second_plain.value()), std::move(first_iv), std::move(first_tag),
        std::vector<std::uint8_t>(blob.associated_data)};

    return first_->decrypt(first_blob);
}

} // namespace crypter
