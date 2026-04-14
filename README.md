# ERDDAP - DEGI4ECO Project

This repository manages an ERDDAP service designed to visualize high-resolution European Sea Surface Temperature (SST) data. It builds upon the **erddap-playground** architecture to provide a containerized environmental data server.

## Background: ERDDAP Playground

The project uses a standard ERDDAP deployment based on [Axiom's docker-erddap image](https://hub.docker.com/r/axiom/docker-erddap). 
- **Dockerized Environment**: The entire service is encapsulated in Docker, ensuring portability and ease of setup.
- **Project Structure**:
    - `conf/`: Contains `setup.xml` (server settings) and `datasets.xml` (dataset definitions).
    - `datasets/`: The data repository where NetCDF (`.nc`) files are stored and served.
    - `erddapData/`: Internal ERDDAP storage for logs and state.

## Data Processing Pipeline

The project includes a series of Python scripts to automate the acquisition and merging of Copernicus Marine datasets.

### 1. Data Acquisition (`fetch_copernicus.py`)
This script downloads the required NetCDF files from the **Copernicus Marine Service**. You must have your Copernicus credentials configured to use it.

**Required Products:**
- **Mediterranean:** `SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2`
- **Baltic:** `DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE`
- **Atlantic:** `IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE`
- **Black Sea:** `SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2`
- **Global:** `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` (Used as a fallback for full coverage)

Run the script:
```bash
python scripts/fetch_copernicus.py
```

### 2. Mesh Generation (`build_mesh.py`)
Combines the regional datasets into a unified 1km resolution European SST mosaic. It uses a priority merging strategy (Regional > Global) to ensure the highest resolution data is used where available.

Run the script:
```bash
python scripts/build_mesh.py
```

### 3. Visualization (`plot_unified_sst.py`)
Generates a static map (`unified_sst_map.png`) of the latest processed data for quick verification.

Run the script:
```bash
python scripts/plot_unified_sst.py
```

## Running the Server

Once the data is processed and located in the `datasets/` folder, you can start the ERDDAP server:

```bash
docker compose up -d
```

The server will be available at: [http://localhost:8080/erddap](http://localhost:8080/erddap)
