// Read selected local file events through the Windows ETW/TDH APIs.
// Other providers, including unrecognized CLR events, are not decoded.
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <tdh.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

static std::wstring needle;
static bool metadata_only = false;
static std::unordered_set<ULONG> worker_pids;
static std::ofstream output;
static std::unordered_set<ULONGLONG> operations;
static std::unordered_set<ULONGLONG> file_objects;
static std::unordered_set<ULONGLONG> rename_operations;
static size_t exported = 0;
static const GUID file_io = {0x90cbdc39, 0x4a3e, 0x11d1, {0x84, 0xf4, 0, 0, 0xf8, 4, 0x64, 0xe3}};
static const GUID process_events = {0x3d6fa8d0, 0xfe05, 0x11d0, {0x9d, 0xda, 0, 0xc0, 0x4f, 0xd7, 0xba, 0x7c}};
static const GUID image_events = {0x2cb15d1d, 0x5fc1, 0x11d2, {0xab, 0xe1, 0, 0xa0, 0xc9, 0x11, 0xf5, 0x18}};

static std::string utf8(const std::wstring& value) {
    int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0, nullptr, nullptr);
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), result.data(), size, nullptr, nullptr);
    return result;
}

static std::string quote(const std::string& value) {
    std::ostringstream result;
    result << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') result << '\\' << c;
        else if (c < 32) result << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (unsigned)c;
        else result << c;
    }
    return result.str() + '"';
}

static std::string hex(const BYTE* value, size_t size) {
    std::ostringstream result;
    result << std::hex << std::setfill('0');
    for (size_t i = 0; i < size; ++i) result << std::setw(2) << (unsigned)value[i];
    return result.str();
}

static void WINAPI consume(EVENT_RECORD* event) {
    auto* data = static_cast<BYTE*>(event->UserData);
    size_t size = event->UserDataLength;
    bool metadata = IsEqualGUID(event->EventHeader.ProviderId, process_events) ||
                    IsEqualGUID(event->EventHeader.ProviderId, image_events);
    if (metadata_only && !metadata) return;
    bool file = IsEqualGUID(event->EventHeader.ProviderId, file_io);
    bool worker = !worker_pids.empty() && file && worker_pids.count(event->EventHeader.ProcessId) != 0;
    if (!worker_pids.empty() && !worker) return;
    bool matched = false;
    for (size_t offset = 0; !metadata_only && !worker && offset + needle.size() * 2 <= size; ++offset) {
        if (memcmp(data + offset, needle.data(), needle.size() * 2) == 0) { matched = true; break; }
    }
    unsigned opcode = event->EventHeader.EventDescriptor.Opcode;
    ULONGLONG irp = 0;
    if (file && size >= 8) memcpy(&irp, data, 8);
    // Rename contains no filename; retain its paired OperationEnd status.
    if (file && (opcode == 71 || (matched && opcode == 64))) operations.insert(irp);
    if (file && opcode == 71) rename_operations.insert(irp);
    bool paired = file && opcode == 76 && operations.erase(irp) != 0;
    if (file && opcode == 76) rename_operations.erase(irp);
    bool related = false;
    if (file && ((opcode >= 96 && opcode <= 101) || opcode == 65 || opcode == 66)) {
        for (size_t offset = 0; offset + 8 <= size; offset += 8) {
            ULONGLONG pointer = 0;
            memcpy(&pointer, data + offset, 8);
            bool lifecycle = opcode == 65 || opcode == 66;
            if (lifecycle ? file_objects.count(pointer) != 0 : rename_operations.count(pointer) != 0) {
                related = true; break;
            }
        }
    }
    if (!(metadata_only || worker || matched || (file && opcode == 71) || paired || related)) return;
    WCHAR provider[40];
    StringFromGUID2(event->EventHeader.ProviderId, provider, 40);
    output << "{\"provider\":" << quote(utf8(provider)) << ",\"opcode\":" << opcode
           << ",\"event_id\":" << event->EventHeader.EventDescriptor.Id
           << ",\"pid\":" << event->EventHeader.ProcessId << ",\"tid\":" << event->EventHeader.ThreadId
           << ",\"filetime\":" << event->EventHeader.TimeStamp.QuadPart << ",\"properties\":{";
    ULONG bytes = 0;
    auto status = TdhGetEventInformation(event, 0, nullptr, nullptr, &bytes);
    bool comma = false;
    if (status == ERROR_INSUFFICIENT_BUFFER) {
        std::vector<BYTE> metadata(bytes);
        auto* info = reinterpret_cast<TRACE_EVENT_INFO*>(metadata.data());
        if (TdhGetEventInformation(event, 0, nullptr, info, &bytes) == ERROR_SUCCESS) {
            for (ULONG i = 0; i < info->TopLevelPropertyCount; ++i) {
                auto& property = info->EventPropertyInfoArray[i];
                if (property.Flags & PropertyStruct) continue;
                auto* name = reinterpret_cast<WCHAR*>(metadata.data() + property.NameOffset);
                PROPERTY_DATA_DESCRIPTOR descriptor = {};
                descriptor.PropertyName = reinterpret_cast<ULONGLONG>(name);
                descriptor.ArrayIndex = ULONG_MAX;
                ULONG length = 0;
                if (TdhGetPropertySize(event, 0, nullptr, 1, &descriptor, &length) != ERROR_SUCCESS) continue;
                std::vector<BYTE> value(length + 2, 0);
                if (TdhGetProperty(event, 0, nullptr, 1, &descriptor, length, value.data()) != ERROR_SUCCESS) continue;
                if (file && std::wstring(name) == L"FileObject" && length == 8) {
                    ULONGLONG object = 0;
                    memcpy(&object, value.data(), 8);
                    if (matched && opcode == 64) file_objects.insert(object);
                    if (opcode == 66) file_objects.erase(object);
                }
                std::string formatted;
                if (property.nonStructType.InType == TDH_INTYPE_UNICODESTRING) formatted = utf8(reinterpret_cast<WCHAR*>(value.data()));
                else if (property.nonStructType.InType == TDH_INTYPE_ANSISTRING) formatted = reinterpret_cast<char*>(value.data());
                else formatted = "hex:" + hex(value.data(), length);
                if (comma) output << ',';
                output << quote(utf8(name)) << ':' << quote(formatted);
                comma = true;
            }
        }
    }
    output << '}';
    if (!comma) output << ",\"payload_hex\":" << quote(hex(data, size));
    output << "}\n";
    ++exported;
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 4 && argc != 5) { std::cerr << "usage: exporter trace.etl output.jsonl path-fragment [metadata|pids=1,2]\n"; return 2; }
    if (argc == 5) {
        std::wstring mode = argv[4];
        if (mode == L"metadata") metadata_only = true;
        else if (mode.rfind(L"pids=", 0) == 0) {
            std::wistringstream values(mode.substr(5));
            std::wstring value;
            while (std::getline(values, value, L',')) {
                size_t used = 0;
                unsigned long pid = 0;
                try { pid = std::stoul(value, &used); } catch (...) { return 2; }
                if (used != value.size() || pid == 0) return 2;
                worker_pids.insert(pid);
            }
            if (worker_pids.empty()) return 2;
        }
        else return 2;
    }
    needle = argv[3];
    if (needle.size() < 12) { std::cerr << "Use a specific task path fragment\n"; return 2; }
    output.open(argv[2], std::ios::binary | std::ios::trunc);
    if (!output) return 2;
    EVENT_TRACE_LOGFILEW logfile = {};
    logfile.LogFileName = argv[1];
    logfile.ProcessTraceMode = PROCESS_TRACE_MODE_EVENT_RECORD;
    logfile.EventRecordCallback = consume;
    TRACEHANDLE handle = OpenTraceW(&logfile);
    if (handle == INVALID_PROCESSTRACE_HANDLE) { std::cerr << "OpenTrace: " << GetLastError(); return 1; }
    ULONG status = ProcessTrace(&handle, 1, nullptr, nullptr);
    CloseTrace(handle);
    std::cout << "status=" << status << " exported=" << exported << '\n';
    return status == ERROR_SUCCESS ? 0 : 1;
}
