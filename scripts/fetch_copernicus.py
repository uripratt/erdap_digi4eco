import copernicusmarine
import os
import datetime

# Configuration
scripts_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(scripts_dir)
output_folder = os.path.join(base_dir, "datasets", "raw")
os.makedirs(output_folder, exist_ok=True)

products = {
    "MED": "SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2",
    "BAL": "DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE",
    "ATL": "IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE",
    "BS":  "SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2",
    "GLO": "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
}

def download_all(days_history=7):
    # Calculate datetime window for recent data
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days_history)

    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Downloading data from {start_date_str} to {end_date_str}")

    for region, product_id in products.items():
        print(f"--- Downloading {region} Data ---")
        out_dir = os.path.join(output_folder, region)
        os.makedirs(out_dir, exist_ok=True)

        # Copernicus Marine API subset command
        copernicusmarine.subset(
            dataset_id=product_id,
            output_directory=out_dir,
            variables=["analysed_sst"],
            start_datetime=start_date_str,
            end_datetime=end_date_str,
            overwrite=True
        )

if __name__ == "__main__":
    download_all()
