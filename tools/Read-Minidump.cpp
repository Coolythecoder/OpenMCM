// Offline-only dump reader using Microsoft's installed debugging engine.
// No process attach, debugger registration, game writes, or dump uploads.
#include <windows.h>
#include <dbgeng.h>
#include <cstdio>
#include <string>

class DumpOutput final : public IDebugOutputCallbacks {
    FILE* log_;
public:
    explicit DumpOutput(FILE* log) : log_(log) {}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) override {
        if (iid == __uuidof(IUnknown) || iid == __uuidof(IDebugOutputCallbacks)) {
            *out = this; return S_OK;
        }
        *out = nullptr; return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return 1; }
    ULONG STDMETHODCALLTYPE Release() override { return 1; }
    HRESULT STDMETHODCALLTYPE Output(ULONG, PCSTR text) override;
};

HRESULT STDMETHODCALLTYPE DumpOutput::Output(ULONG, PCSTR text) {
    std::fputs(text, stdout);
    if (log_) { std::fputs(text, log_); std::fflush(log_); }
    return S_OK;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "Usage: Read-Minidump dump.dmp output.txt [debugger commands]\n");
        return 2;
    }
    FILE* log = nullptr;
    if (fopen_s(&log, argv[2], "wx") || !log) {
        std::fprintf(stderr, "Cannot create new output file (refusing overwrite).\n");
        return 2;
    }
    // Use the installed SDK symbol client; the Windows inbox dbghelp does not
    // necessarily enable public symbol-server downloads.
    LoadLibraryExW(L"C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\symsrv.dll", nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
    LoadLibraryExW(L"C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\dbghelp.dll", nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
    const HMODULE module = LoadLibraryExW(L"dbgeng.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!module) return 3;
    using Create = HRESULT (WINAPI*)(REFIID, PVOID*);
    auto create = reinterpret_cast<Create>(GetProcAddress(module, "DebugCreate"));
    IDebugClient* client = nullptr;
    IDebugControl* control = nullptr;
    IDebugSymbols* symbols = nullptr;
    HRESULT hr = create ? create(__uuidof(IDebugClient), reinterpret_cast<void**>(&client)) : E_FAIL;
    if (FAILED(hr)) return 4;
    client->QueryInterface(__uuidof(IDebugControl), reinterpret_cast<void**>(&control));
    client->QueryInterface(__uuidof(IDebugSymbols), reinterpret_cast<void**>(&symbols));
    if (!control || !symbols) return 4;
    DumpOutput output(log);
    client->SetOutputCallbacks(&output);
    symbols->SetSymbolPath("srv*E:\\MCM Menu\\.tools\\symbols*https://msdl.microsoft.com/download/symbols;E:\\SteamLibrary\\steamapps\\common\\Skyrim Special Edition\\Data\\SKSE\\Plugins");
    symbols->SetImagePath("E:\\SteamLibrary\\steamapps\\common\\Skyrim Special Edition;E:\\SteamLibrary\\steamapps\\common\\Skyrim Special Edition\\Data\\SKSE\\Plugins;C:\\Windows\\System32");
    hr = client->OpenDumpFile(argv[1]);
    if (SUCCEEDED(hr)) hr = control->WaitForEvent(0, INFINITE);
    if (SUCCEEDED(hr)) {
        const char* commands = argc > 3 ? argv[3] : ".symopt+ 0x100; .reload /f ntdll.dll; .reload /f kernelbase.dll; .reload /f win32u.dll; vertarget; ~; ~* k 16; lm";
        hr = control->Execute(DEBUG_OUTCTL_THIS_CLIENT, commands, DEBUG_EXECUTE_DEFAULT);
    }
    std::fprintf(stderr, "Debugger result: 0x%08lx\n", static_cast<unsigned long>(hr));
    client->EndSession(DEBUG_END_PASSIVE);
    client->SetOutputCallbacks(nullptr);
    symbols->Release(); control->Release(); client->Release();
    std::fclose(log);
    return FAILED(hr) ? 1 : 0;
}
