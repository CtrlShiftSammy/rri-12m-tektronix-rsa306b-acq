# Take siq file name input, default to "iq_capture-00001"
# COnfirm siqd and siqh file names from user
# take CenterFrequency, SampleRate, AcqBandwidth, NumberSamples, RecordUtcTime from siqh file
# make header for fil file

# some to be read from config file, some to be calculated:

# • telescope id (int): 0=fake data; 1=Arecibo; 2=Ooty... others to be added
# • machine id (int): 0=FAKE; 1=PSPM; 2=WAPP; 3=OOTY... others to be added
# • data type (int): 1=filterbank; 2=time series... others to be added
# • rawdatafile (char []): the name of the original data file
# • source name (char []): the name of the source being observed by the telescope
# • barycentric (int): equals 1 if data are barycentric or 0 otherwise
# • pulsarcentric (int): equals 1 if data are pulsarcentric or 0 otherwise
# • az start (double): telescope azimuth at start of scan (degrees)
# • za start (double): telescope zenith angle at start of scan (degrees)
# • src raj (double): right ascension (J2000) of source (hhmmss.s)
# • src dej (double): declination (J2000) of source (ddmmss.s)
# • tstart (double): time stamp (MJD) of first sample
# • tsamp (double): time interval between samples (s)
# • nbits (int): number of bits per time sample
# • nsamples (int): number of time samples in the data file (rarely used any more)
# • fch1 (double): centre frequency (MHz) of first filterbank channel
# • foff (double): filterbank channel bandwidth (MHz)
# • FREQUENCY START (character): start of frequency table (see below for explanation)
# • fchannel (double): frequency channel value (MHz)
# • FREQUENCY END (character): end of frequency table (see below for explanation)
# • nchans (int): number of filterbank channels
# • nifs (int): number of seperate IF channels
# • period (double): folding period (s)

import numpy as np
import struct
import json
import argparse
import sys
import datetime
import os
from tqdm import tqdm

def put_string(f, name, value):
    f.write(struct.pack('<i', len(name)))
    f.write(name.encode())
    f.write(struct.pack('<i', len(value)))
    f.write(value.encode())

def put_int(f, name, value):
    f.write(struct.pack('<i', len(name)))
    f.write(name.encode())
    f.write(struct.pack('<i', value))

def put_double(f, name, value):
    f.write(struct.pack('<i', len(name)))
    f.write(name.encode())
    f.write(struct.pack('<d', value))

def write_sigproc_header(f, header):
    # Start marker
    f.write(struct.pack('<i', len("HEADER_START")))
    f.write("HEADER_START".encode())
    put_string(f, "rawdatafile", header["rawdatafile"])
    put_string(f, "source_name", header["source_name"])
    put_int(f, "machine_id", header["machine_id"])
    put_int(f, "telescope_id", header["telescope_id"])
    put_double(f, "src_raj",       header["src_raj"])
    put_double(f, "src_dej",       header["src_dej"])

    put_double(f, "az_start",      header["az_start"])
    put_double(f, "za_start",      header["za_start"])
    put_int(f, "data_type", header["data_type"])

    # put_int(f,    "nsamples",      header["nsamples"])
    # put_double(f, "period",        header["period"])
    put_double(f, "fch1", header["fch1"])
    put_double(f, "foff", header["foff"])
    put_int(f,    "nchans", header["nchans"])
    put_int(f,    "nbits",  header["nbits"])
    put_double(f, "tstart", header["tstart"])
    put_double(f, "tsamp",  header["tsamp"])
    put_int(f,    "nifs",   header["nifs"])
    # End marker
    f.write(struct.pack('<i', len("HEADER_END")))
    f.write("HEADER_END".encode())


# Parse base name for SIQD and SIQH files
parser = argparse.ArgumentParser()
parser.add_argument("base", nargs="?", default="IQ_data_dump/iq_capture-00001",
                    help="Base name of SIQD/SIQH files")
args = parser.parse_args()
base = args.base
siqd = f"{base}.siqd"
siqh = f"{base}.siqh"

print(f"Using SIQD file: {siqd}, SIQH file: {siqh}")
resp = input("Proceed? [Y/n]: ")
if resp.lower().startswith("n"):
    sys.exit("Aborted by user")

# Read parameters from SIQH header file
header_info = {}
keys = {"CenterFrequency", "SampleRate", "AcqBandwidth", "NumberSamples", "RecordUtcTime"}
with open(siqh, "r") as h:
    for line in h:
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if key in keys:
            if key == "NumberSamples":
                header_info[key] = int(val)
            elif key in ("CenterFrequency", "SampleRate", "AcqBandwidth"):
                header_info[key] = float(val)
            else:  # RecordUtcTime
                header_info[key] = val

# Load header from external JSON file
with open("header.json", "r") as hf:
    header = json.load(hf)

# Set SIQH-derived header fields
header["rawdatafile"] = os.path.splitext(os.path.basename(siqd))[0]

# convert RecordUtcTime string to MJD
iso_str = header_info["RecordUtcTime"]
if '.' in iso_str:
    date, frac = iso_str.split('.')
    frac = frac[:6].ljust(6, '0')    # trim or pad to 6 digits
    iso_str = f"{date}.{frac}"
dt = datetime.datetime.fromisoformat(iso_str)

def _dt_to_mjd(dt):
    D = dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond/1e6)/60)/60)/24
    y, m = dt.year, dt.month
    if m <= 2:
        y -= 1; m += 12
    A = y // 100
    B = 2 - A + A // 4
    JD = int(365.25*(y + 4716)) + int(30.6001*(m + 1)) + D + B - 1524.5
    return JD - 2400000.5

# use MJD (days)
header["tstart"] = _dt_to_mjd(dt)
header["tsamp"]       = 512.0 / header_info["SampleRate"]
header["nchans"]      = 512
# header["nsamples"]    = int(header_info["SampleRate"] / 512)
# print(header["nsamples"])
header["foff"]        = header_info["AcqBandwidth"] * (56 / 40) / (512e6)
cf = header_info["CenterFrequency"] / 1e6
header["fch1"]        = cf - header["foff"]*(512/2 - 0.5)

# Update data dimensions from header
nchans   = int(header["nchans"])
# nsamples = int(header["nsamples"])
# print(f"nchans: {nchans}, nsamples: {nsamples}")
nifs     = int(header["nifs"])

# --- WRITE .FIL FILE ---
with open("output.fil", "wb") as f_out, open(siqd, "rb") as f_in:
    write_sigproc_header(f_out, header)
    
    # compute number of 512‐sample IQ windows
    file_size     = os.path.getsize(siqd)
    total_samples = file_size // 4               # 2 bytes per I/Q × 2 channels
    num_windows   = total_samples // 512

    # process block-by-block with a progress bar
    for _ in tqdm(range(num_windows), desc="FFT blocks"):
        raw = f_in.read(512 * 4)
        iq  = np.frombuffer(raw, dtype='<i2').reshape(512, 2)
        i_vals = iq[:, 0].astype(np.float32)
        q_vals = iq[:, 1].astype(np.float32)
        spec  = np.fft.fftshift(np.abs(np.fft.fft(i_vals + 1j * q_vals)))
        power = spec
    
        power_uint8 = (power / 128).clip(0,255).astype(np.uint8)
        f_out.write(power_uint8.tobytes())
