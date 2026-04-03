#ifndef SYSTEM_INFO_H
#define SYSTEM_INFO_H

#include "include/json.hpp"

using json = nlohmann::json;

class SystemInfo {
public:
    SystemInfo();
    ~SystemInfo();
    json get_all_info();

private:
    json get_cpu_info();
    json get_ram_info();
    json get_gpu_info();
    json get_storage_info();

#ifdef _WIN32
    bool initialize_wmi();
    void cleanup_wmi();
    json wmi_query(const wchar_t* query, const std::vector<const wchar_t*>& properties);
    struct IWbemLocator* pLoc;
    struct IWbemServices* pSvc;
    bool wmi_initialized;
#endif
};

#endif 