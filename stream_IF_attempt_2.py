
from ctypes import *
from os import chdir
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from rsa_api import *

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

# Constants for device search and info
DEVSRCH_MAX_NUM_DEVICES = 20
DEVSRCH_SERIAL_MAX_STRLEN = 100
DEVSRCH_TYPE_MAX_STRLEN = 20
DEVINFO_MAX_STRLEN = 100

from matplotlib import __version__ as __mversion__
print('Matplotlib Version:', __mversion__)
print('Numpy Version:', np.__version__)

# Load the RSA and USB API shared libraries
RTLD_LAZY = 0x0001
LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
rsa = CDLL("./libRSA_API.so", LAZYLOAD)
usbapi = CDLL("./libcyusb_shared.so", LAZYLOAD)

"""################CLASSES AND FUNCTIONS################"""

def search_connect():
    numFound = c_int(0)
    intArray = c_int * DEVSRCH_MAX_NUM_DEVICES
    deviceIDs = intArray()
    deviceSerial = create_string_buffer(DEVSRCH_SERIAL_MAX_STRLEN)
    deviceType = create_string_buffer(DEVSRCH_TYPE_MAX_STRLEN)
    apiVersion = create_string_buffer(DEVINFO_MAX_STRLEN)

    rsa.DEVICE_GetAPIVersion(apiVersion)
    print('API Version {}'.format(apiVersion.value.decode()))

    (rsa.DEVICE_Search(byref(numFound), deviceIDs,
                                deviceSerial, deviceType))

    if numFound.value < 1:
        # rsa.DEVICE_Reset(c_int(0))
        print('No instruments found. Exiting script.')
        exit()
    elif numFound.value == 1:
        print('One device found.')
        print('Device type: {}'.format(deviceType.value.decode()))
        print('Device serial number: {}'.format(deviceSerial.value.decode()))
        (rsa.DEVICE_Connect(deviceIDs[0]))
    else:
        # corner case
        print('2 or more instruments found. Enumerating instruments, please wait.')
        for inst in deviceIDs:
            rsa.DEVICE_Connect(inst)
            rsa.DEVICE_GetSerialNumber(deviceSerial)
            rsa.DEVICE_GetNomenclature(deviceType)
            print('Device {}'.format(inst))
            print('Device Type: {}'.format(deviceType.value))
            print('Device serial number: {}'.format(deviceSerial.value))
            rsa.DEVICE_Disconnect()
        # note: the API can only currently access one at a time
        selection = 1024
        while (selection > numFound.value - 1) or (selection < 0):
            selection = int(input('Select device between 0 and {}\n> '.format(numFound.value - 1)))
        (rsa.DEVICE_Connect(deviceIDs[selection]))
    rsa.CONFIG_Preset()



"""################IF STREAMING EXAMPLE################"""
def config_if_stream(cf=1e9, refLevel=0, fileDir='IF_data_dump', fileName='if_stream_test', durationMsec=100):
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))
    rsa.IFSTREAM_SetDiskFilePath(c_char_p(fileDir.encode()))
    rsa.IFSTREAM_SetDiskFilenameBase(c_char_p(fileName.encode()))
    # rsa.IFSTREAM_SetDiskFilenameSuffix(c_int(1))
    rsa.IFSTREAM_SetDiskFileLength(c_long(durationMsec))
    rsa.IFSTREAM_SetDiskFileMode(c_int(0))
    rsa.IFSTREAM_SetDiskFileCount(c_int(10))


def if_stream_example():
    print('\n\n########IF Stream Example########')
    search_connect()
    durationMsec = 100
    waitTime = durationMsec / 10 / 1000
    config_if_stream(fileDir='/home/sammy/Downloads/', 
                     fileName='if_stream_test', durationMsec=durationMsec)
    writing = c_bool(True)

    rsa.DEVICE_Run()
    rsa.IFSTREAM_SetEnable(c_bool(True))
    while writing.value:
        sleep(waitTime)
        rsa.IFSTREAM_GetActiveStatus(byref(writing))
    print('Streaming finished.')
    rsa.DEVICE_Stop()
    rsa.DEVICE_Disconnect()





def peak_power_detector(freq, trace):
    peakPower = np.amax(trace)
    peakFreq = freq[np.argmax(trace)]

    return peakPower, peakFreq


def main():
    if_stream_example()

if __name__ == '__main__':
    main()