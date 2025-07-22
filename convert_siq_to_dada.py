'''
Header parameters
When parsing header parameters, the minimum information required by DSPSR is as follows:

    HDR_VERSION: the version of the DADA header [1.0]
    INSTRUMENT: the name of the instrument used to record the data -> RSA
    TELESCOPE: the name of the observatory as recognized by tempo/tempo2 -> GBD12m
    SOURCE: the name of the source -> fakeCrab
    FREQ: centre frequency of the observed band in MHz -> 1420
    BW: width of the observed band in MHzA -> 40
    NPOL: number of polarizations -> 1
    NBIT: number of bits per sample -> 32
    TSAMP: sampling interval in microseconds -> 1/56
    UTC_START: yyyy-mm-dd-hh:mm:ss of the start of the observation -> from siqh file RecordUtcTime
    OBS_OFFSET: offset of the first sample in bytes recorded after UTC_START -> 0

The following parameters are optional:

    NCHAN: number of frequency channels into which band has been sub-divided [default: 1] -> 1
    NDIM: dimension of each time sample (1=real; 2=complex) [default: 1] -> 2
    RESOLUTION: minimum number of time samples that can be parsed [default: 1327104]
'''
import argparse
import os
import sys
from tqdm import tqdm
import datetime
import struct
import shutil
import numpy as np
import matplotlib.pyplot as plt

def _dt_to_mjd(dt):
    D = dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond/1e6)/60)/60)/24
    y, m = dt.year, dt.month
    if m <= 2:
        y -= 1; m += 12
    A = y // 100
    B = 2 - A + A // 4
    JD = int(365.25*(y + 4716)) + int(30.6001*(m + 1)) + D + B - 1524.5
    return JD - 2400000.5

# Parse base name for SIQD/SIQH files
parser = argparse.ArgumentParser()
parser.add_argument("base", nargs="?", default="IQ_data_dump/iq_capture-00001",
                    help="Base name of SIQD/SIQH files")
parser.add_argument("--histogram", action="store_true",
                    help="Enable histogramming of 16-bit samples")
args = parser.parse_args()
histogram = args.histogram
base = args.base
siqd = f"{base}.siqd"
siqh = f"{base}.siqh"

print(f"Using SIQD file: {siqd}, SIQH file: {siqh}")
resp = input("Proceed? [Y/n]: ")
if resp.lower().startswith("n"):
    sys.exit("Aborted by user")

# Default header parameters
hdr_version = "1.0"
dada_version = "1.0"
instrument = "Fake"
telescope  = "GRO"
source     = "J0534+2200"
freq       = 1420     # MHz
bw         = 40       # MHz
npol       = 1
nbit       = 8
tsamp      = 1/56     # μs
obs_offset = 0
nchan      = 1
ndim       = 2
resolution = 1
file_size  = os.path.getsize(siqd)

# Read UTC_START, CenterFrequency, AcqBandwidth from SIQH
center_mhz = None
bw_mhz     = None
utc_start  = None
sample_rate = None
with open(siqh, "r") as h:
    for line in h:
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if key == "CenterFrequency":
            center_mhz = float(val) / 1e6
        elif key == "SampleRate":
            bw_mhz = float(val) / 1e6
        elif key == "RecordUtcTime":
            utc_start = val
        elif key == "SampleRate":
            sample_rate = float(val) / 1e6

# override defaults if found
if center_mhz is not None:
    freq = center_mhz
if bw_mhz is not None:
    bw = bw_mhz
if sample_rate is not None:
    tsamp = 1.0 / sample_rate

# Print header
print("Header parameters:")
print(f"HDR_VERSION: {hdr_version}")
print(f"INSTRUMENT: {instrument}")
print(f"TELESCOPE: {telescope}")
print(f"SOURCE: {source}")
print(f"FREQ: {freq}")
print(f"BW: {bw}")
print(f"NPOL: {npol}")
print(f"NBIT: {nbit}")
print(f"TSAMP: {tsamp}")
print(f"UTC_START: {utc_start}")
print(f"OBS_OFFSET: {obs_offset}")
print(f"NCHAN: {nchan}")
print(f"NDIM: {ndim}")
print(f"RESOLUTION: {resolution}")

# # build header text dynamically
# header_txt = f"""HEADER       \tDADA\n\
# HDR_VERSION       \t{hdr_version}\n\
# HDR_SIZE       \t{4096}\n\
# DADA_VERSION       \t{dada_version}\n\
# FILE_SIZE       \t{file_size}\n\
# BW       \t{bw}\n\
# FREQ       \t{int(freq)}\n\
# TELESCOPE       \t{telescope}\n\
# RECEIVER       \t{instrument}\n\
# INSTRUMENT       \t{instrument}\n\
# SOURCE       \t{source}\n\
# RA       \t{"05:34:31.9723187"}\n\
# DEC       \t{"+22:00:52.0690424"}\n\
# MODE       \tPSR\n\
# NBIT       \t{nbit}\n\
# NCHAN       \t{nchan}\n\
# NDIM       \t{ndim}\n\
# NPOL       \t{npol}\n\
# OBS_OFFSET       \t{obs_offset}\n\
# UTC_START       \t{utc_start.replace('T', '-')}\n\
# MJD_START       \t{_dt_to_mjd(datetime.datetime.fromisoformat(utc_start))}\n\
# PICOSECONDS       \t{int(0)}\n\
# TSAMP       \t{tsamp}\n\
# RESOLUTION       \t{resolution}\n\
# END       \t# end of header\n\
# """
# build header text dynamically
header_txt = f"""HEADER       \tDADA\n\
HDR_VERSION       \t{hdr_version}\n\
HDR_SIZE       \t{4096}\n\
DADA_VERSION       \t{dada_version}\n\
BW       \t{bw}\n\
FREQ       \t{freq}\n\
TELESCOPE       \t{telescope}\n\
RECEIVER       \t{instrument}\n\
INSTRUMENT       \t{instrument}\n\
SOURCE       \t{source}\n\
RA       \t{"05:34:31.9723187"}\n\
DEC       \t{"+22:00:52.0690424"}\n\
MODE       \tPSR\n\
NBIT       \t{nbit}\n\
NCHAN       \t{nchan}\n\
NDIM       \t{ndim}\n\
NPOL       \t{npol}\n\
OBS_OFFSET       \t{0}\n\
UTC_START       \t{utc_start.replace('T', '-')}\n\
MJD_START       \t{_dt_to_mjd(datetime.datetime.fromisoformat(utc_start))}\n\
PICOSECONDS       \t{int(0)}\n\
TSAMP       \t{tsamp}\n\
RESOLUTION       \t{resolution}\n\
END       \t# end of header\n\
"""
# Manual 4096‐byte header page
header_size = 4096
# header_bytes = header_txt.encode('ascii')
header_bytes = header_txt.encode('utf-8')

if len(header_bytes) > header_size:
    sys.exit("Header too long for header_size")
header_padded = header_bytes.ljust(header_size, b'\x00')

outfile = f"{base}.dada"
# write header
with open(outfile, "wb") as f_out:
    f_out.write(header_padded)

# set up histogram only if requested
if histogram:
    num_bins = 256*32
    bin_edges = np.linspace(-32768, 32767, num_bins+1, dtype=np.int32)
    hist_counts = np.zeros(num_bins, dtype=np.int64)
min_val = None
max_val = None

file_size = os.path.getsize(siqd)
with open(siqd, "rb") as f_in, open(outfile, "ab") as f_out, \
    tqdm(total=file_size, desc="Processing into .dada", unit='B', unit_scale=True) as pbar:
    while True:
        chunk = f_in.read(64 * 1024 * 1024)
        if not chunk:
            break
        arr16 = np.frombuffer(chunk, dtype='<i2')
        if histogram:
            counts_chunk, _ = np.histogram(arr16, bins=bin_edges)
            hist_counts += counts_chunk
        if min_val is None and max_val is None:
            min_val = int(arr16.min())
            max_val = int(arr16.max())
        else:
            min_val = min(min_val, int(arr16.min()))
            max_val = max(max_val, int(arr16.max()))
        arr8 = ((arr16 << 6) >> 8).astype(np.int8)
        f_out.write(arr8.tobytes())
        f_out.flush()
        pbar.update(len(chunk))
    os.fsync(f_out.fileno())

# plotting and stats only if requested
if histogram:
    plt.figure()
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    plt.bar(centers, hist_counts, width=centers[1] - centers[0])
    plt.xlabel('16-bit sample value')
    plt.ylabel('Count')
    plt.title('Histogram of 16-bit samples')
    plt.tight_layout()
    plt.show()
    print(f"Minimum 16-bit sample value: {min_val}")
    print(f"Maximum 16-bit sample value: {max_val}")

