import rsa_api
import os
import numpy as np

# Directory which contains both libRSA_API.so and libcyusb_shared.so
drivers_path = '.'

# Initialize an RSA device using the API wrapper
rsa = rsa_api.RSA(so_dir=drivers_path)

# Example usage: connect, set up stream and dump IQ data, then disconnect
rsa.DEVICE_SearchAndConnect()
# configure 100 MHz center frequency and 40 MHz bandwidth
rsa.CONFIG_SetCenterFreq(1420e6)
rsa.CONFIG_SetReferenceLevel(0)  # set reference level to -10 dBm
rsa.IQSTREAM_SetAcqBandwidth(40e6)

iq_data, status = rsa.IQSTREAM_Acquire(duration_msec=100, return_status=True)

# ensure dump folder exists and save data
out_dir = '/mnt/ramdisk/IQ_data_dump'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'iq_dump.npy')
np.save(out_path, iq_data)
print(f"IQ dump saved to {out_path}, status: {status}")
print("IQ data first 10 samples:", iq_data[:10])

rsa.DEVICE_Disconnect()

# Print docstrings for any implemented API function
# help(rsa.IQSTREAM_Acquire) # Requires initialized RSA device
# help(rsa_api.RSA.IQSTREAM_Acquire)  # Does not require initalized RSA device


import matplotlib.pyplot as plt

# Prepare time axis for 100 samples
num_samples = 500
t = np.arange(num_samples)

# Extract real, imaginary, and phase
real_part = np.real(iq_data[:num_samples])
imag_part = np.imag(iq_data[:num_samples])
phase = np.angle(iq_data[:num_samples])

# Plot
fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

axs[0].plot(t, real_part, 'o-', label='Real Part')
axs[0].plot(t, imag_part, 'o-', label='Imaginary Part')

axs[1].plot(t, phase)
axs[1].set_ylabel('Phase (rad)')
axs[1].set_xlabel('Sample')
axs[1].set_title('Phase')

plt.tight_layout()
plt.show()