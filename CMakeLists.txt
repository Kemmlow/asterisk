cmake_minimum_required(VERSION 3.20)
project(hyper_crypt VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Ninja generator check
if(NOT CMAKE_GENERATOR STREQUAL "Ninja")
    message(WARNING "This project is configured to build with Ninja generator for optimal performance")
endif()

# Compiler flags
if(MSVC)
    add_compile_options(/W4 /WX /permissive- /Zc:__cplusplus /Zc:inline /Zc:preprocessor)
    add_link_options(/OPT:REF /OPT:ICF)
else()
    add_compile_options(-Wall -Wextra -Werror -Wpedantic -Wshadow -Wconversion -Wsign-conversion -Wnull-dereference -Wdouble-promotion -Wformat=2)
    add_link_options(-Wl,--as-needed -Wl,--gc-sections)
endif()

# Platform-specific definitions
if(WIN32)
    add_compile_definitions(NOMINMAX _WIN32_WINNT=0x0A00)
    add_link_options(-lbcrypt)
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(OPENSSL REQUIRED openssl)
    add_compile_definitions(_GNU_SOURCE)
endif()

# Library target
add_library(hyper_crypt_lib STATIC
    src/crypter.cpp
    src/crypter.hpp
)

target_include_directories(hyper_crypt_lib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(hyper_crypt_lib PUBLIC cxx_std_20)

if(WIN32)
    target_link_libraries(hyper_crypt_lib PUBLIC bcrypt)
else()
    target_link_libraries(hyper_crypt_lib PUBLIC OpenSSL::Crypto)
    target_include_directories(hyper_crypt_lib PUBLIC ${OPENSSL_INCLUDE_DIRS})
endif()

# Example executable
add_executable(crypter_example
    examples/main.cpp
)

target_link_libraries(crypter_example PRIVATE hyper_crypt_lib)

# Tests
enable_testing()

add_executable(crypter_tests
    tests/test_crypter.cpp
)

target_link_libraries(crypter_tests PRIVATE hyper_crypt_lib)

add_test(NAME crypter_unit_tests COMMAND crypter_tests)

# Installation rules
install(TARGETS hyper_crypt_lib
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

install(FILES src/crypter.hpp
    DESTINATION include/hyper_crypt
)

# Package configuration
include(CPack)
set(CPACK_PACKAGE_NAME "hyper_crypt")
set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Production-grade cryptographic library")
set(CPACK_PACKAGE_VENDOR "HyperCrypt Inc.")
set(CPACK_PACKAGE_CONTACT "security@hypercrypt.example")
include(CPack)
