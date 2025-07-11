import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from ctypes import *
import argparse

# Constants for device search and info
DEVSRCH_MAX_NUM_DEVICES = 20
DEVSRCH_SERIAL_MAX_STRLEN = 100
DEVSRCH_TYPE_MAX_STRLEN = 20
DEVINFO_MAX_STRLEN = 100

class RSA_API_Converter:
    def __init__(self):
        self.rsa = None
        self.device_connected = False
        self.load_library()

    def load_library(self):
        """Load RSA_API library"""
        # Load the RSA and USB API shared libraries
        RTLD_LAZY = 0x0001
        LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
        self.rsa = CDLL("./libRSA_API.so", LAZYLOAD)
        self.usbapi = CDLL("./libcyusb_shared.so", LAZYLOAD)

    def check_error(self, error_code):
        """Check for API errors and get error string"""
        if error_code != 0:
            # Get error string
            self.rsa.DEVICE_GetErrorString.restype = c_char_p
            error_msg = self.rsa.DEVICE_GetErrorString(error_code)
            raise Exception(f"RSA API Error {error_code}: {error_msg.decode()}")

    def search_and_connect_device(self):
        """Search for and connect to first available device"""
        print("Searching for RSA devices...")

        numDevices = c_int()
        deviceIDs = (c_int * DEVSRCH_MAX_NUM_DEVICES)()
        deviceSNs = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_SERIAL_MAX_STRLEN)()
        deviceTypes = ((c_char * DEVSRCH_MAX_NUM_DEVICES) * DEVSRCH_TYPE_MAX_STRLEN)()

        # Search for devices
        error = self.rsa.DEVICE_Search(byref(numDevices), deviceIDs, deviceSNs, deviceTypes)
        self.check_error(error)

        if numDevices.value == 0:
            print("No RSA devices found. Using playback mode with R3F file.")
            return False

        print(f"Found {numDevices.value} device(s)")

        # Connect to first device
        error = self.rsa.DEVICE_Connect(deviceIDs[0])
        self.check_error(error)

        self.device_connected = True
        print("Connected to RSA device")
        return True

    def open_r3f_file(self, filename, deterministic=True):
        """Open R3F file for playback"""
        print(f"Opening R3F file: {filename}")

        # Convert filename to wide string (wchar_t*)
        filename_w = c_wchar_p(filename)

        # PLAYBACK_OpenDiskFile parameters
        startPercentage = c_int(0)      # Start from beginning
        stopPercentage = c_int(100)     # Play to end
        skipTime = c_double(0.0)        # Don't skip any data
        loopAtEnd = c_bool(False)       # Don't loop
        emulateRealTime = c_bool(not deterministic)  # FALSE for deterministic playback

        error = self.rsa.PLAYBACK_OpenDiskFile(
            filename_w, 
            startPercentage, 
            stopPercentage, 
            skipTime, 
            loopAtEnd, 
            emulateRealTime
        )
        self.check_error(error)
        print("R3F file opened successfully for deterministic playback")

    def configure_iq_acquisition(self):
        """Configure IQ acquisition parameters"""
        print("Configuring IQ acquisition...")

        # Set IQ bandwidth to maximum for full data capture
        max_bandwidth = c_double()
        error = self.rsa.IQBLK_GetMaxIQBandwidth(byref(max_bandwidth))
        self.check_error(error)

        # Set bandwidth
        error = self.rsa.IQBLK_SetIQBandwidth(max_bandwidth)
        self.check_error(error)

        # Get maximum record length
        max_samples = c_int()
        error = self.rsa.IQBLK_GetMaxIQRecordLength(byref(max_samples))
        self.check_error(error)

        # Set record length to capture significant data
        # record_length = min(max_samples.value, 1000000)  # 1M samples max for memory
        record_length = max_samples.value  # Use maximum available length
        error = self.rsa.IQBLK_SetIQRecordLength(c_int(record_length))
        self.check_error(error)

        print(f"IQ acquisition configured: BW={max_bandwidth.value/1e6:.1f} MHz, Length={record_length} samples")
        return record_length

    def start_acquisition(self):
        """Start the device/playback"""
        print("Starting acquisition...")
        error = self.rsa.DEVICE_Run()
        self.check_error(error)

    def acquire_iq_data(self, record_length):
        """Acquire IQ data from the device/file"""
        print("Acquiring IQ data...")

        # Trigger IQ acquisition
        error = self.rsa.IQBLK_AcquireIQData()
        self.check_error(error)

        # Wait for data to be ready
        timeout_ms = c_int(30000)  # 30 second timeout
        ready = c_bool()
        print("Waiting for IQ data samples to be ready...")
        error = self.rsa.IQBLK_WaitForIQDataReady(timeout_ms, byref(ready))
        self.check_error(error)

        if not ready.value:
            raise Exception("Timeout waiting for IQ data")

        # Get IQ data in deinterleaved format (separate I and Q arrays)
        i_data = (c_float * record_length)()
        q_data = (c_float * record_length)()
        out_length = c_int()
        req_length = c_int(record_length)

        error = self.rsa.IQBLK_GetIQDataDeinterleaved(
            i_data, q_data, byref(out_length), req_length
        )
        self.check_error(error)

        # Convert to numpy arrays
        i_array = np.array([i_data[i] for i in range(out_length.value)])
        q_array = np.array([q_data[i] for i in range(out_length.value)])

        print(f"Successfully acquired {out_length.value} IQ samples")
        return i_array, q_array

    def get_acquisition_info(self):
        """Get acquisition timing and sample rate info"""
        sample_rate = c_double()
        error = self.rsa.IQBLK_GetIQSampleRate(byref(sample_rate))
        self.check_error(error)
        return sample_rate.value

    def stop_and_disconnect(self):
        """Stop acquisition and disconnect"""
        print("Stopping acquisition and disconnecting...")
        if self.device_connected:
            self.rsa.DEVICE_Stop()
            self.rsa.DEVICE_Disconnect()

    def save_iq_to_csv(self, i_data, q_data, filename, sample_rate):
        """Save IQ data to CSV file"""
        print(f"Saving IQ data to {filename}")

        # Create time array
        time_array = np.arange(len(i_data)) / sample_rate

        # Calculate magnitude and phase
        magnitude = np.sqrt(i_data**2 + q_data**2)
        phase = np.arctan2(q_data, i_data) * 180 / np.pi

        # Save to CSV
        data = np.column_stack((time_array, i_data, q_data, magnitude, phase))
        header = "Time(s),I,Q,Magnitude,Phase(deg)"
        np.savetxt(filename, data, delimiter=',', header=header, comments='')
        print(f"IQ data saved to {filename}")

    def plot_iq_data(self, i_data, q_data, sample_rate, output_file=None):
        print("Creating IQ time series, phase, and FFT plots...")
        # Create time array (show first 10000 samples for clarity)
        max_samples = min(10000, len(i_data))
        time_us = np.arange(max_samples) / sample_rate * 1e6  # Convert to microseconds

        # Create subplots: time series, phase, and FFT
        fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=False)

        # --- Top subplot: I/Q time series ---
        axs[0].plot(time_us, i_data[:max_samples], 'b-', label='I (Real)', alpha=0.8, linewidth=1)
        axs[0].plot(time_us, q_data[:max_samples], 'r-', label='Q (Imaginary)', alpha=0.8, linewidth=1)
        axs[0].set_ylabel('Amplitude (V)')
        axs[0].set_title('IQ Data Time Series')
        axs[0].legend()
        axs[0].grid(True, alpha=0.3)

        # Compute phase in degrees for the first N samples
        phase_deg = np.arctan2(q_data[:max_samples], i_data[:max_samples]) * 180 / np.pi

        # --- Middle subplot: Phase vs Time ---
        axs[1].plot(time_us, phase_deg, 'm-', label='Phase', alpha=0.8, linewidth=1)
        axs[1].set_xlabel('Time (μs)')
        axs[1].set_ylabel('Phase (deg)')
        axs[1].set_title('IQ Phase vs Time')
        axs[1].set_ylim(-180, 180)
        axs[1].grid(True, alpha=0.3)

        # --- Bottom subplot: FFT magnitude (shifted by center frequency) ---
        # Get center frequency
        cf = c_double()
        self.rsa.CONFIG_GetCenterFreq(byref(cf))
        cf_hz = cf.value
        # Compute FFT of windowed IQ data and shift
        window = i_data[:max_samples] + 1j * q_data[:max_samples]
        spec = np.fft.fft(window)
        spec_shift = np.fft.fftshift(spec)
        freq = np.fft.fftfreq(max_samples, d=1/sample_rate)
        freq_shift = np.fft.fftshift(freq) + cf_hz
        # Plot FFT
        axs[2].plot(freq_shift/1e6, np.abs(spec_shift), 'g-', linewidth=1)
        axs[2].set_xlabel('Frequency (MHz)')
        axs[2].set_ylabel('Magnitude')
        axs[2].set_title('FFT of IQ Data (Shifted by Center Freq)')
        axs[2].grid(True, alpha=0.3)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {output_file}")

        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Convert R3F file to IQ data using deterministic playback')
    parser.add_argument('r3f_file', help='Path to the .r3f file')
    parser.add_argument('--output-csv', help='Output CSV filename for IQ data')
    parser.add_argument('--output-plot', help='Output plot filename (PNG)')
    parser.add_argument('--max-samples', type=int, help='Maximum number of samples to process')

    args = parser.parse_args()

    if not os.path.exists(args.r3f_file):
        print(f"Error: R3F file '{args.r3f_file}' not found")
        sys.exit(1)

    converter = RSA_API_Converter()

    try:

        # Open R3F file for deterministic playback
        converter.open_r3f_file(args.r3f_file, deterministic=True)

        # Configure IQ acquisition
        record_length = converter.configure_iq_acquisition()

        if args.max_samples and args.max_samples < record_length:
            # Update record length if user specified smaller value
            error = converter.rsa.IQBLK_SetIQRecordLength(c_int(args.max_samples))
            converter.check_error(error)
            record_length = args.max_samples

        # Start acquisition/playback
        converter.start_acquisition()

        # Acquire IQ data
        i_data, q_data = converter.acquire_iq_data(record_length)

        # Get sample rate for time axis
        sample_rate = converter.get_acquisition_info()

        print(f"\nAcquisition completed successfully!")
        print(f"Sample rate: {sample_rate/1e6:.3f} MSa/s")
        print(f"Total samples: {len(i_data)}")
        print(f"Duration: {len(i_data)/sample_rate*1000:.3f} ms")

        # Save to CSV if requested
        if args.output_csv:
            converter.save_iq_to_csv(i_data, q_data, args.output_csv, sample_rate)

        # Create plot
        converter.plot_iq_data(i_data, q_data, sample_rate, args.output_plot)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        converter.stop_and_disconnect()

if __name__ == "__main__":
    main()
