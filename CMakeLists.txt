cmake_minimum_required(VERSION 3.20)
project(crypter LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
set(CMAKE_C_FLAGS_RELEASE "-O3 -DNDEBUG")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++20 -Wall -Wextra -Werror -Wno-unused-parameter")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Werror")

find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)

option(USE_BUNDLED_ARGON2 "Use bundled argon2 implementation" OFF)

if(USE_BUNDLED_ARGON2)
    add_subdirectory(external/argon2)
    set(ARGON2_LIB argon2)
else()
    find_library(ARGON2_LIBRARY argon2)
    if(ARGON2_LIBRARY)
        set(ARGON2_LIB ${ARGON2_LIBRARY})
    else()
        message(STATUS "Argon2 library not found, using bundled")
        set(USE_BUNDLED_ARGON2 ON)
        add_subdirectory(external/argon2)
        set(ARGON2_LIB argon2)
    endif()
endif()

include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(crypter STATIC
    src/crypter.cpp
    src/aes256gcm_crypter.cpp
    src/chacha20poly1305_crypter.cpp
    src/cascade_crypter.cpp
    src/key_derivation.cpp
    src/secure_memory.cpp
    src/utilities.cpp
)

target_link_libraries(crypter PUBLIC OpenSSL::SSL OpenSSL::Crypto Threads::Threads ${ARGON2_LIB})

add_executable(crypter_demo src/demo.cpp)
target_link_libraries(crypter_demo PRIVATE crypter)
