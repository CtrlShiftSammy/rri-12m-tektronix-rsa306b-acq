#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <filesystem>
#include <cstring>
#include <cstdlib>
#include <dlfcn.h>
#include <vector>

using namespace std;
using namespace std::chrono;
using namespace std::filesystem;

// Include the RSA API definitions
extern "C" {
    #include "RSA_API.h"
}

// Global function pointers for dynamic library loading
void* rsa_lib = nullptr;
void* usb_lib = nullptr;

// Device management functions
typedef ReturnStatus (*DEVICE_GetAPIVersion_t)(char*);
typedef ReturnStatus (*DEVICE_Search_t)(int*, int*, char[][100], char[][20]);
typedef ReturnStatus (*DEVICE_Connect_t)(int);
typedef ReturnStatus (*DEVICE_GetSerialNumber_t)(char*);
typedef ReturnStatus (*DEVICE_Disconnect_t)();
typedef ReturnStatus (*DEVICE_Run_t)();
typedef ReturnStatus (*DEVICE_Stop_t)();
typedef const char* (*DEVICE_GetErrorString_t)(ReturnStatus);

// Configuration functions
typedef ReturnStatus (*CONFIG_Preset_t)();
typedef ReturnStatus (*CONFIG_SetCenterFreq_t)(double);
typedef ReturnStatus (*CONFIG_SetReferenceLevel_t)(double);

// IF Streaming functions  
typedef ReturnStatus (*IFSTREAM_SetDiskFilePath_t)(const char*);
typedef ReturnStatus (*IFSTREAM_SetDiskFilenameBase_t)(const char*);
typedef ReturnStatus (*IFSTREAM_SetDiskFilenameSuffix_t)(int);
typedef ReturnStatus (*IFSTREAM_SetDiskFileLength_t)(long);
typedef ReturnStatus (*IFSTREAM_SetDiskFileMode_t)(int);
typedef ReturnStatus (*IFSTREAM_SetDiskFileCount_t)(int);
typedef ReturnStatus (*IFSTREAM_SetEnable_t)(bool);
typedef ReturnStatus (*IFSTREAM_GetActiveStatus_t)(bool*);

// Global function pointers
DEVICE_GetAPIVersion_t DEVICE_GetAPIVersion_func;
DEVICE_Search_t DEVICE_Search_func;
DEVICE_Connect_t DEVICE_Connect_func;
DEVICE_GetSerialNumber_t DEVICE_GetSerialNumber_func;
DEVICE_Disconnect_t DEVICE_Disconnect_func;
DEVICE_Run_t DEVICE_Run_func;
DEVICE_Stop_t DEVICE_Stop_func;
DEVICE_GetErrorString_t DEVICE_GetErrorString_func;
CONFIG_Preset_t CONFIG_Preset_func;
CONFIG_SetCenterFreq_t CONFIG_SetCenterFreq_func;
CONFIG_SetReferenceLevel_t CONFIG_SetReferenceLevel_func;
IFSTREAM_SetDiskFilePath_t IFSTREAM_SetDiskFilePath_func;
IFSTREAM_SetDiskFilenameBase_t IFSTREAM_SetDiskFilenameBase_func;
IFSTREAM_SetDiskFilenameSuffix_t IFSTREAM_SetDiskFilenameSuffix_func;
IFSTREAM_SetDiskFileLength_t IFSTREAM_SetDiskFileLength_func;
IFSTREAM_SetDiskFileMode_t IFSTREAM_SetDiskFileMode_func;
IFSTREAM_SetDiskFileCount_t IFSTREAM_SetDiskFileCount_func;
IFSTREAM_SetEnable_t IFSTREAM_SetEnable_func;
IFSTREAM_GetActiveStatus_t IFSTREAM_GetActiveStatus_func;

// Error checking function
bool checkError(ReturnStatus error, const string& operation = "") {
    if (error != 0) {
        cerr << "Error in " << operation << ": Code " << error << endl;
        if (DEVICE_GetErrorString_func) {
            const char* errorStr = DEVICE_GetErrorString_func(error);
            if (errorStr) {
                cerr << "Error details: " << errorStr << endl;
            }
        }
        return false;
    }
    return true;
}

// Load shared libraries and function pointers
bool loadLibraries() {
    // Load RSA API library
    rsa_lib = dlopen("./libRSA_API.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!rsa_lib) {
        cerr << "Error loading libRSA_API.so: " << dlerror() << endl;
        return false;
    }

    // Load USB library
    usb_lib = dlopen("./libcyusb_shared.so", RTLD_LAZY | RTLD_GLOBAL);
    if (!usb_lib) {
        cerr << "Error loading libcyusb_shared.so: " << dlerror() << endl;
        dlclose(rsa_lib);
        return false;
    }

    // Load function pointers
    DEVICE_GetAPIVersion_func = (DEVICE_GetAPIVersion_t)dlsym(rsa_lib, "DEVICE_GetAPIVersion");
    DEVICE_Search_func = (DEVICE_Search_t)dlsym(rsa_lib, "DEVICE_Search");
    DEVICE_Connect_func = (DEVICE_Connect_t)dlsym(rsa_lib, "DEVICE_Connect");
    DEVICE_GetSerialNumber_func = (DEVICE_GetSerialNumber_t)dlsym(rsa_lib, "DEVICE_GetSerialNumber");
    DEVICE_Disconnect_func = (DEVICE_Disconnect_t)dlsym(rsa_lib, "DEVICE_Disconnect");
    DEVICE_Run_func = (DEVICE_Run_t)dlsym(rsa_lib, "DEVICE_Run");
    DEVICE_Stop_func = (DEVICE_Stop_t)dlsym(rsa_lib, "DEVICE_Stop");
    DEVICE_GetErrorString_func = (DEVICE_GetErrorString_t)dlsym(rsa_lib, "DEVICE_GetErrorString");
    CONFIG_Preset_func = (CONFIG_Preset_t)dlsym(rsa_lib, "CONFIG_Preset");
    CONFIG_SetCenterFreq_func = (CONFIG_SetCenterFreq_t)dlsym(rsa_lib, "CONFIG_SetCenterFreq");
    CONFIG_SetReferenceLevel_func = (CONFIG_SetReferenceLevel_t)dlsym(rsa_lib, "CONFIG_SetReferenceLevel");
    IFSTREAM_SetDiskFilePath_func = (IFSTREAM_SetDiskFilePath_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFilePath");
    IFSTREAM_SetDiskFilenameBase_func = (IFSTREAM_SetDiskFilenameBase_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFilenameBase");
    IFSTREAM_SetDiskFilenameSuffix_func = (IFSTREAM_SetDiskFilenameSuffix_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFilenameSuffix");
    IFSTREAM_SetDiskFileLength_func = (IFSTREAM_SetDiskFileLength_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFileLength");
    IFSTREAM_SetDiskFileMode_func = (IFSTREAM_SetDiskFileMode_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFileMode");
    IFSTREAM_SetDiskFileCount_func = (IFSTREAM_SetDiskFileCount_t)dlsym(rsa_lib, "IFSTREAM_SetDiskFileCount");
    IFSTREAM_SetEnable_func = (IFSTREAM_SetEnable_t)dlsym(rsa_lib, "IFSTREAM_SetEnable");
    IFSTREAM_GetActiveStatus_func = (IFSTREAM_GetActiveStatus_t)dlsym(rsa_lib, "IFSTREAM_GetActiveStatus");

    // Check if all critical functions were loaded
    if (!DEVICE_GetAPIVersion_func || !DEVICE_Search_func || !DEVICE_Connect_func ||
        !DEVICE_Disconnect_func || !CONFIG_Preset_func || !CONFIG_SetCenterFreq_func ||
        !CONFIG_SetReferenceLevel_func || !IFSTREAM_SetEnable_func) {
        cerr << "Failed to load one or more required functions" << endl;
        return false;
    }

    return true;
}

// Clean up libraries
void cleanup() {
    if (rsa_lib) {
        dlclose(rsa_lib);
        rsa_lib = nullptr;
    }
    if (usb_lib) {
        dlclose(usb_lib);
        usb_lib = nullptr;
    }
}

// Search and connect to RSA device
int searchAndConnect() {
    char version[100];
    ReturnStatus rs = DEVICE_GetAPIVersion_func(version);
    if (!checkError(rs, "DEVICE_GetAPIVersion")) return -1;

    cout << "API Version: " << version << endl;
    cout << "Searching for devices..." << endl;

    int numDevices;
    int deviceIDs[20];
    char deviceSNs[20][100];
    char deviceTypes[20][20];

    rs = DEVICE_Search_func(&numDevices, deviceIDs, deviceSNs, deviceTypes);
    if (!checkError(rs, "DEVICE_Search")) return -1;

    cout << "Found " << numDevices << " device(s)" << endl;

    if (numDevices == 0) {
        cerr << "No devices found" << endl;
        return -1;
    }

    // Print device information
    for (int i = 0; i < numDevices; i++) {
        cout << "Device " << i << ": ID=" << deviceIDs[i] 
             << ", Serial=" << deviceSNs[i] 
             << ", Type=" << deviceTypes[i] << endl;
    }

    // Connect to first device
    int deviceID = deviceIDs[0];
    rs = DEVICE_Connect_func(deviceID);
    if (!checkError(rs, "DEVICE_Connect")) return -1;

    char serialNumber[100];
    rs = DEVICE_GetSerialNumber_func(serialNumber);
    if (!checkError(rs, "DEVICE_GetSerialNumber")) return -1;

    cout << "Connected to device " << deviceID << endl;
    cout << "Serial Number: " << serialNumber << endl;
    cout << "Device Type: " << deviceTypes[0] << endl;

    return deviceID;
}

// Configure IF streaming (similar to Python version)
bool configureIFStreaming(const string& outputDir, const string& filenameBase, 
                         int observationDurationMs, int numFilesToKeep) {
    cout << "Configuring IF streaming parameters..." << endl;

    // Create output directory if it doesn't exist
    if (!exists(outputDir)) {
        create_directories(outputDir);
        cout << "Created directory: " << outputDir << endl;
    }

    ReturnStatus rs;

    // Set IF streaming parameters (matching Python script)
    if (IFSTREAM_SetDiskFilePath_func) {
        rs = IFSTREAM_SetDiskFilePath_func(outputDir.c_str());
        if (!checkError(rs, "IFSTREAM_SetDiskFilePath")) return false;
    }

    if (IFSTREAM_SetDiskFilenameBase_func) {
        rs = IFSTREAM_SetDiskFilenameBase_func(filenameBase.c_str());
        if (!checkError(rs, "IFSTREAM_SetDiskFilenameBase")) return false;
    }

    if (IFSTREAM_SetDiskFilenameSuffix_func) {
        rs = IFSTREAM_SetDiskFilenameSuffix_func(1); // IFSSDFN_SUFFIX_TIMESTAMP
        if (!checkError(rs, "IFSTREAM_SetDiskFilenameSuffix")) return false;
    }

    if (IFSTREAM_SetDiskFileLength_func) {
        rs = IFSTREAM_SetDiskFileLength_func(observationDurationMs);
        if (!checkError(rs, "IFSTREAM_SetDiskFileLength")) return false;
    }

    if (IFSTREAM_SetDiskFileMode_func) {
        rs = IFSTREAM_SetDiskFileMode_func(0); // StreamingModeFormatted
        if (!checkError(rs, "IFSTREAM_SetDiskFileMode")) return false;
    }

    if (IFSTREAM_SetDiskFileCount_func) {
        rs = IFSTREAM_SetDiskFileCount_func(numFilesToKeep);
        if (!checkError(rs, "IFSTREAM_SetDiskFileCount")) return false;
    }

    cout << "IF streaming parameters configured." << endl;
    return true;
}

// Add safe_move to work around cross-device rename errors
bool safe_move(const path& src, const path& dst) {
    try {
        copy_file(src, dst, copy_options::overwrite_existing);
        remove(src);
        return true;
    } catch (const filesystem_error& e) {
        cerr << "Error moving file " << src << ": " << e.what() << endl;
        return false;
    }
}

// Move files from source to destination directory
void moveFiles(const string& sourceDir, const string& destDir) {
    cout << "Moving files from " << sourceDir << " to " << destDir << "..." << endl;

    if (!exists(destDir)) {
        create_directories(destDir);
    }

    int fileCount = 0;
    for (const auto& entry : directory_iterator(sourceDir)) {
        if (entry.is_regular_file()) {
            string filename = entry.path().filename();
            path sourcePath = entry.path();
            path destPath = path(destDir) / filename;

            // use safe_move instead of rename
            if (safe_move(sourcePath, destPath)) {
                fileCount++;
                cout << "Moved: " << filename << endl;
            }
        }
    }

    cout << "Moved " << fileCount << " files successfully." << endl;
}

#ifndef IFSTREAM_SIMPLE_NO_MAIN
int main() {
    cout << "RSA API IF Streaming Application" << endl;
    cout << "=================================" << endl;

    // Configuration parameters (matching Python script)
    double centerFreq = 1420e6;
    double refLevel = 0.0;      // reference level
    double recordDurationSeconds = 0.002;
    double individualFileLengthSeconds = 0.001;
    int numFilesToKeep = static_cast<int>(recordDurationSeconds / individualFileLengthSeconds);

    double sampleRate = 112e6;  // 112 Msps
    int observationDurationMs = static_cast<int>(individualFileLengthSeconds * 1000);

    // Calculate file size information
    int fileSizeMiB = static_cast<int>((sampleRate * individualFileLengthSeconds * 2) / (1024 * 1024));
    int totalMemoryMiB = fileSizeMiB * numFilesToKeep;

    cout << "Configuration:" << endl;
    cout << "  Center Frequency: " << centerFreq / 1e6 << " MHz" << endl;
    cout << "  Reference Level: " << refLevel << " dBm" << endl;
    cout << "  Individual File Length: " << individualFileLengthSeconds * 1000 << " ms" << endl;
    cout << "  Number of files to keep: " << numFilesToKeep << endl;
    cout << "  Expected file size: " << fileSizeMiB << " MiB" << endl;
    cout << "  Total memory required: " << totalMemoryMiB << " MiB" << endl;

    // Directory paths
    string tempOutputDir = "/mnt/ramdisk/IF_data_temp";
    string finalOutputDir = "IF_data_dump";
    string filenameBase = "if_capture";

    int deviceID = -1;

    try {
        // Load libraries
        if (!loadLibraries()) {
            cerr << "Failed to load RSA API libraries" << endl;
            return 1;
        }

        // Search and connect to device
        deviceID = searchAndConnect();
        if (deviceID < 0) {
            cerr << "Failed to connect to RSA device" << endl;
            cleanup();
            return 1;
        }

        // Preset and configure device
        ReturnStatus rs = CONFIG_Preset_func();
        if (!checkError(rs, "CONFIG_Preset")) {
            cleanup();
            return 1;
        }

        cout << "Setting Center Frequency: " << centerFreq << " Hz" << endl;
        rs = CONFIG_SetCenterFreq_func(centerFreq);
        if (!checkError(rs, "CONFIG_SetCenterFreq")) {
            cleanup();
            return 1;
        }

        cout << "Setting Reference Level: " << refLevel << " dBm" << endl;
        rs = CONFIG_SetReferenceLevel_func(refLevel);
        if (!checkError(rs, "CONFIG_SetReferenceLevel")) {
            cleanup();
            return 1;
        }

        // Configure IF streaming
        if (!configureIFStreaming(tempOutputDir, filenameBase, 
                                 observationDurationMs, numFilesToKeep)) {
            cerr << "Failed to configure IF streaming" << endl;
            cleanup();
            return 1;
        }

        // Start acquisition
        cout << "Starting acquisition..." << endl;
        rs = DEVICE_Run_func();
        if (!checkError(rs, "DEVICE_Run")) {
            cleanup();
            return 1;
        }

        rs = IFSTREAM_SetEnable_func(true);
        if (!checkError(rs, "IFSTREAM_SetEnable")) {
            cleanup();
            return 1;
        }

        cout << "IF streaming enabled." << endl;

        // Monitor streaming status
        bool writing = true;
        int waitTimeMs = 10; // Check every X ms
        auto startTime = steady_clock::now();

        while (writing) {
            this_thread::sleep_for(milliseconds(waitTimeMs));

            if (IFSTREAM_GetActiveStatus_func) {
                rs = IFSTREAM_GetActiveStatus_func(&writing);
                if (!checkError(rs, "IFSTREAM_GetActiveStatus")) break;
            }

            auto elapsed = steady_clock::now() - startTime;
            auto elapsedSec = duration_cast<milliseconds>(elapsed).count() / 1000.0;
            cout << "\rIF streaming active: " << (writing ? "true" : "false") 
                 << ", time elapsed: " << elapsedSec << " seconds" << flush;

            // Safety timeout
            if (elapsedSec > 30.0) {
                cerr << "\nTimeout after 30 seconds, stopping..." << endl;
                break;
            }
        }

        cout << "\nStreaming finished." << endl;

        // Stop streaming and device
        rs = IFSTREAM_SetEnable_func(false);
        checkError(rs, "IFSTREAM_SetEnable");

        rs = DEVICE_Stop_func();
        checkError(rs, "DEVICE_Stop");

        cout << "Acquisition stopped." << endl;

        // Move files from temp to final location
        moveFiles(tempOutputDir, finalOutputDir);

        // Disconnect
        rs = DEVICE_Disconnect_func();
        if (checkError(rs, "DEVICE_Disconnect")) {
            cout << "Device disconnected." << endl;
        }

        cout << "IF streaming completed successfully!" << endl;

    } catch (const exception& e) {
        cerr << "Exception occurred: " << e.what() << endl;

        // Cleanup on error
        if (deviceID >= 0 && DEVICE_Disconnect_func) {
            DEVICE_Disconnect_func();
        }
        cleanup();
        return 1;
    }

    cleanup();
    return 0;
}
#endif