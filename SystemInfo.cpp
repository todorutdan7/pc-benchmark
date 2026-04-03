#include "SystemInfo.h"
#include <iostream>
#include <string>
#include <vector>


#define _WIN32_DCOM
#include <windows.h>
#include <comdef.h>
#include <wbemidl.h>


SystemInfo::SystemInfo() {
    wmi_initialized = initialize_wmi();
}

SystemInfo::~SystemInfo() {
    if (wmi_initialized) {
        cleanup_wmi();
    }
}

json SystemInfo::get_all_info() {
    json info;
    info["cpu"] = get_cpu_info();
    info["ram"] = get_ram_info();
    info["gpu"] = get_gpu_info();
    info["storage"] = get_storage_info();
    return info;
}


bool SystemInfo::initialize_wmi() {
    pLoc = nullptr;
    pSvc = nullptr;
    HRESULT hres;
    hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    if (FAILED(hres)) return false;
    hres = CoInitializeSecurity(NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_DEFAULT, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL);
    if (FAILED(hres)) { CoUninitialize(); return false; }
    hres = CoCreateInstance(CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, IID_IWbemLocator, (LPVOID*)&pLoc);
    if (FAILED(hres)) { CoUninitialize(); return false; }
    hres = pLoc->ConnectServer(_bstr_t(L"ROOT\\CIMV2"), NULL, NULL, 0, NULL, 0, 0, &pSvc);
    if (FAILED(hres)) { pLoc->Release(); CoUninitialize(); return false; }
    hres = CoSetProxyBlanket(pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL, RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);
    if (FAILED(hres)) { pSvc->Release(); pLoc->Release(); CoUninitialize(); return false; }
    return true;
}

void SystemInfo::cleanup_wmi() {
    if (pSvc) pSvc->Release();
    if (pLoc) pLoc->Release();
    CoUninitialize();
}

json SystemInfo::wmi_query(const wchar_t* query, const std::vector<const wchar_t*>& properties) {
    if (!wmi_initialized) return { {"error", "WMI not initialized"} };

    IEnumWbemClassObject* pEnumerator = NULL;
    HRESULT hres = pSvc->ExecQuery(bstr_t("WQL"), bstr_t(query), WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY, NULL, &pEnumerator);
    if (FAILED(hres)) return { {"error", "WMI query failed"} };

    json results = json::array();
    IWbemClassObject* pclsObj = NULL;
    ULONG uReturn = 0;

    while (pEnumerator) {
        pEnumerator->Next(WBEM_INFINITE, 1, &pclsObj, &uReturn);
        if (0 == uReturn) break;

        json item;
        for (const auto& prop_name : properties) {
            VARIANT vtProp;
            pclsObj->Get(prop_name, 0, &vtProp, 0, 0);

            std::string prop_name_str;
            {
                _bstr_t b(prop_name);
                prop_name_str = (const char*)b;
            }

            if (vtProp.vt == VT_BSTR) {
                _bstr_t bstr(vtProp.bstrVal);
                item[prop_name_str] = (const char*)bstr;
            }
            else if (vtProp.vt == VT_I4 || vtProp.vt == VT_UI4) {
                item[prop_name_str] = vtProp.uintVal;
            }
            VariantClear(&vtProp);
        }
        results.push_back(item);
        pclsObj->Release();
    }
    if (pEnumerator) pEnumerator->Release();

    return results;
}



json SystemInfo::get_cpu_info() {
    json cpus = wmi_query(L"SELECT * FROM Win32_Processor",
        { L"Name", L"NumberOfCores", L"NumberOfLogicalProcessors", L"MaxClockSpeed", L"L3CacheSize" });
    return cpus.is_array() && !cpus.empty() ? cpus[0] : json({});
}

json SystemInfo::get_ram_info() {
    
    json ram_info;
    unsigned long long total_bytes = 0;

    json sticks = wmi_query(L"SELECT * FROM Win32_PhysicalMemory",
        { L"Manufacturer", L"Capacity", L"Speed", L"PartNumber" });

    if (sticks.is_array()) {
        for (auto& stick : sticks) {
            if (stick.contains("Capacity")) {
                try {
                    unsigned long long bytes = std::stoull(stick["Capacity"].get<std::string>());
                    stick["capacity_gb"] = bytes / (1024 * 1024 * 1024);
                    total_bytes += bytes;
                    stick.erase("Capacity");
                }
                catch (...) {  }
            }
        }
    }

    ram_info["sticks"] = sticks;
    ram_info["total_size_gb"] = total_bytes / (1024 * 1024 * 1024);
    return ram_info;
}

json SystemInfo::get_gpu_info() {
    return wmi_query(L"SELECT * FROM Win32_VideoController",
        { L"Name", L"AdapterRAM", L"DriverVersion" });
}

json SystemInfo::get_storage_info() {
    json drives = wmi_query(L"SELECT * FROM Win32_DiskDrive", { L"Model", L"Size" });

    if (drives.is_array()) {
        for (auto& drive : drives) {
            if (drive.contains("Size")) {
                try {
                    unsigned long long bytes = std::stoull(drive["Size"].get<std::string>());
                    drive["capacity_gb"] = bytes / (1024 * 1024 * 1024);
                    drive.erase("Size");
                }
                catch (...) { }
            }
        }
    }
    return drives;
}