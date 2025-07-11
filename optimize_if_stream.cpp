#include <iostream>
#include <vector>
#include <chrono>
#include <thread>
#include <filesystem>
#include <cmath>
#include <algorithm>

#define IFSTREAM_SIMPLE_NO_MAIN
// pull in loadLibraries(), searchAndConnect(), checkError(), cleanup(),
// and the IFSTREAM_* function pointers from if_stream_simple.cpp
#include "if_stream_simple.cpp"

int main() {
    using namespace std;
    using namespace std::chrono;
    namespace fs = std::filesystem;

    const double totalDurationSec = 10.0;
    const string outputDir = "/mnt/ramdisk2/IF_data_temp";
    const string filenameBase = "if_capture";

    // 1) load & connect
    if (!loadLibraries()) {
        cerr << "Failed to load libraries\n";
        return 1;
    }
    int devId = searchAndConnect();
    if (devId < 0) {
        cleanup();
        return 1;
    }

    // 2) static IFSTREAM setup (path, base, suffix, mode)
    checkError(IFSTREAM_SetDiskFilePath_func(outputDir.c_str()),       "IFSTREAM_SetDiskFilePath");
    checkError(IFSTREAM_SetDiskFilenameBase_func(filenameBase.c_str()),"IFSTREAM_SetDiskFilenameBase");
    checkError(IFSTREAM_SetDiskFilenameSuffix_func(1),                 "IFSTREAM_SetDiskFilenameSuffix"); // timestamp
    checkError(IFSTREAM_SetDiskFileMode_func(0),                       "IFSTREAM_SetDiskFileMode");   // formatted

    // 3) benchmarking loop
    vector<pair<double,double>> results;
    const int steps = 6;
    for (int i = 0; i < steps; ++i) {
        double step_size = 0.2;
        double max_secs = steps * step_size;
        double secs = step_size + (max_secs - step_size) * i / (steps - 1);
        // double secs = 0.5 + (3.0 - 0.5) * i / (steps - 1);
        int obsMs = int(secs * 1000 + 0.5);
        int numFiles = int(round(totalDurationSec / secs));

        // clear old files
        for (auto& e : fs::directory_iterator(outputDir)) {
            if (e.is_regular_file()) fs::remove(e);
        }

        // set per‐run IFSTREAM params
        checkError(IFSTREAM_SetDiskFileLength_func(obsMs), "IFSTREAM_SetDiskFileLength");
        checkError(IFSTREAM_SetDiskFileCount_func(numFiles), "IFSTREAM_SetDiskFileCount");

        // run + time
        checkError(DEVICE_Run_func(),            "DEVICE_Run");
        // auto t0 = steady_clock::now();
        checkError(IFSTREAM_SetEnable_func(true),"IFSTREAM_SetEnable");
        auto t0 = steady_clock::now();
        bool writing = true;
        while (writing) {
            this_thread::sleep_for(milliseconds(1)); // check every 1 ms
            IFSTREAM_GetActiveStatus_func(&writing);
        }

        double elapsed = duration<double>(steady_clock::now() - t0).count();
        checkError(IFSTREAM_SetEnable_func(false),"IFSTREAM_SetEnable");
        checkError(DEVICE_Stop_func(),           "DEVICE_Stop");

        double rate = obsMs * double(numFiles) / elapsed;
        results.emplace_back(secs, rate);
        cout << "[" << secs << " s] → " << rate << " ms/s\n";
    }

    // 4) report optimal
    auto opt = *max_element(
        results.begin(), results.end(),
        [](auto &a, auto &b){ return a.second < b.second; }
    );
    cout << "\nOptimal file length: " << opt.first
         << " s → " << opt.second << " ms/s\n";

    // 5) cleanup
    DEVICE_Disconnect_func();
    cleanup();
    return 0;
}
