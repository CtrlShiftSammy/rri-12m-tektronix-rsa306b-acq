import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import logging

# Configuration
recLen = 1000  # Must match the record length used in IQ_dump.py
iq_dir = "IQ_data_dump"
spec_dir = "spectra_dump"
os.makedirs(spec_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def process_iq_file(filepath):
    try:
        data = np.fromfile(filepath, dtype=np.float32)
        if data.size != recLen * 2:
            logging.warning(f"File {filepath} has unexpected size ({data.size}), skipping.")
            return None, None, None
        i = data[::2]
        q = data[1::2]
        z = i + 1j * q
        # FFT and magnitude
        spec = np.fft.fft(z, recLen)
        mag = np.abs(np.fft.fftshift(spec))
        mag_squared = mag ** 2
        # Frequency axis (assuming Fs=56e6 as in spectrum_plotter.py)
        Fs = 56e6
        f = np.fft.fftshift(np.fft.fftfreq(recLen, d=1/Fs)) / 1e6  # MHz
        return f, mag_squared, os.path.basename(filepath)
    except Exception as e:
        logging.error(f"Error processing {filepath}: {e}")
        return None, None, None

def main():
    iq_files = sorted(glob.glob(os.path.join(iq_dir, "IQ_*.bin")))
    if not iq_files:
        logging.error("No IQ binary files found.")
        return

    spectra_files = []
    for iq_file in iq_files:
        f, mag, fname = process_iq_file(iq_file)
        if f is None:
            continue
        # Extract timestamp from filename
        ts = fname.split("IQ_")[-1].replace(".bin", "")
        out_path = os.path.join(spec_dir, f"spectrum_{ts}.npz")
        np.savez_compressed(out_path, freqs=f, magnitude=mag)
        spectra_files.append((ts, out_path))
        logging.info(f"Processed {fname} -> {out_path}")

    if not spectra_files:
        logging.error("No spectra were generated.")
        return

    # Waterfall plot prompt
    resp = input("Generate waterfall plot? [y/N] ").strip().lower()
    if resp != "y":
        logging.info("Waterfall plot not generated.")
        return

    # Load spectra in time order
    spectra_files.sort()
    spectra = []
    freqs = None
    for ts, npz_path in spectra_files:
        try:
            d = np.load(npz_path)
            if freqs is None:
                freqs = d["freqs"]
            spectra.append(d["magnitude"])
        except Exception as e:
            logging.warning(f"Could not load {npz_path}: {e}")

    if not spectra:
        logging.error("No spectra loaded for waterfall plot.")
        return

    waterfall = np.vstack(spectra)
    plt.figure(figsize=(10, 6))
    plt.imshow(
        waterfall,
        aspect="auto",
        extent=[freqs[0], freqs[-1], 0, len(waterfall)],
        origin="lower",
        cmap="viridis"
    )
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Time (record index)")
    plt.title("Waterfall Plot")
    plt.colorbar(label="Magnitude")
    out_img = os.path.join(spec_dir, "waterfall.png")
    plt.savefig(out_img, dpi=150)
    plt.show()
    logging.info(f"Waterfall plot saved to {out_img}")


    # Plot average spectrum
    avg_spectrum = np.mean(waterfall, axis=0)
    plt.figure(figsize=(8, 4))
    plt.plot(freqs, avg_spectrum)
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Average Magnitude")
    plt.title("Average Spectrum")
    avg_img = os.path.join(spec_dir, "average_spectrum.png")
    plt.savefig(avg_img, dpi=150)
    plt.show()
    logging.info(f"Average spectrum plot saved to {avg_img}")

if __name__ == "__main__":
    main()
