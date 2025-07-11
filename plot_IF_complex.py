import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np  # added for FFT
from matplotlib.ticker import FuncFormatter

NUM_SAMPLES = 112e1  # number of samples to process


# Custom tick labels
def format_func(value, tick_number):
    n = int(np.round(value / (np.pi / 2)))
    if n == 0:
        return "0"
    elif n == 1:
        return r"$\frac{\pi}{2}$"
    elif n == 2:
        return r"$\pi$"
    elif n == 3:
        return r"$\frac{3\pi}{2}$"
    elif n == 4:
        return r"$2\pi$"
    elif n == -1:
        return r"$-\frac{\pi}{2}$"
    elif n == -2:
        return r"$-\pi$"
    elif n == -3:
        return r"$-\frac{3\pi}{2}$"
    elif n == -4:
        return r"$-2\pi$"
    else:
        return f"{value:.2f}"

def main():
    parser = argparse.ArgumentParser(
        description=f"Plot first {NUM_SAMPLES} values of the last CSV column against index."
    )
    parser.add_argument("csv_file", help="Path to input CSV file")
    args = parser.parse_args()

    # values = []
    even_values = np.zeros(int(NUM_SAMPLES))
    odd_values = np.zeros(int(NUM_SAMPLES))
    with open(args.csv_file, newline="") as f:
        reader = csv.reader(f)
        i = 0
        for row in reader:
            if not row:
                continue
            try:
                # values.append(float(row[-1]))
                if i % 2 == 0:
                    even_values[i // 2] = float(row[-1])
                else:
                    odd_values[i // 2] = float(row[-1])                    
            except ValueError:
                # skip rows where last column isn't numeric
                continue
            i += 1
            if i >= NUM_SAMPLES * 2:
                break
    tuning_freq = 1420e6
    signal_generator_freq = 1400e6  # Hz
    Fs = 56e6  # sample rate in Hz
    times = np.arange(NUM_SAMPLES) / Fs

    
    fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Plot even and odd values
    axs[0].plot(times, even_values, 'o-', label="Even samples")
    axs[0].plot(times, odd_values, 'o-', label="Odd samples")
    axs[0].set_ylabel("Amplitude")
    axs[0].set_title("Even and Odd Sample Values")
    axs[0].legend()
    axs[0].grid(True)

    # Compute and plot phase
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        phase = np.arctan2(odd_values, even_values)
    axs[1].plot(times, phase, 'o-')
    axs[1].set_ylabel("Phase (radians)")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_title("Phase: arctan2(odd, even)")
    axs[1].grid(True)

    # Set y-ticks at multiples of pi/2
    yticks = np.arange(-2*np.pi, 2.5*np.pi, np.pi/2)
    axs[1].set_yticks(yticks)

    axs[1].yaxis.set_major_formatter(FuncFormatter(format_func))

    plt.tight_layout()
    plt.show()




    odd_values_dc_removed = odd_values - np.mean(odd_values)
    even_values_dc_removed = even_values - np.mean(even_values)

    fig, axs = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Plot even and odd values
    axs[0].plot(times, even_values_dc_removed, 'o-', label="Even samples")
    axs[0].plot(times, odd_values_dc_removed, 'o-', label="Odd samples")
    axs[0].set_ylabel("Amplitude")
    axs[0].set_title("Even and Odd Sample Values")
    axs[0].legend()
    axs[0].grid(True)

    # Compute and plot phase
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        phase = np.arctan2(odd_values_dc_removed, even_values_dc_removed)
    axs[1].plot(times, phase, 'o-')
    axs[1].set_ylabel("Phase (radians)")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_title("Phase: arctan2(odd, even)")
    axs[1].grid(True)

    # Set y-ticks at multiples of pi/2
    yticks = np.arange(-2*np.pi, 2.5*np.pi, np.pi/2)
    axs[1].set_yticks(yticks)

    axs[1].yaxis.set_major_formatter(FuncFormatter(format_func))

    plt.tight_layout()
    plt.show()





if __name__ == "__main__":
    main()

