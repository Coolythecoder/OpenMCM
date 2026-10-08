// Derived from MCM Menu Redone 2.3.0 ProfileStore by SpawneR27. GPL-3.0.
// OpenMCM modifications: isolated path, fail-closed bounded loading, recoverable
// atomic replacement, commit rollback and per-movie transfers. No game objects.
#include "ProfileStore.h"
#include <cmath>
#include <charconv>
#include <cctype>
#include <algorithm>
#include <fstream>
#include <limits>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

namespace OpenMCMBrowser {
namespace {
bool ValidState(std::string_view state) {
    if (!state.starts_with("OPENMCMB1|") || state.size() > ProfileCodec::kMaximumStateLength ||
        !std::ranges::all_of(state, [](unsigned char ch) { return ch >= 32 && ch < 127; })) return false;
    std::vector<std::string_view> parts;
    while (true) {
        const auto separator = state.find('|');
        parts.push_back(state.substr(0, separator));
        if (separator == std::string_view::npos) break;
        state.remove_prefix(separator + 1);
    }
    const auto number = [](std::string_view text, unsigned maximum) {
        unsigned value = 0;
        const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
        return !text.empty() && error == std::errc{} && end == text.data() + text.size() && value <= maximum;
    };
    const auto text = [](std::string_view encoded, std::size_t maximum) {
        std::size_t decodedLength = 0;
        for (std::size_t i = 0; i < encoded.size(); ++i) {
            if (++decodedLength > maximum) return false;
            if (encoded[i] != '%') continue;
            const bool unicode = i + 1 < encoded.size() && encoded[i + 1] == 'u';
            const auto digits = unicode ? 4U : 2U;
            i += unicode ? 2 : 1;
            if (i + digits > encoded.size()) return false;
            for (unsigned j = 0; j < digits; ++j)
                if (!std::isxdigit(static_cast<unsigned char>(encoded[i + j]))) return false;
            i += digits - 1;
        }
        return true;
    };
    if (parts.size() < 11) return false;
    for (std::size_t i = 1; i <= 10; ++i)
        if (!number(parts[i], i <= 4 ? 2 : i <= 7 ? 1000000 : 1)) return false;
    std::size_t records = 0;
    for (std::size_t i = 11; i < parts.size();) {
        const auto kind = parts[i++];
        if (++records > 4096 || i >= parts.size() || parts[i].empty() || !text(parts[i++], 1024)) return false;
        if (kind == "F" || kind == "H") continue;
        if (i >= parts.size()) return false;
        if (kind == "N") { if (!text(parts[i++], 60)) return false; }
        else if (kind == "P") { if (!number(parts[i++], 999)) return false; }
        else return false;
    }
    return true;
}
}
bool ProfileStore::Load() {
    std::lock_guard lock(mutex_);
    std::error_code error;
    const auto size = std::filesystem::file_size(path_, error);
    if (error) {
        error_ = error.message();
        return false;
    }
    constexpr auto maximumFileSize = ProfileCodec::kMaximumStateLength * 2 +
        ProfileCodec::kMaximumEntries * (ProfileCodec::kMaximumNameLength * 2 + 12) + 64;
    if (size > maximumFileSize) {
        corrupt_ = true;
        error_ = "Profile exceeds the bounded file size";
        return false;
    }
    std::ifstream input(path_, std::ios::binary);
    ProfileCodec::ProfileData parsed;
    if (!input || !ProfileCodec::Read(input, parsed, error_) || !ValidState(parsed.browserState)) {
        corrupt_ = true;
        return false;
    }
    data_ = std::move(parsed);
    hasState_ = true;
    corrupt_ = false;
    return true;
}
bool ProfileStore::HasState() const {
    std::lock_guard lock(mutex_);
    return hasState_;
}
std::string ProfileStore::BrowserState() const {
    std::lock_guard lock(mutex_);
    return data_.browserState;
}
std::string ProfileStore::Error() const {
    std::lock_guard lock(mutex_);
    return error_;
}
bool ProfileStore::SetBrowserState(std::string_view state) {
    if (!ValidState(state)) {
        return false;
    }
    std::lock_guard lock(mutex_);
    if (hasState_ && data_.browserState == state) {
        return true;
    }
    auto next = data_;
    next.browserState = state;
    if (!Save(next)) {
        return false; // In-memory state remains the last durable commit.
    }
    data_ = std::move(next);
    hasState_ = true;
    error_.clear();
    return true;
}
bool ProfileStore::PreserveCorruptProfile() {
    if (!corrupt_) return true;
    std::error_code error;
    auto backup = path_;
    backup += ".corrupt.bak";
    for (std::uint32_t index = 1; std::filesystem::exists(backup, error) && !error; ++index) {
        if (index > 1000) {
            error_ = "Too many corrupt profile backups";
            return false;
        }
        backup = path_;
        backup += ".corrupt." + std::to_string(index) + ".bak";
    }
    if (error || !std::filesystem::copy_file(path_, backup, std::filesystem::copy_options::none, error)) {
        error_ = "Cannot preserve corrupt profile: " + error.message();
        return false; // Never overwrite a corrupt original if backup fails.
    }
    corrupt_ = false;
    return true;
}
bool ProfileStore::Save(const ProfileCodec::ProfileData& next) {
    std::error_code error;
    std::filesystem::create_directories(path_.parent_path(), error);
    if (error) {
        error_ = "Cannot create browser profile directory: " + error.message();
        return false;
    }
    if (!PreserveCorruptProfile()) return false;
    auto temporary = path_;
    temporary += ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output || !ProfileCodec::Write(output, next)) {
            error_ = "Cannot write temporary browser profile";
            return false;
        }
        output.flush();
        if (!output) {
            error_ = "Cannot flush temporary browser profile";
            return false;
        }
        output.close();
        if (!output) {
            error_ = "Cannot close temporary browser profile";
            return false;
        }
    }
    if (!MoveFileExW(temporary.c_str(), path_.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        error_ = "Cannot replace browser profile, Win32 " + std::to_string(GetLastError());
        std::filesystem::remove(temporary, error);
        return false;
    }
    return true;
}
bool ProfileTransfer::Begin() {
    std::lock_guard lock(mutex_);
    pending_.clear();
    active_ = true;
    return true;
}
bool ProfileTransfer::Append(std::string_view chunk) {
    std::lock_guard lock(mutex_);
    if (!active_) return false;
    if (chunk.size() > kChunkSize || chunk.find('\0') != std::string_view::npos ||
        chunk.size() > ProfileCodec::kMaximumStateLength - pending_.size()) {
        pending_.clear();
        active_ = false;
        return false;
    }
    pending_.append(chunk);
    return true;
}
bool ProfileTransfer::Commit() {
    std::lock_guard lock(mutex_);
    if (!active_) return false;
    active_ = false;
    auto next = std::move(pending_);
    pending_.clear();
    return store_.SetBrowserState(next);
}
std::size_t ProfileTransfer::SnapshotChunkCount() {
    std::lock_guard lock(mutex_);
    snapshot_ = store_.BrowserState();
    return (snapshot_.size() + kChunkSize - 1) / kChunkSize;
}
std::string ProfileTransfer::Chunk(double index) const {
    std::lock_guard lock(mutex_);
    const auto count = (snapshot_.size() + kChunkSize - 1) / kChunkSize;
    if (!std::isfinite(index) || index < 0 || index != std::floor(index) || index >= static_cast<double>(count)) {
        return {};
    }
    return snapshot_.substr(static_cast<std::size_t>(index) * kChunkSize, kChunkSize);
}
}
