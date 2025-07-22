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
import argparse

# Load RSA API libraries
RTLD_LAZY = 0x0001
LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
rsa = CDLL("./libRSA_API.so", LAZYLOAD)
usbapi = CDLL("./libcyusb_shared.so", LAZYLOAD)

# Constants for device search
DEVSRCH_MAX_NUM_DEVICES    = 20
DEVSRCH_SERIAL_MAX_STRLEN  = 100
DEVSRCH_TYPE_MAX_STRLEN    = 20

def check_error(err):
    if err != 0:
        rsa.DEVICE_GetErrorString.restype = c_char_p
        msg = rsa.DEVICE_GetErrorString(err)
        raise Exception(f"RSA API Error {err}: {msg.decode()}")

def search_and_connect_device():
    print("Searching for RSA devices...")
    numDevices = c_int()
    deviceIDs = (c_int * DEVSRCH_MAX_NUM_DEVICES)()
    deviceSNs  = ((c_char * DEVSRCH_SERIAL_MAX_STRLEN) * DEVSRCH_MAX_NUM_DEVICES)()
    deviceTypes= ((c_char * DEVSRCH_TYPE_MAX_STRLEN) * DEVSRCH_MAX_NUM_DEVICES)()
    err = rsa.DEVICE_Search(byref(numDevices), deviceIDs, deviceSNs, deviceTypes)
    check_error(err)
    if numDevices.value == 0:
        print("No RSA devices found. Proceeding in playback mode.")
        return False
    err = rsa.DEVICE_Connect(deviceIDs[0])
    check_error(err)
    print("Connected to RSA device")
    return True

def open_r3f_file(filename, deterministic=True):
    print(f"Opening R3F file: {filename}")
    filename_w   = c_wchar_p(filename)
    startPct     = c_int(0)
    stopPct      = c_int(100)
    skipTime     = c_double(0.0)
    loopAtEnd    = c_bool(False)
    emuRealTime  = c_bool(not deterministic)
    err = rsa.PLAYBACK_OpenDiskFile(filename_w,
                                     startPct,
                                     stopPct,
                                     skipTime,
                                     loopAtEnd,
                                     emuRealTime)
    check_error(err)
    print("R3F file opened for playback")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('r3f_file', help='Path to input .r3f file')
    parser.add_argument('--file-duration', type=float, default=1.0,
                        help='Length of each iq file (sec)')
    parser.add_argument('--output-temp', default='/mnt/ramdisk/IQ_data_temp',
                        help='Temporary RAM-disk dir')
    parser.add_argument('--output-final', default='IQ_data_dump',
                        help='Final storage dir')
    parser.add_argument('--direct', action='store_true',
                        help='Stream directly into final dir, skip temp')
    args = parser.parse_args()

    os.makedirs(args.output_temp, exist_ok=True)
    os.makedirs(args.output_final, exist_ok=True)
    # choose where to stream
    stream_dir = args.output_final if args.direct else args.output_temp

    # open playback device or file
    # search_and_connect_device()
    open_r3f_file(args.r3f_file, deterministic=True)

    # preset & RF config
    rsa.CONFIG_Preset()
    cf    = c_double(1420e6)
    ref   = c_double(-10.0)
    acq_bw= c_double(40e6)
    print(f"Setting Center Frequency: {cf.value} Hz")
    rsa.CONFIG_SetCenterFreq(cf)
    print(f"Setting Reference Level: {ref.value} dBm")
    rsa.CONFIG_SetReferenceLevel(ref)
    print(f"Setting Acquisition Bandwidth: {acq_bw.value} Hz")
    rsa.IQSTREAM_SetAcqBandwidth(acq_bw)

    # IQ stream setup
    print("Configuring IQ streaming parameters...")
    rsa.IQSTREAM_SetOutputConfiguration(c_int(3), c_int(2))
    base = os.path.join(stream_dir, 'iq_capture')
    rsa.IQSTREAM_SetDiskFilenameBase(c_char_p(base.encode()))
    rsa.IQSTREAM_SetDiskFilenameSuffix(c_int(1))
    rsa.IQSTREAM_SetDiskFileLength(c_long(int(args.file_duration*1000)))
    print("Starting IQ streaming...")
    # start streaming
    check_error(rsa.DEVICE_Run())
    check_error(rsa.IQSTREAM_Start())

    complete = c_bool(False)
    writing = c_bool(True)
    playback_done = c_bool(False)
    start_time = time.time()

    while not complete.value and writing.value and not playback_done:
        time.sleep(0.001)
        status = rsa.IQSTREAM_GetDiskFileWriteStatus(byref(complete), byref(writing))

        if status != 0:
            print(f"Error: status = {status}")
            break
        status = rsa.PLAYBACK_GetReplayComplete(byref(playback_done))
        if status != 0:
            print(f"Error checking playback status: {status}")
            break
        sys.stdout.write(f"\rIQ streaming active: {writing.value}, time elapsed: {time.time() - start_time:.2f} seconds")
        sys.stdout.flush()
    print()

    check_error(rsa.IQSTREAM_Stop())
    check_error(rsa.DEVICE_Stop())
    check_error(rsa.DEVICE_Disconnect())

    if not args.direct:
        for f in os.listdir(args.output_temp):
            shutil.move(os.path.join(args.output_temp, f),
                        os.path.join(args.output_final, f))
        print("Streaming complete, files moved.")
    else:
        print("Streaming complete, files in final directory.")

if __name__ == '__main__':
    main()
