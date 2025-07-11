import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np  # added for FFT

NUM_SAMPLES = 112e3  # number of samples to process

def main():
    parser = argparse.ArgumentParser(
        description=f"Plot first {NUM_SAMPLES} values of the last CSV column against index."
    )
    parser.add_argument("csv_file", help="Path to input CSV file")
    args = parser.parse_args()

    values = []
    with open(args.csv_file, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                values.append(float(row[-1]))
            except ValueError:
                # skip rows where last column isn't numeric
                continue
            if len(values) >= NUM_SAMPLES:
                break

    tuning_freq = 1420e6
    signal_generator_freq = 1400e6  # Hz
    Fs = 112e6  # sample rate in Hz
    times = np.arange(len(values)) / Fs

    # calculate phase offset for signal_generator_freq from FFT
    spec_full = np.fft.fft(values)
    freqs_full = np.fft.fftfreq(len(values), d=1/Fs)[:len(values) // 2] / 1e6 + tuning_freq / 1e6 - Fs / 4e6
    # freqs_full = np.fft.fftfreq(len(values), d=1/Fs) / 1e6 + tuning_freq / 1e6 - Fs / 4e6
    idx_sig = np.argmin(np.abs(freqs_full - signal_generator_freq/1e6))
    phase_offset = np.angle(spec_full[idx_sig])

    # generate high-res cosine with that phase offset
    high_res_factor = 10
    t_high = np.arange(len(values) * high_res_factor) / (Fs * high_res_factor)
    # cos_signal = 200 * np.cos(2 * np.pi * (signal_generator_freq - tuning_freq) * t_high + phase_offset)
    cos_signal = 200 * np.cos(2 * np.pi * (10e6) * t_high + phase_offset)

    # Replace single plot with two subplots: time-series on top, FFT below
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))

    # Top: time series with overlay
    ax1.plot(times, values, label='IF data')
    # Set xlim to first 1/10th of the data
    max_time = times[-1] if len(times) > 0 else 0
    ax1.set_xlim(0, max_time / 10)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("IF data")
    ax1.set_title(f"First {NUM_SAMPLES} samples vs Time")
    ax1.legend()
    ax1.grid(True)

    # Bottom: FFT magnitude (dB)
    # tuning_freq= 40e6
    # Fs = 112e6
    spec = np.fft.fft(values)
    # freqs = np.fft.fftfreq(len(values), d=1/Fs)[:len(values) // 2] / 1e6 + tuning_freq / 1e6 - Fs / 4e6
    freqs = np.fft.fftfreq(len(values), d=1/Fs) / 1e6 + tuning_freq / 1e6 - Fs / 4e6
    half = len(values) // 2
    # ax2.plot(freqs[:half], 20 * np.log10(np.abs(spec[:half]) + 1e-12))
    ax2.plot(freqs, 20 * np.log10(np.abs(spec) + 1e-12), 'o-')
    ax2.set_xlabel("Frequency (MHz)")
    ax2.set_ylabel("Magnitude (dB)")
    ax2.set_title("FFT of Window")
    ax2.grid(True)
    print(f"At frequency {freqs[len(freqs) - 1]:.2f} MHz, magnitude is {20 * np.log10(np.abs(spec[len(spec) - 1]) + 1e-12):.2f} dB")

    plt.tight_layout()
    plt.show()


    odd_samples = np.zeros(len(values) // 2)
    odd_sample_times = np.zeros(len(values) // 2)
    even_samples = np.zeros(len(values) // 2)
    even_sample_times = np.zeros(len(values) // 2)
    for i in range(len(values)):
        if i % 2 == 0:
            even_samples[i // 2] = values[i]
            even_sample_times[i // 2] = times[i]
        else:
            odd_samples[i // 2] = values[i]
            odd_sample_times[i // 2] = times[i]
    # Plot odd and even samples
    plt.figure(figsize=(10, 6))
    plt.plot(even_sample_times, even_samples, 'o-', label='Even Samples', alpha=0.7)
    plt.plot(odd_sample_times, odd_samples, 'o-', label='Odd Samples', alpha=0.7)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Odd and Even Samples")
    plt.legend()
    plt.xlim(0, max_time / 1000)
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    



    from scipy.signal import firwin, filtfilt, freqz
    cutoff_freq = 52e6  # Hz
    nyquist = Fs / 2
    numtaps = 201  # Number of filter taps (adjust as needed)
    fir_coeff = firwin(numtaps, cutoff_freq / nyquist)
    filtered_if = filtfilt(fir_coeff, [1.0], values)


    # Plot filtered_if and values in same graph, with their FFTs, and filter response
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 9))

    # Time domain: original and filtered
    ax1.plot(times, values, label='Original', alpha=0.7)
    ax1.plot(times, filtered_if, label='Filtered', alpha=0.7)
    ax1.set_xlim(0, max_time / 10)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude")
    ax1.set_title("Original vs Filtered Signal (Time Domain)")
    ax1.legend()
    ax1.grid(True)

    # FFTs
    spec_orig = np.fft.fft(values)
    spec_filt = np.fft.fft(filtered_if)
    freqs_fft = np.fft.fftfreq(len(values), d=1/Fs)[:len(values)//2] / 1e6
    ax2.plot(freqs_fft, 20 * np.log10(np.abs(spec_orig[:len(values)//2]) + 1e-12), label='Original')
    ax2.plot(freqs_fft, 20 * np.log10(np.abs(spec_filt[:len(values)//2]) + 1e-12), label='Filtered')
    ax2.set_xlabel("Frequency (MHz)")
    ax2.set_ylabel("Magnitude (dB)")
    ax2.set_title("FFT: Original vs Filtered")
    ax2.legend()
    ax2.grid(True)

    # Filter frequency response
    w, h = freqz(fir_coeff, worN=8000)
    freqs_filter = w * Fs / (2 * np.pi) / 1e6  # MHz
    ax3.plot(freqs_filter, 20 * np.log10(np.abs(h)), label='Filter response')
    ax3.axvline(x=cutoff_freq/1e6, color='k', linestyle='--', alpha=0.7, label=f'Cutoff: {cutoff_freq/1e6:.0f} MHz')
    ax3.set_xlabel("Frequency (MHz)")
    ax3.set_ylabel("Magnitude (dB)")
    ax3.set_title("FIR Filter Frequency Response")
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    plt.show()

    # Mix with 28 MHz signal
    mix_freq = 28e6  # Hz
    t_mix = np.arange(len(values)) / Fs
    mix_signal = np.cos(2 * np.pi * mix_freq * t_mix)
    mixed_if = filtered_if * mix_signal

    # Low-pass filter after mixing
    cutoff_freq_post_mix = 50e6  # Hz
    fir_coeff_post_mix = firwin(numtaps, cutoff_freq_post_mix / nyquist)
    filtered_mixed_if = filtfilt(fir_coeff_post_mix, [1.0], mixed_if)


    # Plot mixed filtered signal time series, FFTs, and filter response
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), gridspec_kw={'height_ratios': [2, 1, 1]})

    ax1, ax2, ax3 = axes

    # 1. Time domain: mixed and filtered mixed signals
    ax1.plot(t_mix, filtered_if, label='Filtered IF', alpha=0.7)
    ax1.plot(t_mix, mixed_if, label='Mixed IF', alpha=0.7)
    ax1.plot(t_mix, filtered_mixed_if, label='Filtered Mixed IF', alpha=0.7)
    ax1.set_xlim(0, max_time / 10)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude")
    ax1.set_title("Mixed and Filtered Mixed Signal (Time Domain)")
    ax1.legend()
    ax1.grid(True)

    # 2. FFTs
    mixed_spec = np.fft.fft(mixed_if)
    filtered_mixed_spec = np.fft.fft(filtered_mixed_if)
    freqs_mix = np.fft.fftfreq(len(mixed_if), d=1/Fs)[:len(mixed_if)//2] / 1e6
    ax2.plot(freqs_mix, 20 * np.log10(np.abs(mixed_spec[:len(mixed_if)//2]) + 1e-12), label='Mixed IF')
    ax2.plot(freqs_mix, 20 * np.log10(np.abs(filtered_mixed_spec[:len(mixed_if)//2]) + 1e-12), label='Filtered Mixed IF')
    ax2.set_xlabel("Frequency (MHz)")
    ax2.set_ylabel("Magnitude (dB)")
    ax2.set_title("FFT: Mixed vs Filtered Mixed Signal")
    ax2.legend()
    ax2.grid(True)

    # 3. Filter frequency response
    w_post, h_post = freqz(fir_coeff_post_mix, worN=8000)
    freqs_filter_post = w_post * Fs / (2 * np.pi) / 1e6
    ax3.plot(freqs_filter_post, 20 * np.log10(np.abs(h_post)), label='Post-mix filter response')
    ax3.axvline(x=cutoff_freq_post_mix/1e6, color='k', linestyle='--', alpha=0.7, label=f'Cutoff: {cutoff_freq_post_mix/1e6:.0f} MHz')
    ax3.set_xlabel("Frequency (MHz)")
    ax3.set_ylabel("Magnitude (dB)")
    ax3.set_title("FIR Filter Frequency Response (Post-mix)")
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    plt.show()

    # # Plot mixed and filtered signals
    # fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(12, 12))

    # # Filtered signal time domain
    # ax1.plot(t_mix, filtered_if, color='red')
    # ax1.set_xlim(0, max_time / 10)
    # ax1.set_xlabel("Time (s)")
    # ax1.set_ylabel("Amplitude")
    # ax1.set_title("Low-pass Filtered Signal (50 MHz cutoff)")
    # ax1.legend()
    # ax1.grid(True)

    # # Mixed signal time domain
    # ax2.plot(t_mix, mixed_if, label='Mixed with 28 MHz', color='blue')
    # ax2.set_xlim(0, max_time / 10)
    # ax2.set_xlabel("Time (s)")
    # ax2.set_ylabel("Amplitude")
    # ax2.set_title("IF Mixed with 28 MHz Signal")
    # ax2.legend()
    # ax2.grid(True)

    # # Filtered mixed signal time domain
    # ax3.plot(t_mix, filtered_mixed_if, color='green')
    # ax3.set_xlim(0, max_time / 10)
    # ax3.set_xlabel("Time (s)")
    # ax3.set_ylabel("Amplitude")
    # ax3.set_title("Low-pass Filtered Signal After Mixing (50 MHz cutoff)")
    # ax3.legend()
    # ax3.grid(True)

    # # FFT comparison
    # mixed_spec = np.fft.fft(mixed_if)
    # filtered_spec = np.fft.fft(filtered_if)
    # filtered_mixed_spec = np.fft.fft(filtered_mixed_if)
    # freqs_mix = np.fft.fftfreq(len(mixed_if), d=1/Fs)[:len(mixed_if) // 2] / 1e6
    # ax4.plot(freqs_mix, 20 * np.log10(np.abs(mixed_spec[:len(mixed_spec) // 2]) + 1e-12), 
    #          alpha=0.7, label='Mixed signal')
    # ax4.plot(freqs_mix, 20 * np.log10(np.abs(filtered_spec[:len(filtered_spec) // 2]) + 1e-12), 
    #          label='Pre-mix filtered signal', color='red')
    # ax4.plot(freqs_mix, 20 * np.log10(np.abs(filtered_mixed_spec[:len(filtered_mixed_spec) // 2]) + 1e-12), 
    #          label='Post-mix filtered signal', color='green')
    # ax4.set_xlabel("Frequency (MHz)")
    # ax4.set_ylabel("Magnitude (dB)")
    # ax4.set_title("FFT Comparison: Mixed vs Filtered Signals")
    # ax4.legend()
    # ax4.grid(True)

    # # Filter frequency response
    # from scipy.signal import freqz
    # w, h = freqz(fir_coeff, worN=8000)
    # w_post, h_post = freqz(fir_coeff_post_mix, worN=8000)
    # freqs_filter = w * Fs / (2 * np.pi) / 1e6  # Convert to MHz
    # freqs_filter_post = w_post * Fs / (2 * np.pi) / 1e6
    # ax5.plot(freqs_filter, 20 * np.log10(np.abs(h)), 'b-', label='Pre-mix filter (50 MHz)')
    # ax5.plot(freqs_filter_post, 20 * np.log10(np.abs(h_post)), 'g-', label='Post-mix filter (24 MHz)')
    # ax5.set_xlabel("Frequency (MHz)")
    # ax5.set_ylabel("Magnitude (dB)")
    # ax5.set_title("FIR Filter Frequency Responses")
    # ax5.legend()
    # ax5.grid(True)
    
    # plt.tight_layout()
    # plt.show()



    # # Mix with 28 MHz signal
    # mix_freq = 28e6  # Hz
    # t_mix = np.arange(len(values)) / Fs
    # mix_signal = np.cos(2 * np.pi * mix_freq * t_mix)
    # mixed_if = np.array(values) * mix_signal
    
    # # FIR Low-pass filter at 27 MHz
    # from scipy.signal import firwin, filtfilt
    # cutoff_freq = 27e6  # Hz
    # nyquist = Fs / 2
    # numtaps = 201  # Number of filter taps (adjust as needed)
    # fir_coeff = firwin(numtaps, cutoff_freq / nyquist)
    # filtered_if = filtfilt(fir_coeff, [1.0], mixed_if)
    
    # # Plot mixed and filtered signals
    # fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 10))
    
    # # Mixed signal time domain
    # ax1.plot(t_mix, mixed_if, label='Mixed with 28 MHz')
    # ax1.set_xlim(0, max_time / 10)
    # ax1.set_xlabel("Time (s)")
    # ax1.set_ylabel("Amplitude")
    # ax1.set_title("IF Mixed with 28 MHz Signal")
    # ax1.legend()
    # ax1.grid(True)
    
    # # Filtered signal time domain
    # ax2.plot(t_mix, filtered_if, label='Low-pass filtered (55 MHz)', color='red')
    # ax2.set_xlim(0, max_time / 10)
    # ax2.set_xlabel("Time (s)")
    # ax2.set_ylabel("Amplitude")
    # ax2.set_title("Low-pass Filtered Signal (55 MHz cutoff)")
    # ax2.legend()
    # ax2.grid(True)
    
    # # FFT comparison
    # mixed_spec = np.fft.fft(mixed_if)
    # filtered_spec = np.fft.fft(filtered_if)
    # freqs_mix = np.fft.fftfreq(len(mixed_if), d=1/Fs)[:len(mixed_if) // 2] / 1e6
    
    # ax3.plot(freqs_mix, 20 * np.log10(np.abs(mixed_spec[:len(mixed_spec) // 2]) + 1e-12), 
    #          alpha=0.7, label='Mixed signal')
    # ax3.plot(freqs_mix, 20 * np.log10(np.abs(filtered_spec[:len(filtered_spec) // 2]) + 1e-12), 
    #          label='Filtered signal', color='red')
    # ax3.set_xlabel("Frequency (MHz)")
    # ax3.set_ylabel("Magnitude (dB)")
    # ax3.set_title("FFT Comparison: Mixed vs Filtered")
    # ax3.legend()
    # ax3.grid(True)
    
    # # Filter frequency response
    # from scipy.signal import freqz
    # w, h = freqz(fir_coeff, worN=8000)
    # freqs_filter = w * Fs / (2 * np.pi) / 1e6  # Convert to MHz
    
    # ax4_twin = ax4.twinx()
    # ax4.plot(freqs_filter, 20 * np.log10(np.abs(h)), 'b-', label='Magnitude')
    # ax4.set_xlabel("Frequency (MHz)")
    # ax4.set_ylabel("Magnitude (dB)", color='b')
    # ax4.set_title("FIR Filter Frequency Response")
    # ax4.grid(True)
    # ax4.tick_params(axis='y', labelcolor='b')
    
    # # ax4_twin.plot(freqs_filter, np.angle(h) * 180 / np.pi, 'r-', label='Phase')
    # # ax4_twin.set_ylabel("Phase (degrees)", color='r')
    # # ax4_twin.tick_params(axis='y', labelcolor='r')
    
    # # Add vertical line at cutoff frequency
    # ax4.axvline(x=cutoff_freq/1e6, color='k', linestyle='--', alpha=0.7, label=f'Cutoff: {cutoff_freq/1e6:.0f} MHz')
    # ax4.legend(loc='upper right')
    
    # plt.tight_layout()
    # plt.show()

    

if __name__ == "__main__":
    main()
