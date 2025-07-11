import numpy as np
import matplotlib.pyplot as plt
from ctypes import *
from datetime import datetime
import os
import time
import scienceplots

plt.style.use('science')
plt.rcParams['text.usetex'] = False  # Disable LaTeX rendering

# --- helper funcs ---
def exerr(err):
    if err != 0:
        rsa.DEVICE_GetErrorString.restype = c_char_p
        msg = rsa.DEVICE_GetErrorString(err).decode()
        raise RuntimeError(msg)

def connect_and_configure(rec_len, cf_hz, bw_hz, ref_lvl_dbm):
    # load libs
    global rsa
    RTLD_LAZY = 0x0001
    LAZYLOAD = RTLD_LAZY | RTLD_GLOBAL
    rsa = CDLL("./libRSA_API.so",LAZYLOAD)
    usbapi = CDLL("./libcyusb_shared.so",LAZYLOAD)

    # connect
    num = c_int()
    ids = (c_int*20)()
    exerr(rsa.DEVICE_Search(byref(num), ids, None, None))
    if num.value==0: raise RuntimeError("No device")
    exerr(rsa.DEVICE_Connect(ids[0]))
    # basic config
    exerr(rsa.CONFIG_SetCenterFreq(c_double(cf_hz)))
    exerr(rsa.CONFIG_SetReferenceLevel(c_double(ref_lvl_dbm)))
    exerr(rsa.IQBLK_SetIQRecordLength(c_int(rec_len)))
    exerr(rsa.IQBLK_SetIQBandwidth(c_double(bw_hz)))
    return rec_len

def get_iq(rec_len):
    # run & wait
    r = c_bool(False)
    exerr(rsa.DEVICE_Run())
    exerr(rsa.IQBLK_WaitForIQDataReady(1000, byref(r)))
    buf = (c_float* (rec_len*2))()
    out = c_int()
    if r.value:
        exerr(rsa.IQBLK_GetIQData(buf, byref(out), c_int(rec_len)))
        data = np.frombuffer(buf, dtype=np.float32).reshape(-1,2)
        return data[:,0] + 1j*data[:,1]
    return np.array([],dtype=complex)

# --- main ---
if __name__=="__main__":
    center_freq = 1.42e9  # Center frequency in Hz
    bandwidth = 40e6      # Bandwidth in Hz
    ref_level = 0.0       # Reference level in dBm

    rec_len = connect_and_configure(rec_len=1024, cf_hz=center_freq, bw_hz=bandwidth, ref_lvl_dbm=ref_level)
    # plotting setup
    plt.ion()
    fig, (ax_fft, ax_pow) = plt.subplots(2,1, figsize=(10,9))
    fig.suptitle("RSA 306B Low Performance Display Dump", fontsize=15)
    # Add text with configuration information
    info_text = f"Center Frequency: {center_freq/1e6:.1f} MHz, Bandwidth: {bandwidth/1e6:.1f} MHz, Reference Level: {ref_level:.1f} dBm"
    fig.text(0.5, 0.93, info_text, ha='center', va='center', fontsize=13)
    
    line_fft, = ax_fft.plot([],[], alpha=0.65)
    line_fft_avg, = ax_fft.plot([],[], color='red')
    ax_fft.set_title("Spectrum")
    ax_fft.legend(["FFT (Instantaneous)", "FFT (Moving Avg)"], loc='upper right')
    line_pow, = ax_pow.plot([],[], 'o-')
    ax_pow.set_title("Power vs time")
    pow_hist = []
    pow_db_hist = []  # Store power in dB
    time_hist = []
    fft_hist = []
    start_time = time.time()
    dump_dir = "LIVE_DISPLAY_DUMP"
    os.makedirs(dump_dir, exist_ok=True)

    def format_time_axis(times):
        """Return (scaled_times, label) based on max time."""
        if not times:
            return times, r"$t\,(s)$"
        max_time = times[-1]
        if max_time < 120:
            return times, r"$t\,(s)$"
        elif max_time < 7200:
            return [t/60 for t in times], r"$t\,(min)$"
        else:
            return [t/3600 for t in times], r"$t\,(hr)$"

    def on_close(event):
        try:
            rsa.DEVICE_Stop()
            rsa.DEVICE_Disconnect()
        except Exception:
            pass  # Ignore errors if already disconnected

    fig.canvas.mpl_connect('close_event', on_close)

    try:
        while True:
            z = get_iq(rec_len)
            if z.size==0: continue
            # fft
            spec = np.fft.fftshift(np.abs(np.fft.fft(z)))
            freqs = np.linspace(center_freq - 56e6/2, center_freq + 56e6/2, rec_len)
            # Store FFT for moving average
            fft_hist.append(spec)
            if len(fft_hist) > 20:
                fft_hist.pop(0)
            # Compute moving average if enough data
            if len(fft_hist) > 1:
                spec_avg = np.mean(fft_hist, axis=0)
            else:
                spec_avg = spec
            # power metric
            p = np.mean(np.abs(z)**2)
            pow_hist.append(p)
            current_time = time.time() - start_time
            time_hist.append(current_time)
            # --- Power dB scaling ---
            # Find indices for points within first 10 seconds
            ten_sec_indices = [i for i, t in enumerate(time_hist) if t <= 10.0]
            if ten_sec_indices:
                idx_last = ten_sec_indices[-1] + 1  # up to and including last <=10s
            else:
                idx_last = 1  # fallback, should not happen
            p0db = np.mean(pow_hist[:idx_last])
            # Convert all power values to dB relative to p0db
            pow_db_hist = [10 * np.log10(p/p0db) if p0db > 0 else 0 for p in pow_hist]
            # save
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fn = os.path.join(dump_dir, f"dump_{ts}.npz")
            np.savez(fn, iq=z, fft=spec, freq=freqs, power=p, time=current_time)
            # update plots
            line_fft.set_data(freqs, spec)
            line_fft_avg.set_data(freqs, spec_avg)
            ax_fft.relim(); ax_fft.autoscale_view()
            ax_fft.set_xlabel(r"$f\,(Hz)$")
            ax_fft.set_ylabel(r"$P\,\mathrm{(Arbitrary\ Units)}$")
            # Update time axis scaling and label
            scaled_time, time_label = format_time_axis(time_hist)
            line_pow.set_data(scaled_time, pow_db_hist)
            ax_pow.set_xlabel(time_label)
            ax_pow.set_ylabel(r"$P\,\mathrm{(dB)}$")
            ax_pow.relim(); ax_pow.autoscale_view()
            plt.pause(0.1)
    except KeyboardInterrupt:
        rsa.DEVICE_Stop()
        rsa.DEVICE_Disconnect()
        pass




