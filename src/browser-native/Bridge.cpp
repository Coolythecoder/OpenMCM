// OpenMCM browser bridge, GPL-3.0. Based on the five-function profile bridge
// in MCM Menu Redone 2.3.0 by SpawneR27. No registry or gameplay hooks.
#include <SKSE/Impl/PCH.h>
#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include "ProfileStore.h"

namespace {
using namespace OpenMCMBrowser;
std::shared_ptr<ProfileStore> profile;

bool Supported(REL::Version version) {
    return version == SKSE::RUNTIME_SSE_1_5_97 || version == SKSE::RUNTIME_SSE_1_6_640 ||
        version == SKSE::RUNTIME_SSE_1_6_1170 || version == SKSE::RUNTIME_SSE_1_7_104;
}
enum class Operation { Begin, Append, Commit, Count, Chunk, HasState };
class Handler final : public RE::GFxFunctionHandler {
public:
    Handler(std::shared_ptr<ProfileStore> store, std::shared_ptr<ProfileTransfer> transfer, Operation operation) :
        store_(std::move(store)), transfer_(std::move(transfer)), operation_(operation) {}
    void Call(Params& params) override {
        if (!params.retVal) return;
        try {
            switch (operation_) {
            case Operation::Begin:
                params.retVal->SetBoolean(transfer_->Begin());
                break;
            case Operation::Append:
                params.retVal->SetBoolean(params.argCount == 1 && params.args && params.args[0].IsString() &&
                    transfer_->Append(params.args[0].GetString()));
                break;
            case Operation::Commit:
                params.retVal->SetBoolean(transfer_->Commit());
                break;
            case Operation::Count:
                params.retVal->SetNumber(static_cast<double>(transfer_->SnapshotChunkCount()));
                break;
            case Operation::Chunk: {
                const auto chunk = params.argCount == 1 && params.args && params.args[0].IsNumber() ?
                    transfer_->Chunk(params.args[0].GetNumber()) : std::string{};
                // Movie-owned string: never return a pointer into a destroyed temporary.
                if (params.movie) params.movie->CreateString(params.retVal, chunk.c_str());
                else params.retVal->SetString("");
                break;
            }
            case Operation::HasState:
                params.retVal->SetBoolean(store_->HasState());
                break;
            }
        } catch (const std::exception&) {
            // Exceptions may not cross the Scaleform/engine callback ABI.
            params.retVal->SetBoolean(false);
        }
    }
private:
    std::shared_ptr<ProfileStore> store_;
    std::shared_ptr<ProfileTransfer> transfer_;
    Operation operation_;
};

bool Register(RE::GFxMovieView* movie, RE::GFxValue* root) {
    if (!movie || !root || !profile) return false;
    try {
        auto transfer = std::make_shared<ProfileTransfer>(*profile);
        constexpr std::pair<const char*, Operation> functions[] = {
            { "BeginProfileStateUpdate", Operation::Begin },
            { "AppendProfileStateChunk", Operation::Append },
            { "CommitProfileStateUpdate", Operation::Commit },
            { "GetProfileStateChunkCount", Operation::Count },
            { "GetProfileStateChunk", Operation::Chunk },
            { "HasProfileState", Operation::HasState }
        };
        for (const auto& [name, operation] : functions) {
            RE::GFxValue function;
            auto* handler = new Handler(profile, transfer, operation);
            movie->CreateFunction(&function, handler);
            handler->Release(); // Movie owns its reference; no permanent handler leak.
            if (!root->SetMember(name, function)) return false;
        }
        return true;
    } catch (const std::exception&) {
        return false;
    }
}
}

extern "C" __declspec(dllexport) constinit SKSE::PluginVersionData SKSEPlugin_Version = [] {
    SKSE::PluginVersionData data;
    data.PluginVersion(REL::Version(OPENMCM_BROWSER_MAJOR, OPENMCM_BROWSER_MINOR, OPENMCM_BROWSER_PATCH, 0));
    data.PluginName("OpenMCMBrowser");
    data.AuthorName("OpenMCM; profile codec/store derived from SpawneR27");
    // Explicit allowlist: source support is not an in-game validation claim.
    data.CompatibleVersions({ SKSE::RUNTIME_SSE_1_5_97, SKSE::RUNTIME_SSE_1_6_640,
        SKSE::RUNTIME_SSE_1_6_1170, SKSE::RUNTIME_SSE_1_7_104 });
    data.UsesUpdatedStructs();
    return data;
}();

extern "C" __declspec(dllexport) bool SKSEPlugin_Query(const SKSE::QueryInterface* skse, SKSE::PluginInfo* info) {
    if (!skse || !info) return false;
    info->infoVersion = SKSE::PluginInfo::kVersion;
    info->name = "OpenMCMBrowser";
    info->version = SKSEPlugin_Version.pluginVersion;
    return !skse->IsEditor() && Supported(skse->RuntimeVersion());
}

extern "C" __declspec(dllexport) bool SKSEPlugin_Load(const SKSE::LoadInterface* skse) {
    if (!skse || skse->IsEditor() || !Supported(skse->RuntimeVersion())) return false;
    try {
        SKSE::Init(skse, SKSE::InitInfo{ .logName = "OpenMCMBrowser.log" });
        const auto directory = SKSE::log::log_directory();
        if (!directory) return false;
        profile = std::make_shared<ProfileStore>(*directory / "OpenMCM" / "Browser" / "Default.omcmb");
        profile->Load(); // Absent/corrupt file preserves per-save UI fallback.
        const auto* scaleform = SKSE::GetScaleformInterface();
        if (!scaleform || !scaleform->Register(Register, "OpenMCMBrowser")) return false;
        SKSE::log::info("OpenMCMBrowser {} loaded: profile persistence only; no registry/gameplay hooks", OPENMCM_BROWSER_VERSION);
        return true;
    } catch (const std::exception&) {
        return false;
    }
}
