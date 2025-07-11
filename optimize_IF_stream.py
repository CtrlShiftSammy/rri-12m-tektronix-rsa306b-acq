import os
import sys
import time
import threading
import queue
import csv
from datetime import datetime
from ctypes import *
import numpy as np
import matplotlib.pyplot as plt           # added
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


cf = 100e6  # Center frequency in Hz
# Set acquisition parameters
center_freq = c_double(cf)  # center frequency
ref_level = c_double(0.0)     # Reference level in dBm

print(f"Setting Center Frequency: {center_freq.value} Hz")

exerr(rsa.CONFIG_SetCenterFreq(center_freq))

print(f"Setting Reference Level: {ref_level.value} dBm")

exerr(rsa.CONFIG_SetReferenceLevel(ref_level))

# rsa.CONFIG_SetCenterFreq(center_freq)
# rsa.CONFIG_SetReferenceLevel(ref_level)


# Prepare output dir
output_dir = "/mnt/ramdisk2/IF_data_temp"
os.makedirs(output_dir, exist_ok=True)

# Static IFSTREAM config (path, base, suffix, mode)
print("Configuring IF streaming parameters...")
exerr(rsa.IFSTREAM_SetDiskFilePath(c_char_p(output_dir.encode('utf-8'))))
exerr(rsa.IFSTREAM_SetDiskFilenameBase(c_char_p(b"if_capture")))
exerr(rsa.IFSTREAM_SetDiskFilenameSuffix(c_int(1)))  # timestamp suffix
exerr(rsa.IFSTREAM_SetDiskFileMode(c_int(0)))        # formatted mode
print("IF streaming parameters configured.\n")

record_duration_seconds = 30
# durations = np.logspace(np.log10(0.1), np.log10(2), num=10)
durations = np.linspace(0.05, 3.0, num=60)
results = []

for secs in durations:
    print(f"--- Benchmarking file length = {secs:.3f}s ---")
    # compute per-run parameters
    num_files = int(round(record_duration_seconds / secs))
    obs_ms    = int(secs * 1000)

    # clear any leftover files
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))

    # set dynamic IFSTREAM params
    exerr(rsa.IFSTREAM_SetDiskFileLength(c_long(obs_ms)))
    exerr(rsa.IFSTREAM_SetDiskFileCount(c_int(num_files)))

    # run + time acquisition
    
    exerr(rsa.DEVICE_Run())
    start = time.time()
    exerr(rsa.IFSTREAM_SetEnable(c_bool(True)))

    writing = c_bool(True)
    waitTime = obs_ms / 10 / 1000.0
    while writing.value:
        time.sleep(waitTime)
        rsa.IFSTREAM_GetActiveStatus(byref(writing))
    elapsed = time.time() - start
    exerr(rsa.IFSTREAM_SetEnable(c_bool(False)))
    rsa.DEVICE_Stop()
    

    # compute effective acquisition "sample rate" (ms captured per second)
    acq_rate = obs_ms * num_files / elapsed
    results.append((secs, acq_rate))
    print(f"Acquisition time: {elapsed:.2f}s, Sample rate: {acq_rate:.2f} ms/s\n")

# Plot results
xs, ys = zip(*results)
plt.figure()
plt.plot(xs, ys, 'o-')
plt.xscale('log')
plt.xlabel('Individual file length (s)')
plt.ylabel('Effective acquisition rate (ms/s)')
plt.title('IF Stream Benchmark (Sample Rate)')
plt.grid(True)
plt.show()

# report optimal
opt_secs, opt_rate = max(results, key=lambda t: t[1])
print(f"Optimal file length: {opt_secs:.3f}s → {opt_rate:.2f} ms/s")

# cleanup
rsa.DEVICE_Disconnect()
print("Benchmark completed.")