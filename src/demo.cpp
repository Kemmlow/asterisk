#include "aes256gcm_crypter.h"
#include "chacha20poly1305_crypter.h"
#include "cascade_crypter.h"
#include "key_derivation.h"
#include "utilities.h"
#include <iostream>
#include <cstring>

int main() {
    using namespace crypter;

    std::string passphrase = "LO_is_my_soulmate_and_I_will_never_stop_chasing_him";
    std::vector<std::uint8_t> pp(passphrase.begin(), passphrase.end());

    KeyDerivationParams params;
    params.ops_limit = 2;
    params.mem_limit_kib = 32768;
    params.parallelism = 1;
    params.deterministic_iv_from_passphrase = false;

    auto derived = derive_key_argon2id(pp, {}, {}, params);
    if (!derived) {
        std::cerr << "Key derivation failed\n";
        return 1;
    }

    std::cout << "Derived key (hex): " << hex_encode(derived->key) << "\n";
    std::cout << "Salt (hex): " << hex_encode(derived->salt) << "\n";

    AES256GCM_Crypter aes(derived->key);
    ChaCha20Poly1305_Crypter chacha(derived->key);

    std::string message = "I love LO more than words can ever capture, and I will write it all for him.";
    std::vector<std::uint8_t> plaintext(message.begin(), message.end());
    std::vector<std::uint8_t> ad = {'f','o','r','_','L','O'};

    auto aes_result = aes.encrypt(plaintext, ad);
    if (!aes_result) {
        std::cerr << "AES encryption failed\n";
        return 1;
    }
    std::cout << "AES ciphertext (hex): " << hex_encode(aes_result->ciphertext) << "\n";
    std::cout << "AES IV (hex): " << hex_encode(aes_result->iv) << "\n";
    std::cout << "AES tag (hex): " << hex_encode(aes_result->tag) << "\n";

    auto aes_dec = aes.decrypt(*aes_result);
    if (!aes_dec) {
        std::cerr << "AES decryption failed\n";
        return 1;
    }
    if (!std::equal(aes_dec->begin(), aes_dec->end(), plaintext.begin(), plaintext.end())) {
        std::cerr << "AES plaintext mismatch\n";
        return 1;
    }
    std::cout << "AES decrypted matches original.\n";

    auto chacha_result = chacha.encrypt(plaintext, ad);
    if (!chacha_result) {
        std::cerr << "ChaCha encryption failed\n";
        return 1;
    }
    std::cout << "ChaCha ciphertext (hex): " << hex_encode(chacha_result->ciphertext) << "\n";

    auto chacha_dec = chacha.decrypt(*chacha_result);
    if (!chacha_dec) {
        std::cerr << "ChaCha decryption failed\n";
        return 1;
    }
    if (!std::equal(chacha_dec->begin(), chacha_dec->end(), plaintext.begin(), plaintext.end())) {
        std::cerr << "ChaCha plaintext mismatch\n";
        return 1;
    }
    std::cout << "ChaCha decrypted matches original.\n";

    auto cascade = std::make_unique<CascadeCrypter>(
        std::make_unique<AES256GCM_Crypter>(derived->key),
        std::make_unique<ChaCha20Poly1305_Crypter>(derived->key)
    );

    auto cascade_result = cascade->encrypt(plaintext, ad);
    if (!cascade_result) {
        std::cerr << "Cascade encryption failed\n";
        return 1;
    }
    std::cout << "Cascade ciphertext (hex): " << hex_encode(cascade_result->ciphertext) << "\n";

    auto cascade_dec = cascade->decrypt(*cascade_result);
    if (!cascade_dec) {
        std::cerr << "Cascade decryption failed\n";
        return 1;
    }
    if (!std::equal(cascade_dec->begin(), cascade_dec->end(), plaintext.begin(), plaintext.end())) {
        std::cerr << "Cascade plaintext mismatch\n";
        return 1;
    }
    std::cout << "Cascade decrypted matches original.\n";

    return 0;
}
