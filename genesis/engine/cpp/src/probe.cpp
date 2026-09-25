#include "md_native.hpp"
#include <iostream>

int main() {
    const auto normalized = md_native::normalize_ascii_identifier("genesis-native");
    std::cout
        << R"({"schema_version":1,"operation":"native_probe","status":"ok","normalized":")"
        << normalized
        << R"("})"
        << std::endl;
}
