import xarray as xr
import matplotlib.pyplot as plt
import os
import numpy as np
import requests
from PIL import Image
import io

def download_satellite_img(bbox, size=(1200, 800)):
    lon_min, lat_min, lon_max, lat_max = bbox
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox={lon_min},{lat_min},{lon_max},{lat_max}&bboxSR=4326&imageSR=4326&size={size[0]},{size[1]}&format=jpg&f=image"
    
    print(f"Downloading satellite image from ESRI...")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            print(f"Failed to download image: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading satellite image: {e}")
        return None

def plot_obsea_local_dto_satellite():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(scripts_dir)
    nc_path = os.path.join(base_dir, 'datasets', 'unified_europe_3d', 'OBSEA_LOCAL_DTO_3D.nc')
    
    if not os.path.exists(nc_path):
        print(f"Error: Local DTO file not found at {nc_path}")
        return

    print(f"Loading Local DTO: {nc_path}")
    ds = xr.open_dataset(nc_path)
    
    # Metadata from NetCDF
    time_val = ds.time.values
    time_str = np.datetime_as_string(time_val, unit='D')
    source_name = "Copernicus IBI (Atlantic-Iberian-Biscay)"
    
    # BBOX from requested domain
    lon_min, lat_min, lon_max, lat_max = 1.57, 41.15, 1.9, 41.26
    bbox = (lon_min, lat_min, lon_max, lat_max)
    extent = [lon_min, lon_max, lat_min, lat_max]
    
    # Download satellite background
    sat_img = download_satellite_img(bbox)
    
    fig, ax = plt.subplots(figsize=(15, 10))
    
    if sat_img:
        ax.imshow(sat_img, extent=extent, aspect='auto', interpolation='bilinear')
    
    # Overlay Temperature (Surface) with transparency
    temp_surface = ds.temp.isel(depth=0)
    
    im = ax.imshow(temp_surface, extent=extent, origin='lower', cmap='RdYlBu_r', 
                   alpha=0.6, aspect='auto')
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Potential Temperature (°C)", fontsize=12, fontweight='bold')
    
    # OBSEA Position
    obsea_lon, obsea_lat = 1.7525, 41.182167
    ax.plot(obsea_lon, obsea_lat, 'r*', markersize=18, label="OBSEA Observatory", markeredgecolor='white')
    ax.annotate("OBSEA", (obsea_lon, obsea_lat), xytext=(10, 10), 
                textcoords='offset points', color='white', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.4", fc="red", alpha=0.8, ec="white"))
    
    # Title and Labels
    plt.title(f"OBSEA Local DTO - {time_str}\nSurface Temperature Overlay | Source: {source_name}", 
              fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    
    # Explanation of Pixel Sizes (Sub-caption)
    plt.figtext(0.5, 0.01, 
                "Note: 'Stairs' reflect the native IBI resolution (~2.5km) interpolated to 200m. Different pixel looks occur near land masks.", 
                ha="center", fontsize=10, style='italic', bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    
    ax.grid(True, linestyle='--', alpha=0.4, color='white')
    ax.legend(loc='upper right', framealpha=0.9)
    
    output_png = os.path.join(scripts_dir, 'obsea_local_dto_satellite.png')
    plt.savefig(output_png, bbox_inches='tight', dpi=200)
    plt.close()
    
    print(f"Satellite DTO plot saved to {output_png}")

if __name__ == "__main__":
    plot_obsea_local_dto_satellite()
