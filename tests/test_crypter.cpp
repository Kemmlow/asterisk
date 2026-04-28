#include "crypter.hpp"

#include <cassert>
#include <iostream>
#include <string>
#include <vector>

namespace
{

void test_basic_encryption_decryption()
{
    hyper_crypt::crypter crypto_engine;

    const std::string original = "Test message for encryption";
    const std::string password = "TestPassword123";

    std::vector<std::uint8_t> data(original.begin(), original.end());
    std::vector<std::uint8_t> pwd(password.begin(), password.end());

    const auto encrypted = crypto_engine.encrypt_data(data, pwd);
    const auto decrypted = crypto_engine.decrypt_data(encrypted.span(), pwd);

    std::string result(decrypted.span().begin(), decrypted.span().end());

    assert(original == result && "Basic encryption/decryption failed");
    std::cout << "PASS: Basic encryption/decryption test" << std::endl;
}

void test_empty_password_rejection()
{
    hyper_crypt::crypter crypto_engine;

    std::vector<std::uint8_t> data = {1, 2, 3, 4, 5};
    std::vector<std::uint8_t> short_pwd = {1, 2, 3, 4, 5, 6, 7}; // 7 bytes < 8

    try
    {
        crypto_engine.encrypt_data(data, short_pwd);
        assert(false && "Should have thrown exception for short password");
    }
    catch (const std::invalid_argument&)
    {
        std::cout << "PASS: Short password rejection test" << std::endl;
    }
}

void test_empty_data_rejection()
{
    hyper_crypt::crypter crypto_engine;

    std::vector<std::uint8_t> empty_data;
    std::vector<std::uint8_t> password = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};

    try
    {
        crypto_engine.encrypt_data(empty_data, password);
        assert(false && "Should have thrown exception for empty data");
    }
    catch (const std::invalid_argument&)
    {
        std::cout << "PASS: Empty data rejection test" << std::endl;
    }
}

void test_different_passwords_fail()
{
    hyper_crypt::crypter crypto_engine;

    const std::string original = "Secret message";
    const std::string password1 = "PasswordOne123";
    const std::string password2 = "PasswordTwo456";

    std::vector<std::uint8_t> data(original.begin(), original.end());
    std::vector<std::uint8_t> pwd1(password1.begin(), password1.end());
    std::vector<std::uint8_t> pwd2(password2.begin(), password2.end());

    const auto encrypted = crypto_engine.encrypt_data(data, pwd1);

    try
    {
        crypto_engine.decrypt_data(encrypted.span(), pwd2);
        assert(false && "Should have thrown exception for wrong password");
    }
    catch (const std::runtime_error&)
    {
        std::cout << "PASS: Wrong password rejection test" << std::endl;
    }
}

void test_large_data()
{
    hyper_crypt::crypter crypto_engine;

    std::vector<std::uint8_t> large_data(1024 * 1024); // 1MB
    for (std::size_t i = 0; i < large_data.size(); ++i)
    {
        large_data[i] = static_cast<std::uint8_t>(i % 256);
    }

    std::vector<std::uint8_t> password = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};

    const auto encrypted = crypto_engine.encrypt_data(large_data, password);
    const auto decrypted = crypto_engine.decrypt_data(encrypted.span(), password);

    assert(large_data == std::vector<std::uint8_t>(decrypted.span().begin(), decrypted.span().end()) &&
           "Large data encryption/decryption failed");
    std::cout << "PASS: Large data encryption/decryption test" << std::endl;
}

void test_binary_data()
{
    hyper_crypt::crypter crypto_engine;

    std::vector<std::uint8_t> binary_data = {0x00, 0xFF, 0x00, 0xFF, 0xAA, 0x55, 0xAA, 0x55, 0x00, 0x00, 0xFF, 0xFF};
    std::vector<std::uint8_t> password = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};

    const auto encrypted = crypto_engine.encrypt_data(binary_data, password);
    const auto decrypted = crypto_engine.decrypt_data(encrypted.span(), password);

    assert(binary_data == std::vector<std::uint8_t>(decrypted.span().begin(), decrypted.span().end()) &&
           "Binary data encryption/decryption failed");
    std::cout << "PASS: Binary data encryption/decryption test" << std::endl;
}

} // namespace

int main()
{
    try
    {
        test_basic_encryption_decryption();
        test_empty_password_rejection();
        test_empty_data_rejection();
        test_different_passwords_fail();
        test_large_data();
        test_binary_data();

        std::cout << "\nAll tests passed successfully!" << std::endl;
        return 0;
    }
    catch (const std::exception& ex)
    {
        std::cerr << "Test failed with exception: " << ex.what() << std::endl;
        return 1;
    }
}
