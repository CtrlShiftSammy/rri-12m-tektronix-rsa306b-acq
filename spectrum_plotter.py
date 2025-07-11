import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib.widgets import Button
import time
from pylab import *
from time import sleep
from ctypes import *
import warnings
import statistics


do_timing_analysis = True

# Suppress specific UserWarning from mlab.specgram
warnings.filterwarnings(
    "ignore",
    message="Only one segment is calculated since parameter NFFT.*",
    category=UserWarning
)

# Load the RSA and USB API shared libraries
RTLD_LAZY = 0x0001
LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
rsa = CDLL("./libRSA_API.so",LAZYLOAD)
usbapi = CDLL("./libcyusb_shared.so",LAZYLOAD)

# Helper function to get error string from device
def GetErrorString(error):
    rsa.DEVICE_GetErrorString.restype = c_char_p
    errorString = rsa.DEVICE_GetErrorString(error)
    return errorString

# Helper function to exit on error
def exerr(error):
    if error != 0:
        sys.exit(GetErrorString(error))
        

error = 0

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

print('')
print('Searching for devices...')
numDevices = c_int()
deviceIDs = (c_int * DEVSRCH_MAX_NUM_DEVICES)() 
deviceSNs = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_SERIAL_MAX_STRLEN)()
deviceTypes = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_TYPE_MAX_STRLEN)()
# Search for connected devices
error = rsa.DEVICE_Search(byref(numDevices), deviceIDs, deviceSNs, deviceTypes)
foundDevices = {id: (deviceSNs[id].value, deviceTypes[id].value) for id in deviceIDs}
exerr(error)

print('Found ' + str(numDevices.value) + ' device(s):')
print(foundDevices)

# Exit if no devices found
if numDevices == 0:
    sys.exit('No devices found')

print('')
# Connect to the first found device
error = rsa.DEVICE_Connect(list(foundDevices.keys())[0])
exerr(error)

# Get and print serial number
sn = (c_char * DEVINFO_MAX_STRLEN)()
error = rsa.DEVICE_GetSerialNumber(sn)
exerr(error)
print('Serial #: ' + str(sn.value))

# Set center frequency (CF)
cf = c_double(1.42e9) 
print('')
print('Setting CF to ' + str(cf.value) + '...')
error = rsa.CONFIG_SetCenterFreq(cf)
exerr(error)
print('done.')

# Set IQ record length
recLen = 1000
length = c_int(recLen)
iqLen = recLen * 2
floatArray = c_float * iqLen
print('')
print('Setting IQRecLength to ' + str(length.value) + '...')
error = rsa.IQBLK_SetIQRecordLength(length)
exerr(error)

# Set reference level
rl = c_double(-10)
print('')
print('Setting RefLevel to ' + str(rl.value) + '...')
exerr(rsa.CONFIG_SetReferenceLevel(rl))

# Set IQ bandwidth
iqBW = c_double(40e6)
print('')
print('Setting IQ Bandwidth to ' + str(iqBW.value) + '...')
exerr(rsa.IQBLK_SetIQBandwidth(iqBW))

print('')
# Set trigger position percent
trigPos = c_double(50.0)
print('Setting TrigPos to ' + str(trigPos.value) + '...')
exerr(rsa.TRIG_SetTriggerPositionPercent(trigPos))

print('')
# Set IF power trigger level
trigLev = c_double(-36.0)
print('Setting TrigLev to ' + str(trigLev.value) + '...')
exerr(rsa.TRIG_SetIFPowerTriggerLevel(trigLev))

print('')
# Set trigger transition
trigTrans = c_int(1)
print('Setting IQ Bandwidth to ' + str(trigTrans.value) + '...')
exerr(rsa.TRIG_SetTriggerTransition(trigTrans))

print('')
# Set trigger source
trigSource = c_int(1)
print('Setting IQ Bandwidth to ' + str(trigSource.value) + '...')
exerr(rsa.TRIG_SetTriggerSource(trigSource))

###############################################

# Timing statistics storage
update_times = []
iq_times = []
iqdata_device_times = []
iqdata_specgram_times = []
iqdata_fft_times = []
device_run_times = []
data_ready_times = []
iqdata_fetch_times = []

# Function to acquire IQ data from the device
def getIQData():
    if do_timing_analysis:
        t0 = time.time()
    ready = c_bool(False)
    t_run_0 = time.time()
    exerr(rsa.DEVICE_Run())
    t_run_1 = time.time()
    device_run_times.append(t_run_1 - t0)

    # Wait for IQ data to be ready
    exerr(rsa.IQBLK_WaitForIQDataReady(10000, byref(ready)))
    t_ready = time.time()
    data_ready_times.append(t_ready - t_run_1)

    iqData = floatArray()
    if ready:
        outLen = c_int(0)
        # Retrieve IQ data
        exerr(rsa.IQBLK_GetIQData(iqData, byref(outLen), length))
        t_fetch = time.time()
        # iqdata_fetch_times.append(t_fetch - t_ready)
        iData = [0] * recLen
        qData = [0] * recLen
        for i in range(0,recLen):
            iData[i] = iqData[i*2]
            qData[i] = iqData[i*2+1]
    else:
        print("No IQ data ready AAAAAAAAA HELP")
    if do_timing_analysis:
        t1 = time.time()
        iqdata_fetch_times.append(t1 - t_ready)
    z = [(x + 1j*y) for x, y in zip(iData,qData)]
    cf = c_double(0)
    exerr(rsa.CONFIG_GetCenterFreq(byref(cf)))
    # Compute spectrogram for frequency axis
    spec2 = mlab.specgram(z, NFFT=recLen, Fs=56e6)
    if do_timing_analysis:
        t2 = time.time()
    f = [(x + cf)/1e6 for x in spec2[1]]
    # Compute FFT for spectrum
    spec = np.fft.fft(z, recLen)
    r = [x * 1 for x in abs(spec)]
    r = np.fft.fftshift(r)
    if do_timing_analysis:
        t3 = time.time()
        iqdata_device_times.append(t1 - t0)
        iqdata_specgram_times.append(t2 - t1)
        iqdata_fft_times.append(t3 - t2)
    return [iData, qData, z, r, f]

# Animation initialization function
def init():
    #line.set_data([], [])
    #line2.set_data([], [])
    #line3.set_data([], [])
    return line, line2, line3,

# Animation update function, called for each frame
def update(i):
    t0 = time.time()
    x = np.linspace(0, recLen, recLen)
    t1 = time.time()
    iq = getIQData()
    t2 = time.time()
    f = iq[4]
    i = iq[0]
    q = iq[1]
        
    r = iq[3]
    #print iq[4][1][0:10]
    line.set_data(x, i)
    line2.set_data(x, q)
    ax2.set_xlim(f[0], f[len(f) - 1])
    line3.set_data(f, r)
        
    ax2.set_xticks( [ 
        round(f[int(8.0/56*len(f))]), 
        round(f[int(18.0/56*len(f))]), 
        f[len(f)//2], 
        round(f[int(38.0/56*len(f))]), 
        round(f[int(48.0/56*len(f))]) 
    ] )
    t3 = time.time()
    if do_timing_analysis:
        update_times.append(t3 - t0)
        iq_times.append(t2 - t1)
    #ax2.relim()
    return line, line2, line3,
        
# Set up the figure and axes for plotting
fig = figure()

ax2 = fig.add_subplot(211)
ax2.set_xlim(0, recLen)
ax2.set_ylim(0, 4e-1)
ax2.set_yscale('symlog')

xlabel('RefLevel = ' + str(rl.value) + ' dBm')
title('IQBandwith = ' + str(iqBW.value / 1e6) + ' MHz')
ax = fig.add_subplot(212)
ax.set_xlim(0, recLen)
ax.set_ylim(-15e-3, 15e-3)

xlabel('CF = ' + str(cf.value / 1e6) + ' MHz')
# Create empty lines for animation
line, = ax.plot([], [], lw=2)
line2, = ax.plot([], [], lw=2)
line3, = ax2.plot([], [], lw=2)

# Button callback to increase center frequency
def next(event):
    rsa.DEVICE_Stop()
    cf = c_double(0)
    rsa.CONFIG_GetCenterFreq(byref(cf))
    cf = c_double(cf.value + 1e6)
    rsa.CONFIG_SetCenterFreq(cf)
    rsa.DEVICE_Run()
    ax.set_xlabel('CF = ' + str(cf.value / 1e6) + ' MHz')
        
# Button callback to decrease center frequency
def prev(event):
    rsa.DEVICE_Stop()
    cf = c_double(0)
    rsa.CONFIG_GetCenterFreq(byref(cf))
    cf = c_double(cf.value - 1e6)
    rsa.CONFIG_SetCenterFreq(cf)
    rsa.DEVICE_Run()
    ax.set_xlabel('CF = ' + str(cf.value / 1e6) + ' MHz')
        
# Button callback to increase reference level
def up(event):
    rsa.DEVICE_Stop()
    rl = c_double(0)
    rsa.CONFIG_GetReferenceLevel(byref(rl))
    rl = c_double(rl.value + 5.0)
    rsa.CONFIG_SetReferenceLevel(rl)
    rsa.DEVICE_Run()
    ax2.set_xlabel('RefLevel = ' + str(rl.value) + ' dBm')
        
# Button callback to decrease reference level
def down(event):
    rsa.DEVICE_Stop()
    rl = c_double(0)
    rsa.CONFIG_GetReferenceLevel(byref(rl))
    rl = c_double(rl.value - 5.0)
    rsa.CONFIG_SetReferenceLevel(rl)
    rsa.DEVICE_Run()
    ax2.set_xlabel('RefLevel = ' + str(rl.value) + ' dBm')

# Button callback to toggle trigger mode
def trigger(event):
    rsa.DEVICE_Stop()
    trigMode = c_int(True)
    rsa.TRIG_GetTriggerMode(byref(trigMode))
    trigMode = c_int(not trigMode.value)
    rsa.TRIG_SetTriggerMode(trigMode)
    rsa.DEVICE_Run()
        
# Button callback to double IQ bandwidth
def more(event):
    rsa.DEVICE_Stop()
    iqBQ = c_double(0)
    rsa.IQBLK_GetIQBandwidth(byref(iqBQ))
    iqBQ = c_double(iqBQ.value * 2)
    rsa.IQBLK_SetIQBandwidth(iqBQ)
    rsa.DEVICE_Run()
    ax2.set_title('IQBandwith = ' + str(iqBQ.value / 1e6) + ' MHz')

# Button callback to halve IQ bandwidth
def less(event):
    rsa.DEVICE_Stop()
    iqBQ = c_double(0)
    rsa.IQBLK_GetIQBandwidth(byref(iqBQ))
    iqBQ = c_double(iqBQ.value / 2)
    rsa.IQBLK_SetIQBandwidth(iqBQ)
    rsa.DEVICE_Run()
    ax2.set_title('IQBandwith = ' + str(iqBQ.value / 1e6) + ' MHz')
        
# Create and place control buttons on the figure
axbuttonNext = plt.axes([0.91, 0.02, 0.070, 0.05])
bnext = Button(axbuttonNext, 'Next')
bnext.on_clicked(next)

axbuttonPrev = plt.axes([0.02, 0.02, 0.070, 0.05])
bprev = Button(axbuttonPrev, 'Prev')
bprev.on_clicked(prev)

axbuttonUp = plt.axes([0.02, 0.92, 0.12, 0.05])
bup = Button(axbuttonUp, 'Ref Up')
bup.on_clicked(up)

axbuttonDown = plt.axes([0.145, 0.92, 0.12, 0.05])
bdown = Button(axbuttonDown, 'Ref Down')
bdown.on_clicked(down)

axbuttonTrigger = plt.axes([0.85, 0.92, 0.12, 0.05])
btrigger = Button(axbuttonTrigger, 'Trigger')
btrigger.on_clicked(trigger)

axbuttonMore = plt.axes([0.81, 0.02, 0.070, 0.05])
bmore = Button(axbuttonMore, 'More')
bmore.on_clicked(more)

axbuttonLess = plt.axes([0.12, 0.02, 0.070, 0.05])
bless = Button(axbuttonLess, 'Less')
bless.on_clicked(less)

# Set up animation for live updating plots
ani = animation.FuncAnimation(fig, update, init_func=init, frames=200, interval=100, blit=True)
show()


print('Stopping device...')
rsa.DEVICE_Stop()
print('Disconnecting device...')
rsa.DEVICE_Disconnect()

# Print timing statistics
if do_timing_analysis:
    if update_times:
        print("\nTiming statistics:")
        print(f"Update calls: {len(update_times)}")
        print(f"  Avg update time: {np.mean(update_times):.6f} s")
        print(f"  Stddev update time: {np.std(update_times):.6f} s")
    else:
        print("No update timing data collected.")

    if iq_times:
        print(f"IQ fetch calls: {len(iq_times)}")
        print(f"  Avg IQ fetch time: {np.mean(iq_times):.6f} s")
        print(f"  Stddev IQ fetch time: {np.std(iq_times):.6f} s")
    else:
        print("No IQ fetch timing data collected.")

    if update_times and iq_times:
        fraction = statistics.mean(iq_times) / statistics.mean(update_times)
        print(f"Percentage of update time spent fetching IQ data: {fraction * 100:.2f}%")

    # Detailed getIQData analysis
    if iqdata_device_times:
        print("\ngetIQData breakdown (averages and stddevs):")
        print(f"  Device fetch (I/Q arrays): {np.mean(iqdata_device_times):.6f} s avg, {np.std(iqdata_device_times):.6f} s stddev")
        print(f"  Spectrogram calculation:   {np.mean(iqdata_specgram_times):.6f} s avg, {np.std(iqdata_specgram_times):.6f} s stddev")
        print(f"  FFT calculation:           {np.mean(iqdata_fft_times):.6f} s avg, {np.std(iqdata_fft_times):.6f} s stddev")
    if device_run_times:
        print(f"  Device run time:           {np.mean(device_run_times):.6f} s avg, {np.std(device_run_times):.6f} s stddev")
    if data_ready_times:
        print(f"  Data ready wait time:      {np.mean(data_ready_times):.6f} s avg, {np.std(data_ready_times):.6f} s stddev")
    if iqdata_fetch_times:
        print(f"  IQ data fetch time:        {np.mean(iqdata_fetch_times):.6f} s avg, {np.std(iqdata_fetch_times):.6f} s stddev")



