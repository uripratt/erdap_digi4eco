import requests
import xarray as xr
from bs4 import BeautifulSoup
import pandas as pd

datasets = {
    'Chlorophyll': 'unified_europe_chl',
    'Sea Surface Currents': 'unified_europe_cur_surface',
    'Sea Surface Salinity': 'unified_europe_sal_surface',
    'SST': 'unified_europe_sst',
    'Waves': 'unified_europe_waves',
    'Temp 3D': 'unified_europe_temp_surface'
}

base_url = 'http://188.73.202.45:8080/erddap'

print("=== Checking File Groupings (/files/ endpoint) ===")
for name, ds_id in datasets.items():
    url = f"{base_url}/files/{ds_id}/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Assuming files are listed in an HTML table or links
            links = [a.text for a in soup.find_all('a') if a.text.endswith('.nc')]
            print(f"[{name}] ({ds_id}): Found {len(links)} NetCDF files.")
            for link in links:
                print(f"  - {link}")
        else:
            print(f"[{name}] ({ds_id}): Error accessing files (status code {response.status_code})")
    except Exception as e:
        print(f"[{name}] ({ds_id}): Exception: {e}")

print("\n=== Checking Daily Data Coverage via OPeNDAP ===")
for name, ds_id in datasets.items():
    opendap_url = f"{base_url}/griddap/{ds_id}"
    try:
        # Open dataset metadata via OPeNDAP
        ds = xr.open_dataset(opendap_url)
        time_vals = pd.to_datetime(ds['time'].values)
        
        # Check if April and May exist
        april_may_data = time_vals[(time_vals.month.isin([4, 5]))]
        
        if len(april_may_data) > 0:
            start = april_may_data.min()
            end = april_may_data.max()
            num_days = len(april_may_data)
            
            # Check for daily frequency in April and May
            # Calculate expected number of days
            expected_days = (end.date() - start.date()).days + 1
            
            # Check if there are daily gaps
            unique_dates = pd.Series(april_may_data.date).unique()
            
            print(f"[{name}]: Time coverage from {start.date()} to {end.date()} ({len(unique_dates)} unique days out of expected {expected_days} days).")
            if len(unique_dates) == expected_days:
                print(f"  -> SUCCESS: Daily data is present for April and May without gaps.")
            else:
                print(f"  -> WARNING: Missing {expected_days - len(unique_dates)} days.")
        else:
            print(f"[{name}]: NO data found for April and May.")
    except Exception as e:
        print(f"[{name}] ({ds_id}): OPeNDAP Exception: {e}")

