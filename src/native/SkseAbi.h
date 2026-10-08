#pragma once

#include <cstddef>
#include <cstdint>

// Minimal ABI declarations, independently named; no SKSE implementation is
// linked or bundled. Field order/width verified against SKSE 2.3.1 PluginAPI.h.
namespace openmcm::skse {

struct Interface {
    std::uint32_t skseVersion;
    std::uint32_t runtimeVersion;
    std::uint32_t editorVersion;
    std::uint32_t isEditor;
    void* (*queryInterface)(std::uint32_t);
    std::uint32_t (*getPluginHandle)();
    std::uint32_t (*getReleaseIndex)();
    const void* (*getPluginInfo)(const char*);
};

struct Message {
    const char* sender;
    std::uint32_t type;
    std::uint32_t dataLength;
    void* data;
};

struct Messaging {
    std::uint32_t interfaceVersion;
    bool (*registerListener)(std::uint32_t, const char*, void (*)(Message*));
    bool (*dispatch)(std::uint32_t, std::uint32_t, void*, std::uint32_t, const char*);
    void* (*getEventDispatcher)(std::uint32_t);
};

struct VersionData {
    std::uint32_t dataVersion;
    std::uint32_t pluginVersion;
    char name[256];
    char author[256];
    char supportEmail[252];
    std::uint32_t versionIndependenceEx;
    std::uint32_t versionIndependence;
    std::uint32_t compatibleVersions[16];
    std::uint32_t skseVersionRequired;
};

static_assert(sizeof(void*) == 8, "Only the x64 SKSE ABI is supported");
static_assert(sizeof(Interface) == 48 && offsetof(Interface, queryInterface) == 16);
static_assert(sizeof(Message) == 24 && offsetof(Message, data) == 16);
static_assert(sizeof(Messaging) == 32 && offsetof(Messaging, registerListener) == 8);
static_assert(sizeof(VersionData) == 0x350);
static_assert(offsetof(VersionData, versionIndependenceEx) == 0x304);
static_assert(offsetof(VersionData, compatibleVersions) == 0x30C);

inline constexpr std::uint32_t kMessagingInterface = 5;
inline constexpr std::uint32_t kPostPostLoad = 1;

} // namespace openmcm::skse
