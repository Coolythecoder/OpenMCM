// OpenMCM browser persistence regression tests. GPL-3.0.
#include "ProfileStore.h"
#include <atomic>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <thread>
#include <vector>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

namespace {
std::size_t checks = 0;
const std::string prefix = "OPENMCMB1|0|0|0|0|0|0|0|0|0|0";
std::string State(std::string_view value) { return prefix + "|F|" + std::string(value); }
void Require(bool condition, const char* message) {
    ++checks;
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        std::exit(1);
    }
}
}
int main() {
    using namespace OpenMCMBrowser;
    const auto directory = std::filesystem::temp_directory_path() /
        ("openmcm-browser-tests-" + std::to_string(GetCurrentProcessId()) + "-" + std::to_string(GetTickCount64()));
    std::filesystem::create_directory(directory);
    const auto path = directory / "Default.omcmb";
    ProfileStore store(path);
    Require(!store.Load() && !store.HasState(), "absent file permits UI fallback");
    Require(store.SetBrowserState(State("A%20name")) && store.HasState(), "first durable profile");
    ProfileStore reloaded(path);
    Require(reloaded.Load() && reloaded.BrowserState() == store.BrowserState(), "profile restart roundtrip");
    Require(!store.SetBrowserState(""), "empty profile cannot overwrite durable preferences");
    Require(store.SetBrowserState(prefix) && store.HasState(), "valid empty preferences profile supported");
    Require(store.SetBrowserState(State("prior")), "prepare durable state");
    Require(!store.SetBrowserState(std::string(ProfileCodec::kMaximumStateLength + 1, 'x')), "reject oversized state");
    Require(!store.SetBrowserState(std::string("x\0y", 3)), "reject embedded null");
    Require(store.BrowserState() == State("prior"), "invalid input preserves committed state");
    for (const auto& bad : {"OPENMCMB1|0", "OPENMCMB1|9|0|0|0|0|0|0|0|0|0", "OPENMCMB1|0|0|0|0|0|0|0|0|0|0|F|", "OPENMCMB1|0|0|0|0|0|0|0|0|0|0|Z|name", "OPENMCMB1|0|0|0|0|0|0|0|0|0|0|N|name|%uZZZZ"})
        Require(!store.SetBrowserState(bad) && store.BrowserState() == State("prior"), "malformed envelope rejected transactionally");
    Require(store.SetBrowserState(prefix + "|F|Fran%E7ais|N|%u65E5%u672C|%u65E5%u672C"), "AS2 Unicode escapes accepted");
    ProfileTransfer a(store), b(store);
    Require(!a.Append("x") && !a.Commit(), "chunk/commit without begin rejected");
    Require(a.Begin() && a.Append(State("first")), "start transfer A");
    Require(b.Begin() && b.Append(State("second")), "start independent transfer B");
    Require(a.Commit() && store.BrowserState() == State("first"), "A commits only A chunks");
    Require(b.Commit() && store.BrowserState() == State("second"), "B commits only B chunks");
    Require(!b.Commit(), "duplicate commit rejected");
    Require(a.Begin() && a.Append("discarded") && a.Begin() && a.Append(State("replacement")) && a.Commit(), "begin replaces incomplete transfer");
    Require(store.BrowserState() == State("replacement"), "discarded transfer not appended");
    Require(a.Begin() && !a.Append(std::string(ProfileTransfer::kChunkSize + 1, 'x')) && !a.Commit(), "oversized chunk aborts transaction");
    Require(store.BrowserState() == State("replacement"), "aborted transaction preserves committed state");
    const auto large = prefix + "|F|" + std::string(900, 'x') + "|F|" + std::string(900, 'y') + "|F|" + std::string(700, 'z');
    Require(store.SetBrowserState(large) && a.SnapshotChunkCount() == 3, "snapshot chunks rounded up");
    Require(a.Chunk(0).size() == 1024 && a.Chunk(1).size() == 1024 && a.Chunk(2).size() == large.size() - 2048, "exact snapshot sizes");
    Require(store.SetBrowserState(State("changed")) && a.Chunk(2).size() == large.size() - 2048, "read snapshot unaffected by concurrent write");
    Require(a.Chunk(-1).empty() && a.Chunk(3).empty() && a.Chunk(0.5).empty(), "invalid/overflow indexes rejected");
    Require(a.Chunk(std::numeric_limits<double>::quiet_NaN()).empty() &&
        a.Chunk(std::numeric_limits<double>::infinity()).empty() &&
        a.Chunk(std::numeric_limits<double>::max()).empty(), "nonfinite and enormous indexes rejected");
    Require(a.SnapshotChunkCount() == 1 && a.Chunk(0) == State("changed"), "refresh snapshot explicit");
    Require(a.Begin(), "begin maximum-size update");
    bool bounded = true;
    const std::string chunk(ProfileTransfer::kChunkSize, 'x');
    for (std::size_t i = 0; i < ProfileCodec::kMaximumStateLength / chunk.size(); ++i) bounded &= a.Append(chunk);
    Require(bounded && !a.Append("overflow") && !a.Commit(), "total-size bound aborts update");
    Require(store.BrowserState() == State("changed"), "size-overflow preserves durable state");

    // Windows denies atomic replacement when another handle omits delete sharing.
    const auto handle = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    Require(handle != INVALID_HANDLE_VALUE, "open protected destination");
    Require(!store.SetBrowserState(State("must-not-commit")), "replacement failure returned to UI");
    Require(store.BrowserState() == State("changed"), "failed write rolls back in-memory state");
    CloseHandle(handle);
    ProfileStore afterFailure(path);
    Require(afterFailure.Load() && afterFailure.BrowserState() == State("changed"), "failed replacement preserves disk state");

    const auto corruptPath = directory / "corrupt.omcmb";
    { std::ofstream output(corruptPath); output << "MCMR_PROFILE_V1\nSTATE\t4142\n"; }
    ProfileStore corrupt(corruptPath);
    Require(!corrupt.Load() && !corrupt.HasState(), "foreign Redone profile not implicitly imported");
    Require(corrupt.SetBrowserState(State("fixed")), "explicit customization replaces after backing up");
    auto backup = corruptPath; backup += ".corrupt.bak";
    Require(std::filesystem::exists(backup), "corrupt original retained");
    { std::ifstream input(backup); std::string header; std::getline(input, header);
      Require(header == "MCMR_PROFILE_V1", "backup keeps original bytes"); }

    const auto lockedCorruptPath = directory / "locked-corrupt.omcmb";
    { std::ofstream output(lockedCorruptPath); output << "corrupt original"; }
    ProfileStore lockedCorrupt(lockedCorruptPath);
    Require(!lockedCorrupt.Load(), "recognize corrupt profile before backup failure");
    const auto corruptHandle = CreateFileW(lockedCorruptPath.c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    Require(corruptHandle != INVALID_HANDLE_VALUE, "lock corrupt original against backup");
    Require(!lockedCorrupt.SetBrowserState(State("unsafe-overwrite")) && !lockedCorrupt.HasState(), "backup failure blocks destructive replacement");
    CloseHandle(corruptHandle);
    { std::ifstream input(lockedCorruptPath); std::string original; std::getline(input, original);
      Require(original == "corrupt original", "failed backup preserves original"); }

    std::atomic<bool> coherent{true};
    std::vector<std::thread> threads;
    for (int thread = 0; thread < 4; ++thread) {
        threads.emplace_back([&, thread] {
            ProfileTransfer transfer(store);
            for (int i = 0; i < 20; ++i) {
                const auto value = State("thread" + std::to_string(thread) + "-" + std::to_string(i));
                if (!transfer.Begin() || !transfer.Append(value) || !transfer.Commit()) coherent = false;
                if (transfer.SnapshotChunkCount() != 1 || transfer.Chunk(0).find("|F|thread") == std::string::npos) coherent = false;
            }
        });
    }
    for (auto& thread : threads) thread.join();
    Require(coherent, "concurrent commits and snapshot reads remain coherent");
    ProfileStore concurrentReload(path);
    Require(concurrentReload.Load() && concurrentReload.BrowserState() == store.BrowserState(), "last concurrent commit durable");

    // Only generated files in this uniquely created test directory are removed.
    for (const auto& entry : std::filesystem::directory_iterator(directory)) {
        if (entry.is_regular_file()) std::filesystem::remove(entry.path());
    }
    std::filesystem::remove(directory);
    std::cout << "BrowserNativeTests: " << checks << " checks PASS\n";
}
