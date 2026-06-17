import os
import glob
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

base_dir = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/datasets"
output_path = "/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap_digi4models/plots/data_availability_2026.png"

# Ensure output directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

folders = {
    "SST (1km)": "unified_europe_sst",
    "Chlorophyll (1km)": "unified_europe_chl",
    "Waves (4km)": "unified_europe_waves",
    "Salinity (3km)": "unified_europe_sal_surface",
    "Currents (3km)": "unified_europe_cur_surface"
}

# Modern scientific color palette
colors = {
    "SST (1km)": "#e74c3c",          # Red
    "Chlorophyll (1km)": "#2ecc71",  # Green
    "Waves (4km)": "#9b59b6",        # Purple
    "Salinity (3km)": "#f1c40f",     # Yellow
    "Currents (3km)": "#3498db"      # Blue
}

print("Scanning NetCDF files for time coverage...")

data = []

for var_name, folder in folders.items():
    print(f"Processing {var_name}...")
    files = sorted(glob.glob(os.path.join(base_dir, folder, "*.nc")))
    
    for f in files:
        try:
            ds = xr.open_dataset(f)
            if 'time' in ds.dims and ds.dims['time'] > 0:
                times = pd.to_datetime(ds.time.values)
                t_start = times.min()
                t_end = times.max()
                
                data.append({
                    "Variable": var_name,
                    "Start": t_start,
                    "End": t_end
                })
            ds.close()
        except Exception as e:
            print(f"Error reading {f}: {e}")

df = pd.DataFrame(data)

if df.empty:
    print("No data found to plot!")
    exit(1)

print("Generating plot...")

# Setup plot
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

# Y-axis positions
variables = list(folders.keys())
y_positions = {var: i for i, var in enumerate(reversed(variables))}

# Plotting bars
bar_height = 0.4
for _, row in df.iterrows():
    var = row['Variable']
    y = y_positions[var]
    start = mdates.date2num(row['Start'])
    end = mdates.date2num(row['End'])
    
    # Draw a line from start to end with thickness
    ax.plot([row['Start'], row['End']], [y, y], 
            color=colors[var], linewidth=12, solid_capstyle='butt', alpha=0.85)

# Formatting
ax.set_yticks(list(y_positions.values()))
ax.set_yticklabels(list(y_positions.keys()), fontsize=12, fontweight='bold')

# X-axis dates
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b'))
ax.xaxis.set_minor_locator(mdates.DayLocator([1, 15]))
plt.xticks(rotation=45, ha='right', fontsize=11)

# Grid and styling
ax.grid(True, axis='x', linestyle='--', alpha=0.7)
ax.grid(False, axis='y')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.set_facecolor('#fdfdfd')
fig.patch.set_facecolor('#ffffff')

# Add title and labels
plt.title("Cobertura Temporal de Datasets 2D Consolidados (DEGI4ECO)", 
          fontsize=16, fontweight='bold', pad=20, loc='left')
plt.xlabel("Línea de Tiempo", fontsize=12, fontweight='bold', labelpad=10)

# Annotations / Legend for clarity
plt.figtext(0.05, 0.02, "Generado automáticamente desde los archivos NetCDF mensuales en ./datasets", 
            fontsize=9, color="gray", style='italic')

plt.tight_layout()
plt.savefig(output_path, bbox_inches='tight')
print(f"Plot saved successfully to {output_path}")

