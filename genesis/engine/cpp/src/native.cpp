#include "md_native.hpp"
#include <cctype>

namespace md_native {

std::string normalize_ascii_identifier(const std::string& value) {
    std::string result;
    for (unsigned char ch : value) {
        if (std::isalnum(ch) || ch == '_' || ch == '-') {
            result += static_cast<char>(ch);
        }
    }
    return result;
}

}
