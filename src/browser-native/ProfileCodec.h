// Derived from MCM Menu Redone 2.3.0 by SpawneR27. GPL-3.0.
// OpenMCM modification: separate namespace and file-format identity.
#pragma once

#include <cstddef>
#include <iosfwd>
#include <string>
#include <string_view>
#include <vector>

namespace OpenMCMBrowser::ProfileCodec
{
    inline constexpr std::string_view kHeader = "OPENMCM_BROWSER_PROFILE_V1";
    inline constexpr std::size_t kMaximumEntries = 4096;
    inline constexpr std::size_t kMaximumNameLength = 4096;
    inline constexpr std::size_t kMaximumStateLength = 32768;

    struct ProfileData
    {
        std::string browserState;
        std::vector<std::string> favorites;
    };

    [[nodiscard]] std::string EncodeHex(std::string_view a_value);
    [[nodiscard]] bool DecodeHex(std::string_view a_value, std::string& a_result);
    [[nodiscard]] bool Read(std::istream& a_input, ProfileData& a_result, std::string& a_error);
    [[nodiscard]] bool Write(std::ostream& a_output, const ProfileData& a_data);
}
