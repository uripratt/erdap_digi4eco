# ERDDAP – DEGI4ECO Project

This repository builds upon the **ERDDAP Playground architecture** to deploy a containerized ERDDAP service for high-resolution **European Sea Surface Temperature (SST)** data integration, processing, and visualization.

It extends the base ERDDAP setup with a full **data engineering and geospatial processing pipeline**, including Copernicus Marine data ingestion, multi-basin SST merging, and advanced visualization workflows.

---

# Background: ERDDAP Playground

The project is based on the standard ERDDAP deployment using [Axiom’s docker-erddap image](https://hub.docker.com/r/axiom/docker-erddap).

## Core features

* Fully Dockerized ERDDAP environment
* Portable and reproducible deployment
* Compatible with NetCDF-based datasets

## Project structure

conf/ → ERDDAP configuration (setup.xml, datasets.xml)
datasets/ → NetCDF datasets served by ERDDAP
erddapData/ → Internal ERDDAP logs and system state
scripts/ → Data processing and visualization pipeline

---

# Extended DEGI4ECO Pipeline

This project extends the base playground with a full SST processing workflow over European basins.

---

# Data Processing Pipeline

## 1. Data Acquisition (`fetch_copernicus.py`)

Downloads Copernicus Marine SST products for multiple regions:

* Mediterranean: `SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2`
* Baltic: `DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE`
* Atlantic: `IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE`
* Black Sea: `SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2`
* Global fallback: `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2`

```bash
python scripts/fetch_copernicus.py
```

---

## 2. Mesh Generation (`build_mesh.py`, `build_mesh_3d.py`)

Constructs a unified high-resolution SST mosaic (~1 km) across European seas.

* Priority-based merging: Regional > Global
* Produces consistent spatial coverage
* Supports 2D and 3D reconstructions

```bash
python scripts/build_mesh.py
```

or

```bash
python scripts/build_mesh_3d.py
```

---

## 3. Visualization Pipeline

Scientific visualization modules:

* `plot_unified_sst.py` → SST overview map
* `plot_3d_profile.py` → vertical thermal structure
* `plot_3d_layers.py` → layered 3D reconstruction
* `compare_obsea_models.py` → model benchmarking

Outputs:

* unified_sst_map.png
* temperature_layers_3d.png
* obsea_model_comparison.png

---

# Running the ERDDAP Server

Once datasets are generated and placed in `datasets/`, start the server:

```bash
docker compose up -d
```

ERDDAP will be available at:

[http://localhost:8080/erddap](http://localhost:8080/erddap)

---

# Adding New Datasets

Create a folder inside `datasets/`
Add NetCDF files
Edit `conf/datasets.xml`:

* Set datasetID
* Configure <fileDir> → /datasets/...
* Define metadata and variables
* Ensure coordinate variables:

  * TIME
  * LATITUDE
  * LONGITUDE
  * DEPTH

---

# Documentation

[https://coastwatch.pfeg.noaa.gov/erddap/download/setup.html](https://coastwatch.pfeg.noaa.gov/erddap/download/setup.html)
[https://coastwatch.pfeg.noaa.gov/erddap/download/setupDatasetsXml.html](https://coastwatch.pfeg.noaa.gov/erddap/download/setupDatasetsXml.html)

---

# Project Structure

conf/
├── datasets.xml
├── setup.xml
└── custom_logo.png

datasets/
└── NetCDF files served by ERDDAP

erddapData/
└── logs/

scripts/
├── fetch_copernicus.py
├── build_mesh.py
├── build_mesh_3d.py
├── plot_unified_sst.py
├── plot_3d_profile.py
├── plot_3d_layers.py
└── compare_obsea_models.py

---

# Contact

Author: Oriol Prat
Affiliation: Universitat Politècnica de Catalunya (UPC)
Project: DEGI4ECO / SARTI Group
Contact: [oriol.prat.bayarri@upc.edu](mailto:oriol.prat.bayarri@upc.edu)

