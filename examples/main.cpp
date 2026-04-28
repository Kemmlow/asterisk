#include "crypter.hpp"

#include <iostream>
#include <string>
#include <vector>

int main()
{
    try
    {
        hyper_crypt::crypter crypto_engine;

        const std::string message = "This is a highly sensitive message requiring maximum security protection.";
        const std::string password = "SuperSecurePassword123!";

        std::vector<std::uint8_t> message_data(message.begin(), message.end());
        std::vector<std::uint8_t> password_data(password.begin(), password.end());

        std::cout << "Original message: " << message << std::endl;
        std::cout << "Message size: " << message_data.size() << " bytes" << std::endl;

        const auto encrypted_package = crypto_engine.encrypt_data(message_data, password_data);
        std::cout << "Encrypted package size: " << encrypted_package.size() << " bytes" << std::endl;

        const auto decrypted_data = crypto_engine.decrypt_data(encrypted_package.span(), password_data);
        std::string decrypted_message(decrypted_data.span().begin(), decrypted_data.span().end());

        std::cout << "Decrypted message: " << decrypted_message << std::endl;

        if (message == decrypted_message)
        {
            std::cout << "SUCCESS: Encryption and decryption completed successfully!" << std::endl;
            return 0;
        }
        else
        {
            std::cerr << "ERROR: Decrypted message does not match original!" << std::endl;
            return 1;
        }
    }
    catch (const std::exception& ex)
    {
        std::cerr << "ERROR: " << ex.what() << std::endl;
        return 1;
    }
}
