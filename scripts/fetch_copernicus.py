import copernicusmarine
import os
import datetime

# Configuration
scripts_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(scripts_dir)
output_folder = os.path.join(base_dir, "datasets", "raw")
os.makedirs(output_folder, exist_ok=True)

# 2D Satellite Observations (SST)
products = {
    "MED": "SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2",
    "BAL": "DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE",
    "ATL": "IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE",
    "BS":  "SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2",
    "GLO": "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
}

# 3D Physical Models (Analysis & Forecast)
# Variable: thetao (Potential Temperature)
physics_3d_products = {
    "MED": "cmems_mod_med_phy-tem_anfc_4.2km_P1D-m",
    "BAL": "cmems_mod_bal_phy_anfc_P1D-m",
    "ATL": "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
    "BS":  "cmems_mod_blk_phy-temp_anfc_2.5km_P1D-m",
    "GLO": "cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m"
}

def download_all(days_history=7, bbox=(-12, 29, 43, 73)):
    # Calculate datetime window for recent data
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days_history)

    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Downloading 2D SST data from {start_date_str} to {end_date_str} (BBOX: {bbox})")

    for region, product_id in products.items():
        print(f"--- Downloading {region} 2D Data ---")
        out_dir = os.path.join(output_folder, region)
        os.makedirs(out_dir, exist_ok=True)

        try:
            copernicusmarine.subset(
                dataset_id=product_id,
                output_directory=out_dir,
                variables=["analysed_sst"],
                start_datetime=start_date_str,
                end_datetime=end_date_str,
                minimum_longitude=bbox[0],
                minimum_latitude=bbox[1],
                maximum_longitude=bbox[2],
                maximum_latitude=bbox[3],
                overwrite=True
            )
        except Exception as e:
            print(f"  Warning: Failed to download 2D data for {region}: {e}")

def download_3d_all(days_history=1, depth_range=(0, 100), bbox=(-12, 29, 43, 73)):
    # 3D models are heavier, default to 1 day if not specified
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days_history)

    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    output_folder_3d = os.path.join(base_dir, "datasets", "raw_3d")
    os.makedirs(output_folder_3d, exist_ok=True)

    print(f"Downloading 3D Physics data ({depth_range[0]}m to {depth_range[1]}m) from {start_date_str} to {end_date_str} (BBOX: {bbox})")

    for region, dataset_id in physics_3d_products.items():
        print(f"--- Downloading {region} 3D Data ---")
        out_dir = os.path.join(output_folder_3d, region)
        os.makedirs(out_dir, exist_ok=True)

        try:
            copernicusmarine.subset(
                dataset_id=dataset_id,
                output_directory=out_dir,
                variables=["thetao"],
                start_datetime=start_date_str,
                end_datetime=end_date_str,
                minimum_depth=depth_range[0],
                maximum_depth=depth_range[1],
                minimum_longitude=bbox[0],
                minimum_latitude=bbox[1],
                maximum_longitude=bbox[2],
                maximum_latitude=bbox[3],
                overwrite=True
            )
        except Exception as e:
            print(f"  Warning: Failed to download 3D data for {region}: {e}")

if __name__ == "__main__":
    # If run standalone, defaults to 2D
    download_all()
