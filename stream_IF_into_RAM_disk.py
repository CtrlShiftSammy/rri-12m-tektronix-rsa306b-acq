import os
import sys
import time
import threading
import queue
import csv
from datetime import datetime
from ctypes import *
import numpy as np
import warnings
import shutil

# Load the RSA and USB API shared libraries
RTLD_LAZY = 0x0001
LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
rsa = CDLL("./libRSA_API.so", LAZYLOAD)
usbapi = CDLL("./libcyusb_shared.so", LAZYLOAD)

# Helper function to get error string from device
def GetErrorString(error):
    rsa.DEVICE_GetErrorString.restype = c_char_p
    errorString = rsa.DEVICE_GetErrorString(error)
    return errorString

def exerr(error):
    if error != 0:
        sys.exit(GetErrorString(error))

# Constants for device search and info
DEVSRCH_MAX_NUM_DEVICES = 20
DEVSRCH_SERIAL_MAX_STRLEN = 100
DEVSRCH_TYPE_MAX_STRLEN = 20
DEVINFO_MAX_STRLEN = 100

# Get and print API version
version = (c_char * DEVINFO_MAX_STRLEN)()
error = rsa.DEVICE_GetAPIVersion(version)
exerr(error)
print('API Version #: ' + str(version.value))

print('Searching for devices...')
numDevices = c_int()
deviceIDs = (c_int * DEVSRCH_MAX_NUM_DEVICES)()
deviceSNs = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_SERIAL_MAX_STRLEN)()
deviceTypes = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_TYPE_MAX_STRLEN)()
error = rsa.DEVICE_Search(byref(numDevices), deviceIDs, deviceSNs, deviceTypes)
foundDevices = {id: (deviceSNs[id].value, deviceTypes[id].value) for id in deviceIDs}
exerr(error)
print('Found ' + str(numDevices.value) + ' device(s):')
print(foundDevices)
if numDevices.value == 0:
    sys.exit('No devices found')

error = rsa.DEVICE_Connect(list(foundDevices.keys())[0])
exerr(error)

sn = (c_char * DEVINFO_MAX_STRLEN)()
error = rsa.DEVICE_GetSerialNumber(sn)
exerr(error)
print('Serial #: ' + str(sn.value))
rsa.CONFIG_Preset()


cf = 1420e6  # Center frequency in Hz
# Set acquisition parameters
center_freq = c_double(cf)  # center frequency
ref_level = c_double(0.0)     # Reference level in dBm

record_duration_seconds = 0.02
individual_file_length_seconds = 0.01
num_files_to_keep = round(record_duration_seconds / individual_file_length_seconds)
print(f"Number of files to keep: {num_files_to_keep}")
sample_rate = 112e6  # Sample rate in Hz
observation_duration = int(individual_file_length_seconds*1000)  # Observation duration in ms
file_size_expected_MiB = int((sample_rate * individual_file_length_seconds * 2) / (1024 * 1024))  # 2 bytes per sample
print(f"Expected file size: {file_size_expected_MiB} MiB")
total_memory_required_MiB = file_size_expected_MiB * num_files_to_keep
print(f"Total memory required: {total_memory_required_MiB} MiB")
print(f"Setting Center Frequency: {center_freq.value} Hz")

exerr(rsa.CONFIG_SetCenterFreq(center_freq))

print(f"Setting Reference Level: {ref_level.value} dBm")

exerr(rsa.CONFIG_SetReferenceLevel(ref_level))

# rsa.CONFIG_SetCenterFreq(center_freq)
# rsa.CONFIG_SetReferenceLevel(ref_level)


# output_dir = "IF_data_dump"
output_dir = "/mnt/ramdisk/IF_data_temp"
os.makedirs(output_dir, exist_ok=True)


# Configure IF streaming
print("Configuring IF streaming parameters...")
exerr(rsa.IFSTREAM_SetOutputConfiguration(c_int(1)))  # IFSOD_FILE_R3F format
exerr(rsa.IFSTREAM_SetDiskFilePath(c_char_p(output_dir.encode('utf-8'))))  # Set output directory
exerr(rsa.IFSTREAM_SetDiskFilenameBase(c_char_p(b"if_capture")))
exerr(rsa.IFSTREAM_SetDiskFilenameSuffix(c_int(1)))  # IFSSDFN_SUFFIX_TIMESTAMP
exerr(rsa.IFSTREAM_SetDiskFileLength(c_long(observation_duration)))
# exerr(rsa.IFSTREAM_SetDiskFileMode(c_int(0)))         # StreamingModeFormatted
exerr(rsa.IFSTREAM_SetDiskFileCount(c_int(num_files_to_keep)))  # Number of files to keep
print("IF streaming parameters configured.")

# Start acquisition
print("Starting acquisition...")
exerr(rsa.DEVICE_Run())
exerr(rsa.IFSTREAM_SetEnable(c_bool(True)))
print("IF streaming enabled.")

writing = c_bool(True)
waitTime = observation_duration / 10 / 1000  # seconds
start_time = time.time()
timeout_time = 10 # seconds
while writing.value:
    time.sleep(waitTime)
    rsa.IFSTREAM_GetActiveStatus(byref(writing))
    sys.stdout.write(f"\rIF streaming active: {writing.value}, time elapsed: {time.time() - start_time:.2f} seconds")
    sys.stdout.flush()
# after loop, print newline to move cursor down
print()

print('Streaming finished.')
end_time = time.time()
print(f"Time taken for acquisition: {end_time - start_time:.2f} seconds")
rsa.IFSTREAM_SetEnable(c_bool(False))
rsa.DEVICE_Stop()
print("Acquisition stopped.")
rsa.DEVICE_Disconnect()
print("Device disconnected.")


final_storage_dir = "IF_data_dump"
os.makedirs(final_storage_dir, exist_ok=True)

print(f"Moving files from {output_dir} to {final_storage_dir}...")
for filename in os.listdir(output_dir):
    full_src = os.path.join(output_dir, filename)
    full_dst = os.path.join(final_storage_dir, filename)
    shutil.move(full_src, full_dst)
print("All files moved successfully.")