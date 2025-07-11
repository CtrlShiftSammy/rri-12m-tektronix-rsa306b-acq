import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, firwin, decimate

# Bandpass filters

def bandpass(data, lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return lfilter(b, a, data)

def fir_bandpass(data, lowcut, highcut, fs, numtaps=6):
    nyq = 0.5 * fs
    taps = firwin(numtaps, [lowcut / nyq, highcut / nyq], pass_zero=False)
    return lfilter(taps, 1.0, data)

# === High Sampling Rate for GHz Simulation ===
fs_sim = 11.2e9              # sim rate
n_samples = int(fs_sim * 1e-6)  # 1 microsecond of data = 10,000 samples
t = np.arange(n_samples) / fs_sim

# === Frequencies ===
f_signal = 80e6                            # Input RF signal
IF1_target = 2440e6
IF1_band = ((IF1_target - 28e6, IF1_target + 28e6))  # Band around IF1 target
LO1 = f_signal + IF1_target                # Brings RF to IF1 = 2440 MHz
LO2 = 2300e6                               # Second mixer LO
IF2_band = ((140e6 - 28e6, 140e6 + 28e6))  # Band around IF2 target

rf_signal = np.cos(2 * np.pi * f_signal * t)

lo1_signal = np.cos(2 * np.pi * LO1 * t)
mixed_if1 = rf_signal * lo1_signal

filtered_if1 = fir_bandpass(mixed_if1, IF1_band[0], IF1_band[1], fs_sim)

lo2_signal = np.cos(2 * np.pi * LO2 * t)
mixed_if2 = filtered_if1 * lo2_signal

filtered_if2 = fir_bandpass(mixed_if2, IF2_band[0], IF2_band[1], fs_sim)

fs_adc = 112e6
downsample_factor = int(fs_sim / fs_adc)
print(f"Downsample factor: {downsample_factor}")
sampled_adc = filtered_if2[::downsample_factor]
# sampled_adc = decimate(filtered_if2, downsample_factor, ftype='fir', zero_phase=True)
t_adc = t[::downsample_factor]

# sampled_adc = np.zeros(len(mixed_if2) // downsample_factor)
# t_adc = np.zeros(len(mixed_if2) // downsample_factor)

# for i in range(0, len(mixed_if2), downsample_factor):
#     sampled_adc[i // downsample_factor] = mixed_if2[i]
#     t_adc[i // downsample_factor] = t[i]
#     print(f"Sampled ADC[{i // downsample_factor}] = {sampled_adc[i // downsample_factor]}, t_adc[{i // downsample_factor}] = {t_adc[i // downsample_factor]}, i = {i}, t[i] = {t[i]}, mixed_if2[i] = {mixed_if2[i]}")

print(f"Original signal length: {len(rf_signal)}")
print(f"Filtered IF1 length: {len(filtered_if1)}")
print(f"Sampled ADC length: {len(sampled_adc)}")
print(f"Sampled ADC time vector length: {len(t_adc)}")
# t_adc = np.arange(len(sampled_adc)) / fs_adc

# Plot all signals overlaid
plt.figure(figsize=(12, 6))
t_plot = t
t_adc_plot = t_adc

# plt.plot(t_plot, mixed_if1, alpha=0.7, label='Mixed IF1', linewidth=1)
# plt.plot(t_plot, filtered_if1, alpha=0.7, label='Filtered IF1', linewidth=1)
# plt.plot(t_plot, mixed_if2, alpha=0.7, label='Mixed IF2', linewidth=1)
# plt.plot(t_plot, filtered_if2, alpha=0.7, label='Filtered IF2', linewidth=1)
plt.plot(t_adc_plot, sampled_adc, color='purple', linewidth=2, label='Sampled ADC', marker='o', markersize=2)

plt.title("Signal Processing Chain - All Stages Overlaid")
plt.xlabel("Time (µs)")
plt.ylabel("Amplitude")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
