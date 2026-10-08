// Derived from MCM Menu Redone 2.3.0 by SpawneR27. GPL-3.0.
// OpenMCM modifications: independent file identity, bounded/complete parsing.
#include "ProfileCodec.h"

#include <algorithm>
#include <istream>
#include <ostream>
#include <ranges>
#include <string>
#include <unordered_set>

namespace OpenMCMBrowser::ProfileCodec
{
    namespace
    {
        [[nodiscard]] int HexValue(char a_character)
        {
            if (a_character >= '0' && a_character <= '9') {
                return a_character - '0';
            }
            if (a_character >= 'A' && a_character <= 'F') {
                return 10 + a_character - 'A';
            }
            if (a_character >= 'a' && a_character <= 'f') {
                return 10 + a_character - 'a';
            }
            return -1;
        }
    }

    std::string EncodeHex(std::string_view a_value)
    {
        constexpr char digits[] = "0123456789ABCDEF";
        std::string result;
        result.reserve(a_value.size() * 2);
        for (const auto byte : a_value) {
            const auto value = static_cast<unsigned char>(byte);
            result.push_back(digits[value >> 4]);
            result.push_back(digits[value & 0x0F]);
        }
        return result;
    }

    bool DecodeHex(std::string_view a_value, std::string& a_result)
    {
        if ((a_value.size() % 2) != 0) {
            return false;
        }
        a_result.clear();
        a_result.reserve(a_value.size() / 2);
        for (std::size_t index = 0; index < a_value.size(); index += 2) {
            const auto high = HexValue(a_value[index]);
            const auto low = HexValue(a_value[index + 1]);
            if (high < 0 || low < 0) {
                a_result.clear();
                return false;
            }
            a_result.push_back(static_cast<char>((high << 4) | low));
        }
        return true;
    }

    bool Read(std::istream& a_input, ProfileData& a_result, std::string& a_error)
    {
        ProfileData parsed;
        std::string line;
        if (!std::getline(a_input, line)) {
            a_error = "profile is empty";
            return false;
        }
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line != kHeader) {
            a_error = "invalid OPENMCM_BROWSER_PROFILE_V1 header";
            return false;
        }

        bool sawState = false;
        std::unordered_set<std::string> favorites;
        std::size_t lineNumber = 1;
        while (std::getline(a_input, line)) {
            ++lineNumber;
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            if (line.empty()) {
                continue;
            }

            const auto separator = line.find('\t');
            if (separator == std::string::npos) {
                a_error = "malformed line " + std::to_string(lineNumber);
                return false;
            }
            const auto key = std::string_view(line).substr(0, separator);
            const auto encoded = std::string_view(line).substr(separator + 1);
            // Reject excess encoded input before allocating a second copy.
            const auto maximum = key == "STATE" ? kMaximumStateLength : kMaximumNameLength;
            if (encoded.size() > maximum * 2) {
                a_error = "oversized record on line " + std::to_string(lineNumber);
                return false;
            }
            std::string decoded;
            if (!DecodeHex(encoded, decoded)) {
                a_error = "invalid hexadecimal payload on line " + std::to_string(lineNumber);
                return false;
            }

            if (key == "STATE") {
                if (sawState || decoded.size() > kMaximumStateLength) {
                    a_error = "invalid or duplicate STATE record";
                    return false;
                }
                parsed.browserState = std::move(decoded);
                sawState = true;
            } else if (key == "FAVORITE") {
                if (decoded.empty() || decoded.size() > kMaximumNameLength ||
                    parsed.favorites.size() >= kMaximumEntries) {
                    a_error = "invalid FAVORITE record";
                    return false;
                }
                if (favorites.insert(decoded).second) {
                    parsed.favorites.push_back(std::move(decoded));
                }
            } else {
                a_error = "unknown record on line " + std::to_string(lineNumber);
                return false;
            }
        }

        if (a_input.bad() || !sawState) {
            a_error = "missing STATE record or input read failure";
            return false;
        }
        a_result = std::move(parsed);
        a_error.clear();
        return true;
    }

    bool Write(std::ostream& a_output, const ProfileData& a_data)
    {
        if (a_data.browserState.size() > kMaximumStateLength ||
            a_data.favorites.size() > kMaximumEntries ||
            std::ranges::any_of(a_data.favorites, [](const std::string& a_name) {
                return a_name.empty() || a_name.size() > kMaximumNameLength;
            })) {
            return false;
        }

        a_output << kHeader << '\n';
        a_output << "STATE\t" << EncodeHex(a_data.browserState) << '\n';
        for (const auto& favorite : a_data.favorites) {
            a_output << "FAVORITE\t" << EncodeHex(favorite) << '\n';
        }
        return static_cast<bool>(a_output);
    }
}
