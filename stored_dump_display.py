import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date, time
from tqdm import tqdm
from matplotlib.dates import DateFormatter

DUMP_DIR = "LIVE_DISPLAY_DUMP"

def _list_dumps():
    files = [f for f in os.listdir(DUMP_DIR) if f.startswith("dump_") and f.endswith(".npz")]
    files.sort()
    return [os.path.join(DUMP_DIR, f) for f in files]

def _parse_dt(fname):
    # fname: .../dump_YYYYMMDD_HHMMSS_ffffff.npz
    base = os.path.basename(fname)[5:-4]
    return datetime.strptime(base, "%Y%m%d_%H%M%S_%f")

def mode_plot_power():
    # prompt for interval (empty → today’s start/end)
    start_ts = input("Enter start time (YYYY-MM-DD HH:MM:SS) [default: start of today]: ").strip()
    end_ts   = input("Enter end time (YYYY-MM-DD HH:MM:SS) [default: end of today]: ").strip()
    today = date.today()
    if start_ts:
        try:
            start = datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("Bad start time format. Use YYYY-MM-DD HH:MM:SS.")
            return
    else:
        start = datetime.combine(today, time.min)
    if end_ts:
        try:
            end = datetime.strptime(end_ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("Bad end time format. Use YYYY-MM-DD HH:MM:SS.")
            return
    else:
        end = datetime.combine(today, time.max)
    if start > end:
        print("Start time is after end time.")
        return

    dumps = _list_dumps()
    # filter dumps in interval
    selected = []
    for fn in dumps:
        dt = _parse_dt(fn)
        if start <= dt <= end:
            selected.append((dt, fn))
    if not selected:
        print(f"No dump files between {start_ts} and {end_ts}.")
        return

    # build datetime and power lists
    times = [dt for dt, fn in selected]
    powers = []
    for dt, fn in tqdm(selected, desc="Loading power data"):
        powers.append(np.load(fn)["power"])
    # ask reference power for 0 dB
    default_p0 = np.median(powers)
    p0_str = input(f"Enter P_0 dB reference value [default: {default_p0}]: ").strip()
    if p0_str:
        try:
            p0 = float(p0_str)
        except ValueError:
            print("Bad P_0 format.")
            return
    else:
        p0 = default_p0
    powers_db = 10 * np.log10(np.array(powers) / p0)
    plt.figure()
    plt.plot(times, powers_db, 'o-')
    ax = plt.gca()
    if times[0].date() == times[-1].date():
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
    else:
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d %H:%M:%S"))
    plt.gcf().autofmt_xdate()           # format date labels
    plt.xlabel("Time")
    plt.ylabel("Power (dB re P0)")
    plt.title(f"Recorded Power")
    plt.grid(True)
    plt.show()

def mode_avg_fft():
    ts = input("Enter target time (YYYY-MM-DD HH:MM:SS): ")
    try:
        target = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("Bad format.")
        return
    files = _list_dumps()
    specs = []
    freqs = None
    for fn in files:
        dt = _parse_dt(fn)
        if abs((dt - target).total_seconds()) <= 10:
            data = np.load(fn)
            specs.append(data["fft"])
            freqs = data["freq"]
    if not specs:
        print("No dumps within ±10 s of", target)
        return
    avg_spec = np.mean(specs, axis=0)
    plt.figure()
    plt.plot(freqs, avg_spec)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.title(f"Average FFT ±10 s around {ts}")
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    print("Select mode:\n 1) Plot power vs time\n 2) Average FFT around a timestamp")
    choice = input("Enter 1 or 2: ").strip()
    if choice == "1":
        mode_plot_power()
    elif choice == "2":
        mode_avg_fft()
    else:
        print("Invalid choice.")
