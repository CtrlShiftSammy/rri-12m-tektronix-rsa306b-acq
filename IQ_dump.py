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
recLen = 1000
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
    t4 = time.time()
    iq_split_times.append(t4 - t3)
    return iqData, t0, t4-t0

# Writer thread function for batches from a queue
def writer_thread(data_queue):
    while True:
        batch = data_queue.get()
        if batch is None:
            break
        t0 = time.time()
        for iqData, timestamp in batch:
            fname = os.path.join(output_dir, f"IQ_{timestamp}.bin")
            np.array(iqData, dtype=np.float32).tofile(fname)
        t1 = time.time()
        write_times.append(t1 - t0)
        data_queue.task_done()

print("\nStarting IQ data acquisition. Press Ctrl+C to stop.")
runtime_start = time.time()

batch_size = 50
batch = []
timestamp_list = []  # Store timestamps for interval analysis

data_queue = queue.Queue()
writer = threading.Thread(target=writer_thread, args=(data_queue,))
writer.start()

try:
    while True:
        iqData, t_acq, acq_time = getIQData()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        acquire_times.append(acq_time)
        batch.append((iqData, timestamp))
        timestamp_list.append(timestamp)
        if len(batch) >= batch_size:
            data_queue.put(batch)
            batch = []
except KeyboardInterrupt:
    print("\nStopping acquisition...")
    runtime_end = time.time()
    # Write any remaining data in batch
    if batch:
        print(f"Writing remaining {len(batch)} records to queue...")
        data_queue.put(batch)
    print("Acquisition stopped.")
finally:
    # Signal writer thread to exit and wait for it
    data_queue.put(None)
    print("Waiting for writer thread to finish...")
    writer.join()
    print("Writer thread finished.")
    print('Stopping device...')
    rsa.DEVICE_Stop()
    print('Device stopped.')
    print('Disconnecting device...')
    rsa.DEVICE_Disconnect()
    print('Device disconnected.')

    # Timing statistics
    if acquire_times:
        print(f"\nAcquisition calls: {len(acquire_times)}")
        print(f"  Avg acquisition time: {np.mean(acquire_times):.6f} s")
        print(f"  Stddev acquisition time: {np.std(acquire_times):.6f} s")
    if write_times:
        print(f"Write calls: {len(write_times)}")
        print(f"  Avg write time: {np.mean(write_times):.6f} s")
        print(f"  Stddev write time: {np.std(write_times):.6f} s")

    print(f"Total runtime: {runtime_end - runtime_start:.2f} seconds")
    total_acquire_time = sum(acquire_times)
    print(f"Percentage of runtime spent acquiring data: {total_acquire_time / (runtime_end - runtime_start) * 100:.2f}%")

    print(f"Device run times: {len(device_run_times)} calls, Avg: {np.mean(device_run_times):.6f} s, Stddev: {np.std(device_run_times):.6f} s")
    print(f"Data ready wait times: {len(data_ready_times)} calls, Avg: {np.mean(data_ready_times):.6f} s, Stddev: {np.std(data_ready_times):.6f} s")
    print(f"IQ data get times: {len(iqdata_get_times)} calls, Avg: {np.mean(iqdata_get_times):.6f} s, Stddev: {np.std(iqdata_get_times):.6f} s")
    print(f"IQ split times: {len(iq_split_times)} calls, Avg: {np.mean(iq_split_times):.6f} s, Stddev: {np.std(iq_split_times):.6f} s")

    # --- Timestamp interval analysis ---
    if len(timestamp_list) > 1:
        # Convert string timestamps to datetime objects
        dt_list = [datetime.strptime(ts, "%Y%m%d_%H%M%S_%f") for ts in timestamp_list]
        intervals = [(dt_list[i+1] - dt_list[i]).total_seconds() for i in range(len(dt_list)-1)]
        print("\nTime intervals between consecutive file timestamps:")
        print(f"  Count: {len(intervals)}")
        print(f"  Mean:   {np.mean(intervals):.6f} s")
        print(f"  Stddev: {np.std(intervals):.6f} s")
        print(f"  Max:    {np.max(intervals):.6f} s")
        print(f"  Min:    {np.min(intervals):.6f} s")
    else:
        print("\nNot enough timestamps for interval analysis.")
