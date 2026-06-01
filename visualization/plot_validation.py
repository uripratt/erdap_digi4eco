import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import contextily as ctx
from pipeline.config import PIPELINE_CONFIG, DOMAINS

def plot_validation_raw_vs_unified(var_name, config_dict):
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    plots_dir = os.path.join(base_dir, "plots", "validation")
    os.makedirs(plots_dir, exist_ok=True)

    conf = config_dict[var_name]
    bbox = DOMAINS["OBSEA"]
    
    # 1. FIND RAW FILE
    is_3d = conf.get("is_3d", False)
    raw_folder = f"{var_name}_europe_column" if is_3d else var_name
    raw_pattern = os.path.join(base_dir, "datasets", "raw", raw_folder, "MED", "*.nc")
    raw_files = sorted(glob.glob(raw_pattern))
    if not raw_files: return
    raw_file = raw_files[-1]
    
    # 2. FIND UNIFIED FILE
    unified_dir = os.path.join(base_dir, "datasets", f"unified_europe_{var_name}")
    uni_files = sorted(glob.glob(os.path.join(unified_dir, "*.nc")))
    if not uni_files: return
    uni_file = uni_files[-1]

    # 3. LOAD DATA
    ds_raw = xr.open_dataset(raw_file)
    ds_uni = xr.open_dataset(uni_file)
    
    if 'latitude' in ds_raw.coords: ds_raw = ds_raw.rename({'latitude': 'lat', 'longitude': 'lon'})
    
    if 'depth' in ds_raw.dims: ds_raw = ds_raw.isel(depth=0)
    if 'time' in ds_raw.dims: ds_raw = ds_raw.isel(time=-1)
    if 'depth' in ds_uni.dims: ds_uni = ds_uni.isel(depth=0)
    if 'time' in ds_uni.dims: ds_uni = ds_uni.isel(time=-1)

    # 4. LOAD BATHYMETRY
    bat_path = os.path.join(base_dir, "datasets/bathymetry/OBSEA_bathymetry.nc")
    ds_bat = xr.open_dataset(bat_path).rename({'latitude': 'lat', 'longitude': 'lon'})
    # Ensure bat covers the display area
    ds_bat_plot = ds_bat.sel(lat=slice(bbox[1], bbox[3]), lon=slice(bbox[0], bbox[2]))

    # Unit Conversion
    def clean_da(da):
        da_val = da.compute()
        if np.nanmax(da_val) > 100: da_val = da_val - 273.15
        return da_val

    # Variable Extraction
    if var_name == "cur":
        raw_full = np.sqrt(ds_raw["uo"]**2 + ds_raw["vo"]**2)
        uni_full = np.sqrt(ds_uni["uo"]**2 + ds_uni["vo"]**2)
    else:
        raw_full = clean_da(ds_raw[conf["nc_vars"][0]])
        uni_full = clean_da(ds_uni[conf["nc_vars"][0]])

    # 5. OPTIMIZED RANGES FOR CONTRAST
    style_config = {
        "sst": {"cmap": "magma", "label": "Temperature (°C)", "range": (15.5, 18.5)},
        "chl": {"cmap": "YlGn", "label": "Chlorophyll-a (mg/m³)", "range": (0.05, 0.8)},
        "sal": {"cmap": "viridis", "label": "Salinity (PSU)", "range": (37.2, 38.2)},
        "temp_3d": {"cmap": "magma", "label": "Temperature (°C)", "range": (15.5, 18.5)},
        "cur": {"cmap": "plasma", "label": "Current Speed (m/s)", "range": (0, 0.25)},
    }
    style = style_config.get(var_name, {"cmap": "viridis", "label": var_name, "range": (None, None)})
    vmin, vmax = style["range"]

    # 6. HIGH-RES INTERPOLATION (On the fly)
    plot_res = 0.002
    new_lat = np.arange(bbox[1], bbox[3], plot_res)
    new_lon = np.arange(bbox[0], bbox[2], plot_res)
    
    # BUFFERED EXTRACTION TO PREVENT EDGE ARTIFACTS
    buffer = 0.2
    uni_buffered = uni_full.sel(lat=slice(bbox[1]-buffer, bbox[3]+buffer), 
                                lon=slice(bbox[0]-buffer, bbox[2]+buffer))
    
    # Fill internal NaNs in source before interpolating (Aggressive filling)
    uni_filled = uni_buffered.interpolate_na(dim="lon", method="nearest", fill_value="extrapolate")
    uni_filled = uni_filled.interpolate_na(dim="lat", method="nearest", fill_value="extrapolate")

    # Interpolate to high-res
    uni_data = uni_filled.interp(lat=new_lat, lon=new_lon, method="linear")
    uni_data = uni_data.fillna(uni_filled.interp(lat=new_lat, lon=new_lon, method="nearest"))
    
    # Mask with high-res bathymetry
    bat_interp = ds_bat["elevation"].interp(lat=new_lat, lon=new_lon, method="linear")
    uni_data = uni_data.where(bat_interp < 0)

    # Raw Sample (Cropped for display)
    raw_data = raw_full.sel(lat=slice(bbox[1], bbox[3]), lon=slice(bbox[0], bbox[2]))

    # 7. PLOT
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 9), dpi=150)
    
    for ax, data, title in zip([ax1, ax2], [raw_data, uni_data], ["RAW COPERNICUS DATA", "DEGI4ECO UNIFIED MESH"]):
        im = ax.pcolormesh(data.lon, data.lat, data.values, cmap=style["cmap"], vmin=vmin, vmax=vmax, shading='auto')
        cbar = plt.colorbar(im, ax=ax, label=style["label"], extend='both')
        ax.set_title(f"{title}\n(OBSEA Digital Twin Zoom)", fontsize=14, fontweight='bold')
        
        # Bathymetry Contours
        levels = sorted([-20, -50, -100, -200])
        cs = ax.contour(ds_bat_plot.lon, ds_bat_plot.lat, ds_bat_plot.elevation, levels=levels, 
                        colors='white', linewidths=1.0, alpha=0.7)
        ax.clabel(cs, inline=True, fontsize=9, fmt='%d m')
        
        # Basemap
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, crs=4326, alpha=0.4)
        except: pass
        
        ax.set_xlabel("Longitude (°E)")
        ax.set_ylabel("Latitude (°N)")
        ax.grid(True, linestyle=':', alpha=0.5)

    plt.suptitle(f"DEGI4ECO Scientific Validation: {var_name.upper()}\nHigh-Fidelity Coastal Interpolation & Mesh Synthesis", 
                 fontsize=20, y=1.02, fontweight='bold')
    
    output_png = os.path.join(plots_dir, f'validation_{var_name}_comparison.png')
    plt.tight_layout()
    plt.savefig(output_png, bbox_inches='tight')
    plt.close()
    print(f"Validation plot saved to {output_png}")

if __name__ == "__main__":
    for v in ["sst", "sal", "temp_3d", "cur"]:
        print(f"Validating {v}...")
        try: plot_validation_raw_vs_unified(v, PIPELINE_CONFIG)
        except Exception as e: print(f"Error: {e}")
