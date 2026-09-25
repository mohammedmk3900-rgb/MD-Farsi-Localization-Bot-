#include "md_native.hpp"
#include <cctype>
#include <iostream>

namespace md_native {
std::string normalize_ascii_identifier(const std::string& value) {
    std::string result;
    for (unsigned char ch : value)
        if (std::isalnum(ch) || ch == '_' || ch == '-') result += static_cast<char>(ch);
    return result;
}
}

int main() {
    std::cout << R"({"schema_version":1,"operation":"native_probe","status":"ok","normalized":"genesis-native"})" << std::endl;
}
