// Derived from MCM Menu Redone 2.3.0 by SpawneR27. GPL-3.0.
#include "ProfileCodec.h"

#include <cstdlib>
#include <iostream>
#include <sstream>

namespace
{
    void Require(bool a_condition, const char* a_message)
    {
        if (!a_condition) {
            std::cerr << "FAILED: " << a_message << '\n';
            std::exit(1);
        }
    }
}

int main()
{
    using namespace OpenMCMBrowser::ProfileCodec;

    const std::string unicode = "Fran\xC3\xA7" "ais / \xE6\x97\xA5\xE6\x9C\xAC\xE8\xAA\x9E";
    Require(EncodeHex(unicode) == "4672616EC3A7616973202F20E697A5E69CACE8AA9E", "UTF-8 hex encoding");
    std::string decoded;
    Require(DecodeHex(EncodeHex(unicode), decoded) && decoded == unicode, "UTF-8 hex round trip");
    Require(!DecodeHex("ABC", decoded), "odd hexadecimal length rejected");
    Require(!DecodeHex("GG", decoded), "invalid hexadecimal digit rejected");

    ProfileData original{ "MCMR1|1|0|0|0|0|0|0|0|0|0", { "SkyUI", unicode } };
    std::stringstream encoded;
    Require(Write(encoded, original), "write valid profile");
    ProfileData parsed;
    std::string error;
    Require(Read(encoded, parsed, error), "read written profile");
    Require(parsed.browserState == original.browserState, "state round trip");
    Require(parsed.favorites == original.favorites, "favorites round trip");

    std::stringstream legacy("OPENMCM_BROWSER_PROFILE_V1\r\nSTATE\t\r\nFAVORITE\t536B795549\r\n");
    Require(Read(legacy, parsed, error), "CRLF legacy profile");
    Require(parsed.browserState.empty() && parsed.favorites == std::vector<std::string>{ "SkyUI" }, "legacy values");

    std::stringstream malformed("OPENMCM_BROWSER_PROFILE_V1\nSTATE\t4D43\nSTATE\t4D43\n");
    Require(!Read(malformed, parsed, error), "duplicate state rejected");
    std::stringstream badHeader("MCMR_PROFILE_V2\nSTATE\t\n");
    Require(!Read(badHeader, parsed, error), "unknown profile version rejected");

    ProfileData large{ std::string(25000, 'x'), {} };
    std::stringstream largeEncoded;
    Require(Write(largeEncoded, large), "large state write");
    Require(Read(largeEncoded, parsed, error) && parsed.browserState == large.browserState, "large state round trip");

    std::cout << "ProfileCodecTests: PASS\n";
    return 0;
}
