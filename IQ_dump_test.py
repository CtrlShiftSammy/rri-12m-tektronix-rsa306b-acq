import os
import sys
import time
import csv
from datetime import datetime
from ctypes import *
import numpy as np
import warnings

# Suppress specific UserWarning from mlab.specgram
warnings.filterwarnings(
    "ignore",
    message="Only one segment is calculated since parameter NFFT.*",
    category=UserWarning
)

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

# Set up parameters (can be customized)
cf = c_double(1.42e9)
error = rsa.CONFIG_SetCenterFreq(cf)
exerr(error)
recLen = 27000000
length = c_int(recLen)
iqLen = recLen * 2
floatArray = c_float * iqLen
error = rsa.IQBLK_SetIQRecordLength(length)
exerr(error)
rl = c_double(-10)
exerr(rsa.CONFIG_SetReferenceLevel(rl))
iqBW = c_double(40e6)
exerr(rsa.IQBLK_SetIQBandwidth(iqBW))

# Create output directory if not exists
output_dir = "IQ_data_dump"
os.makedirs(output_dir, exist_ok=True)

# Timing statistics
acquire_times = []
write_times = []
device_run_times = []
data_ready_times = []
iqdata_get_times = []
iq_split_times = []

# Function to acquire IQ data from the device
def getIQData():
    t0 = time.time()
    ready = c_bool(False)
    exerr(rsa.DEVICE_Run())
    t1 = time.time()
    device_run_times.append(t1 - t0)

    exerr(rsa.IQBLK_WaitForIQDataReady(1000, byref(ready)))
    t2 = time.time()
    data_ready_times.append(t2 - t1)

    iqData = floatArray()
    if ready:
        outLen = c_int(0)
        exerr(rsa.IQBLK_GetIQData(iqData, byref(outLen), length))
        t3 = time.time()
        iqdata_get_times.append(t3 - t2)
    else:
        print("No data ready, exiting.")
        return None, t0, 0
    t4 = time.time()
    iq_split_times.append(t4 - t3)
    return iqData, t0, t4-t0

print("\nStarting single IQ data acquisition.")

runtime_start = time.time()
try:
    iqData, t_acq, acq_time = getIQData()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    acquire_times.append(acq_time)
    # Save to file
    fname = os.path.join(output_dir, f"IQ_{timestamp}.bin")
    t0_write = time.time()
    np.array(iqData, dtype=np.float32).tofile(fname)
    t1_write = time.time()
    write_times.append(t1_write - t0_write)
    print(f"Saved IQ data to {fname}")
except KeyboardInterrupt:
    print("\nAcquisition interrupted.")
finally:
    runtime_end = time.time()
    print('Stopping device...')
    rsa.DEVICE_Stop()
    print('Device stopped.')
    print('Disconnecting device...')
    rsa.DEVICE_Disconnect()
    print('Device disconnected.')

    # Timing statistics
    if acquire_times:
        print(f"\nAcquisition time: {acquire_times[0]:.6f} s")
        actual_sample_rate = recLen / acquire_times[0]
        print(f"Actual sample rate: {actual_sample_rate:.2f} samples/s")
    if write_times:
        print(f"Write time: {write_times[0]:.6f} s")

    print(f"Total runtime: {runtime_end - runtime_start:.2f} seconds")
    if acquire_times:
        print(f"Percentage of runtime spent acquiring data: {acquire_times[0] / (runtime_end - runtime_start) * 100:.2f}%")

    if device_run_times:
        print(f"Device run time: {device_run_times[0]:.6f} s")
    if data_ready_times:
        print(f"Data ready wait time: {data_ready_times[0]:.6f} s")
    if iqdata_get_times:
        print(f"IQ data get time: {iqdata_get_times[0]:.6f} s")
    if iq_split_times:
        print(f"IQ split time: {iq_split_times[0]:.6f} s")

    