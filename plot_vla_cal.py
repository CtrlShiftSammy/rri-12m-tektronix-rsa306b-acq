import re
from astropy.coordinates import SkyCoord
import astropy.units as u

import numpy as np
import matplotlib.pyplot as plt

def parse_sources(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    sources = []
    for line in lines:
        if re.match(r'^\d{4}[+-]\d{3}.*J2000', line):
            parts = line.split()
            name = parts[0]
            ra = parts[3]
            dec = parts[4]
            sources.append((name, ra, dec))
    return sources

def ra_to_degrees(ra_str):
    h = float(re.search(r'(\d+)h', ra_str).group(1))
    m = float(re.search(r'(\d+)m', ra_str).group(1))
    s = float(re.search(r'(\d+\.?\d*)s', ra_str).group(1))
    return 15 * (h + m/60 + s/3600)

def dec_to_degrees(dec_str):
    sign = -1 if dec_str.startswith('-') else 1
    dec_str = dec_str.lstrip('-')
    d = float(re.search(r'(\d+)d', dec_str).group(1))
    m = float(re.search(r"(\d+)'", dec_str).group(1))
    s = float(re.search(r'(\d+\.?\d*)"', dec_str).group(1))
    return sign * (d + m/60 + s/3600)

sources = parse_sources('VLA_calibrator_list.txt')
ra_vals = [ra_to_degrees(ra) for _, ra, _ in sources]
dec_vals = [dec_to_degrees(dec) for _, _, dec in sources]
names = [name for name, _, _ in sources]

plt.figure(figsize=(8,6))
plt.scatter(ra_vals, dec_vals, marker='o', color='blue', alpha=0.5)
# for i, name in enumerate(names):
#     plt.annotate(name, (ra_vals[i], dec_vals[i]), textcoords="offset points", xytext=(5,-5), ha='left')

plt.xlim(0, 360)
plt.ylim(-90, 90)
plt.gca().set_aspect('equal', adjustable='box')

# Add Vela pulsar (PSR J0835-4510)
vela_ra = ra_to_degrees('08h35m20.655175s')
vela_dec = dec_to_degrees('-45d10\'35.153252"')
plt.scatter([vela_ra], [vela_dec], marker='*', color='red', s=200, label='Vela Pulsar')
plt.annotate('PSR J0835-4510', (vela_ra, vela_dec), textcoords="offset points", xytext=(10,10), ha='left', color='red')

# Add Crab pulsar (PSR J0534+2200)
crab_ra = ra_to_degrees('05h34m31.95s')
crab_dec = dec_to_degrees('+22d00\'52.2"')
plt.scatter([crab_ra], [crab_dec], marker='*', color='orangered', s=200, label='Crab Pulsar')
plt.annotate('PSR J0534+2200', (crab_ra, crab_dec), textcoords="offset points", xytext=(10,10), ha='left', color='orangered')

# Add Geminga pulsar (PSR J0633+1746)
geminga_ra = ra_to_degrees('06h33m54.15s')
geminga_dec = dec_to_degrees('+17d46\'12.9"')
plt.scatter([geminga_ra], [geminga_dec], marker='*', color='darkorange', s=200, label='Geminga Pulsar')
plt.annotate('PSR J0633+1746', (geminga_ra, geminga_dec), textcoords="offset points", xytext=(10,10), ha='left', color='darkorange')

# Add Blazar 3C 454.3
blazar_ra = ra_to_degrees('22h53m57.7s')
blazar_dec = dec_to_degrees('+16d08\'53.6"')
plt.scatter([blazar_ra], [blazar_dec], marker='*', color='crimson', s=200, label='Blazar 3C 454.3')
plt.annotate('3C 454.3', (blazar_ra, blazar_dec), textcoords="offset points", xytext=(10,10), ha='left', color='crimson')


plt.legend()
plt.xlabel('Right Ascension (degrees)')
plt.ylabel('Declination (degrees)')
plt.title('VLA Calibrator Sources (ICRS Coordinates)')
plt.grid(True, which='both', axis='both')
plt.xticks(range(0, 361, 30))
plt.yticks(range(-90, 91, 30))
plt.gca().invert_xaxis()

# Add top axis with RA in hour:minute
ax = plt.gca()
ax_top = ax.secondary_xaxis('top')
def deg_to_hm(x):
    h = int(x // 15)
    m = int(round((x / 15 - h) * 60))
    return f"{h:02d}h{m:02d}m"
ra_tick_degs = np.arange(0, 361, 30)
ax_top.set_xticks(ra_tick_degs)
ax_top.set_xticklabels([deg_to_hm(deg) for deg in ra_tick_degs])
ax_top.set_xlabel('Right Ascension (hh:mm)')

plt.show()



# Convert all sources to galactic coordinates
coords = SkyCoord(ra=ra_vals*u.degree, dec=dec_vals*u.degree, frame='icrs')
l_vals = -coords.galactic.l.wrap_at(180*u.degree).radian  # Flip longitude values
b_vals = coords.galactic.b.radian

# Vela pulsar galactic coordinates
vela_coord = SkyCoord(ra=vela_ra*u.degree, dec=vela_dec*u.degree, frame='icrs')
vela_l = -vela_coord.galactic.l.wrap_at(180*u.degree).radian  # Flip longitude values
vela_b = vela_coord.galactic.b.radian

# Crab pulsar galactic coordinates
crab_coord = SkyCoord(ra=crab_ra*u.degree, dec=crab_dec*u.degree, frame='icrs')
crab_l = -crab_coord.galactic.l.wrap_at(180*u.degree).radian  # Flip longitude values
crab_b = crab_coord.galactic.b.radian

# Geminga pulsar galactic coordinates
geminga_coord = SkyCoord(ra=geminga_ra*u.degree, dec=geminga_dec*u.degree, frame='icrs')
geminga_l = -geminga_coord.galactic.l.wrap_at(180*u.degree).radian  # Flip longitude values
geminga_b = geminga_coord.galactic.b.radian

# Blazar 3C 454.3 galactic coordinates
blazar_coord = SkyCoord(ra=blazar_ra*u.degree, dec=blazar_dec*u.degree, frame='icrs')
blazar_l = -blazar_coord.galactic.l.wrap_at(180*u.degree).radian  # Flip longitude values
blazar_b = blazar_coord.galactic.b.radian


plt.figure(figsize=(10, 6))
ax = plt.subplot(111, projection="aitoff")
ax.scatter(l_vals, b_vals, marker='o', color='blue', alpha=0.5)
# for i, name in enumerate(names):
#     ax.annotate(names[i], (l_vals[i], b_vals[i]), textcoords="offset points", xytext=(5,-5), ha='left')

ax.scatter([vela_l], [vela_b], marker='*', color='red', s=200, label='Vela Pulsar')
ax.annotate('PSR J0835-4510', (vela_l, vela_b), textcoords="offset points", xytext=(10,10), ha='left', color='red')

ax.scatter([crab_l], [crab_b], marker='*', color='orangered', s=200, label='Crab Pulsar')
ax.annotate('PSR J0534+2200', (crab_l, crab_b), textcoords="offset points", xytext=(10,10), ha='left', color='orangered')

ax.scatter([geminga_l], [geminga_b], marker='*', color='darkorange', s=200, label='Geminga Pulsar')
ax.annotate('PSR J0633+1746', (geminga_l, geminga_b), textcoords="offset points", xytext=(10,10), ha='left', color='darkorange')

ax.scatter([blazar_l], [blazar_b], marker='*', color='crimson', s=200, label='Blazar 3C 454.3')
ax.annotate('Blazar 3C 454.3', (blazar_l, blazar_b), textcoords="offset points", xytext=(10,10), ha='left', color='crimson')


# Set custom x-tick labels for flipped axis
tick_locs = np.radians(np.linspace(-180, 180, int(360/30 + 1)))  # 30-degree intervals
tick_labels = [f'{round(-1 * np.degrees(loc))}°' for loc in tick_locs]
ax.set_xticks(tick_locs)
ax.set_xticklabels(tick_labels)

ax.set_xlabel('Galactic Longitude (l)')
ax.set_ylabel('Galactic Latitude (b)')
ax.set_title('VLA Calibrator Sources (Galactic Coordinates)')
ax.grid(True)
ax.legend()
plt.tight_layout()
plt.show()
