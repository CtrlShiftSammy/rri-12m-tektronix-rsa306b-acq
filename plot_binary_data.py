import os
import glob
import numpy as np
import matplotlib.pyplot as plt

recLen = 1000  # Must match the record length used in IQ_dump.py
iq_dir = "IQ_data_dump"

# Get only the first IQ binary file
iq_files = sorted(glob.glob(os.path.join(iq_dir, "IQ_*.bin")))[:1]
if not iq_files:
    print("No IQ binary files found.")
    exit(1)

samples = []

for filepath in iq_files:
    data = np.fromfile(filepath, dtype=np.float32)
    if data.size != recLen * 2:
        continue  # skip files with unexpected size
    i = data[::2]
    q = data[1::2]
    z = i + 1j * q
    samples.append(z)

if not samples:
    print("No valid samples computed.")
    exit(1)

avg_samples = samples[0]  # Only one file, so just use its samples
i_avg = np.real(avg_samples)
q_avg = np.imag(avg_samples)
phase = np.arctan2(q_avg, i_avg)

plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(i_avg, label="I")
plt.plot(q_avg, label="Q")
plt.xlabel("Sample Index")
plt.ylabel("Amplitude")
plt.title("IQ Samples (First File)")
plt.legend()
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(phase, label="Phase (arctan(Q/I))", color='purple')
plt.xlabel("Sample Index")
plt.ylabel("Phase (radians)")
plt.title("Phase (arctan(Q/I))")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()


