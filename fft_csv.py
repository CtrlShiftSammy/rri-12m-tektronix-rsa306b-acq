import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def process_if_csv(csv_path, window_size=1024, Fs=112e6):
    # Read IF values from CSV
    df = pd.read_csv(csv_path)
    data = df['IF_Value'].to_numpy(dtype=np.float32)
    
    num_windows = len(data) // window_size
    data = data[:num_windows * window_size]  # Truncate to full windows

    waterfall = []

    for i in range(num_windows):
        segment = data[i * window_size : (i + 1) * window_size]
        spec = np.fft.fft(segment)
        power = np.abs(spec[:window_size // 2]) ** 2  # Single-sided spectrum
        waterfall.append(power)

    waterfall = np.array(waterfall)
    avg_spectrum = np.mean(waterfall, axis=0)

    # Frequency axis (in MHz), shifted by tuning frequency
    tuning_freq_MHz = 100
    freqs = np.fft.fftfreq(window_size, d=1/Fs)[:window_size // 2] / 1e6 + tuning_freq_MHz - Fs / 4e6

    # Plot waterfall
    plt.figure(figsize=(10, 6))
    plt.imshow(
        10 * np.log10(waterfall + 1e-12),  # dB scale
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

    # Plot average spectrum
    plt.figure(figsize=(8, 4))
    plt.plot(freqs, 10 * np.log10(avg_spectrum + 1e-12))
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Power (dB)')
    plt.title('Average Spectrum')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# Example usage
process_if_csv("IF_data_dump/if_capture-00001.csv")
