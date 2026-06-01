import requests
import os

def download_bathymetry():
    base_url = "http://188.73.202.45:8080/erddap/griddap"
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(scripts_dir), "datasets", "bathymetry")
    os.makedirs(output_dir, exist_ok=True)

    datasets = {
        "OBSEA": {
            "id": "unified_europe_bathymetry_100m",
            "bbox": [41.08, 41.32, 1.55, 1.95],
            "var": "elevation"
        },
        "GALWAY": {
            "id": "galway_bay_bathymetry",
            "bbox": [53.0, 53.4, -9.5, -8.9],
            "var": "elevation"
        }
    }

    for domain, info in datasets.items():
        print(f"Downloading bathymetry for {domain}...")
        url = f"{base_url}/{info['id']}.nc?{info['var']}[({info['bbox'][0]}):({info['bbox'][1]})][({info['bbox'][2]}):({info['bbox'][3]})]"
        
        output_path = os.path.join(output_dir, f"{domain}_bathymetry.nc")
        
        try:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  Successfully saved to {output_path}")
        except Exception as e:
            print(f"  Error downloading {domain}: {e}")

if __name__ == "__main__":
    download_bathymetry()
