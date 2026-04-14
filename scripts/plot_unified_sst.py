import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os

def plot_unified_sst():
    nc_path = '/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap-playground/datasets/unified_europe_sst/EUROPE_TOTAL_1KM_SST.nc'
    if not os.path.exists(nc_path):
        print(f"Error: File not found at {nc_path}")
        return

    print("Loading data for plotting...")
    ds = xr.open_dataset(nc_path)
    
    # Take the last time slice
    latest_sst = ds.sst.isel(time=-1)
    
    # Downsample for faster plotting (e.g., take every 5th point)
    # 1km to ~5km
    latest_sst = latest_sst.isel(lat=slice(None, None, 5), lon=slice(None, None, 5))
    
    print("Generating plot...")
    plt.figure(figsize=(12, 10))
    
    # Plot with a nice colormap
    # Using 'magma' or 'coolwarm' for SST
    im = latest_sst.plot(cmap='magma', add_colorbar=True)
    
    plt.title(f"Unified European SST Map - {np.datetime_as_string(latest_sst.time.values, unit='D')}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    
    output_png = '/home/uripratt/Documents/SARTI/PROJECTS/DEGI4ECO/erddap/erddap-playground/scripts/unified_sst_map.png'
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    plt.close()
    
    print(f"Plot saved to {output_png}")

if __name__ == "__main__":
    plot_unified_sst()
