#!/usr/bin/env python3
# fft_r3a.py - Process .r3a files to generate waterfall and average spectrum plots
# Based on the Streaming IF Sample Data File Format documentation

import os
import glob
import struct
import numpy as np
import matplotlib.pyplot as plt
import csv

def read_r3a_files(input_dir):
    """
    Read and concatenate samples from all .r3a files in the input directory.
    
    Parameters:
    -----------
    input_dir : str
        Path to the directory containing .r3a files to process
        
    Returns:
    --------
    numpy.ndarray
        Array of concatenated samples from all .r3a files
    """
    file_paths = sorted(glob.glob(os.path.join(input_dir, '*.r3a')))
    all_samples = []
    for fp in file_paths:
        with open(fp, 'rb') as f:
            data = f.read()
            num = len(data) // 2
            samples = struct.unpack(f'<{num}h', data)
            all_samples.extend(samples)
    return np.array(all_samples, dtype=np.float32)

def main():
    """Main processing function for .r3a files"""
    IF_DATA_DIR = "IF_data_dump"
    OUTPUT_DIR = "IF_spectra_dump"
    window_size = 1024
    Fs = 112e6
    tuning_freq_MHz = 102  # shift by tuning frequency

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Read and process all .r3a files
    data = read_r3a_files(IF_DATA_DIR)
    num_windows = len(data) // window_size
    data = data[:num_windows * window_size]

    waterfall = []

    freqs = np.fft.fftfreq(window_size, d=1/Fs)[:window_size//2] / 1e6 + tuning_freq_MHz - Fs / 4e6

    for i in range(num_windows):
        segment = data[i*window_size:(i+1)*window_size]
        spec = np.fft.fft(segment)
        power = np.abs(spec[:window_size//2])**2
        waterfall.append(power)

        # Dump this window’s spectrum to CSV
        csv_path = os.path.join(OUTPUT_DIR, f'window_{i:05d}.csv')
        with open(csv_path, 'w', newline='') as cf:
            writer = csv.writer(cf)
            writer.writerow(['Frequency_MHz', 'Power_dB'])
            for fr, p in zip(freqs, 10*np.log10(power + 1e-12)):
                writer.writerow([fr, p])

    waterfall = np.array(waterfall)
    avg_spectrum = np.mean(waterfall, axis=0)

    # Waterfall plot
    plt.figure(figsize=(10,6))
    plt.imshow(
        10*np.log10(waterfall + 1e-12),
        aspect='auto',
        extent=[freqs[0], freqs[-1], 0, num_windows],
        origin='lower',
        cmap='viridis'
    )
    plt.colorbar(label='Power (dB)')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Time Window Index')
    plt.title('Waterfall Plot (IF Data)')
    plt.tight_layout()
    plt.show()

    # Average spectrum plot
    plt.figure(figsize=(8,4))
    plt.plot(freqs, 10*np.log10(avg_spectrum + 1e-12))
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Power (dB)')
    plt.title('Average Spectrum')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()