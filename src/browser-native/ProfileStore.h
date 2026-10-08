// Derived from MCM Menu Redone 2.3.0 ProfileStore by SpawneR27. GPL-3.0.
// OpenMCM: dependency-free, explicit path, transactional commits and snapshots.
#pragma once

#include "ProfileCodec.h"
#include <filesystem>
#include <mutex>
#include <string>
#include <string_view>

namespace OpenMCMBrowser {

class ProfileStore final {
public:
    explicit ProfileStore(std::filesystem::path path) : path_(std::move(path)) {}
    bool Load();
    bool HasState() const;
    std::string BrowserState() const;
    std::string Error() const;
    bool SetBrowserState(std::string_view state);
private:
    bool Save(const ProfileCodec::ProfileData& next);
    bool PreserveCorruptProfile();
    std::filesystem::path path_;
    mutable std::mutex mutex_;
    ProfileCodec::ProfileData data_;
    std::string error_;
    bool hasState_ = false;
    bool corrupt_ = false;
};

// Each movie gets its own transfer object. No movie/quest/VM pointer is retained.
// A different movie cannot interleave a partial write or change a read snapshot.
class ProfileTransfer final {
public:
    static constexpr std::size_t kChunkSize = 1024;
    explicit ProfileTransfer(ProfileStore& store) : store_(store) {}
    bool Begin();
    bool Append(std::string_view chunk);
    bool Commit();
    std::size_t SnapshotChunkCount();
    std::string Chunk(double index) const;
private:
    ProfileStore& store_;
    mutable std::mutex mutex_;
    std::string pending_;
    std::string snapshot_;
    bool active_ = false;
};
}
