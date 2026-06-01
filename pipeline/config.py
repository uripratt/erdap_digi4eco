"""
Configuration file for the DEGI4ECO Multi-variable Pipeline.
Defines resolutions, depth requirements, NetCDF variables, and product IDs for each variable.

Resolution Strategy:
  - 2D Native (sst, chl, waves): use native product resolution (res)
  - 3D Surface extraction (temp_3d, sal, cur): use res_surface (~IBI native ~3km)
  - 3D Europe volume: use res_europe_3d (5km, balance quality/performance)
  - 3D OBSEA DTO: use res (0.002° = 200m, upsampled from IBI 3km via hybrid interp)
"""

DOMAINS = {
    "EUROPE": [-12.0, 29.0, 43.0, 73.0],   # min_lon, min_lat, max_lon, max_lat
    "OBSEA":  [1.6,  41.1,  1.9,  41.3],    # ~33km x ~22km box around OBSEA
    # GALWAY: excluded from local ERDDAP
}

PIPELINE_CONFIG = {
    # ── 2D NATIVE PRODUCTS ─────────────────────────────────────────────────────

    "sst": {
        "res":    0.01,          # 1km — native L4 product resolution
        "is_3d":  False,
        "nc_vars": ["analysed_sst"],
        "priority": ["MED", "ATL", "BAL", "BS", "GLO"],
        "products": {
            "MED": "SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2",
            "BAL": "DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE",
            "ATL": "IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE",
            "BS":  "SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2",
            "GLO": "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
        }
    },

    "chl": {
        "res":    0.01,          # 1km — native OC product resolution
        "is_3d":  False,
        "nc_vars": ["CHL"],
        "priority": ["MED", "ATL", "BS", "GLO"],
        "products": {
            "MED": "cmems_obs-oc_med_bgc-plankton_nrt_l4-gapfree-multi-1km_P1D",
            "ATL": "cmems_obs-oc_atl_bgc-plankton_nrt_l4-gapfree-multi-1km_P1D",
            "BS":  "cmems_obs-oc_blk_bgc-plankton_nrt_l4-gapfree-multi-1km_P1D",
            "GLO": "cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D"
        }
    },

    "waves": {
        "res":    0.04,          # 4km — native MED WAV resolution
        "is_3d":  False,
        "nc_vars": ["VHM0", "VMDR", "VTPK"],
        "priority": ["MED", "BS", "GLO"],
        "products": {
            "MED": "cmems_mod_med_wav_anfc_4.2km_PT1H-i",
            "BS":  "cmems_mod_blk_wav_anfc_2.5km_PT1H-i",
            "GLO": "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        }
    },

    # ── 3D PRODUCTS (surface + volume + OBSEA DTO) ────────────────────────────

    "temp_3d": {
        "res":           0.002,  # OBSEA DTO horizontal: 200m (~x15 upsampling from IBI 3km)
        "res_surface":   0.027,  # 2D surface map: native IBI resolution ~3km
        "res_europe_3d": 0.05,   # 3D Europe volume: 5km (balance quality/performance)
        "is_3d":  True,
        "nc_vars": ["thetao"],
        "priority": ["MED", "ATL", "BAL", "BS", "GLO"],
        "products": {
            "MED": "cmems_mod_med_phy-tem_anfc_4.2km_P1D-m",
            "BAL": "cmems_mod_bal_phy_anfc_P1D-m",
            "ATL": "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
            "BS":  "cmems_mod_blk_phy-temp_anfc_2.5km_P1D-m",
            "GLO": "cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m"
        }
    },

    "sal": {
        "res":           0.002,  # OBSEA DTO horizontal: 200m
        "res_surface":   0.027,  # 2D surface map: native IBI ~3km
        "res_europe_3d": 0.05,   # 3D Europe volume: 5km
        "is_3d":  True,
        "nc_vars": ["so"],
        "priority": ["MED", "ATL", "BAL", "BS", "GLO"],
        "products": {
            "MED": "cmems_mod_med_phy-sal_anfc_4.2km_P1D-m",
            "BAL": "cmems_mod_bal_phy_anfc_P1D-m",
            "ATL": "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
            "BS":  "cmems_mod_blk_phy-sal_anfc_2.5km_P1D-m",
            "GLO": "cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m"
        }
    },

    "cur": {
        "res":           0.002,  # OBSEA DTO horizontal: 200m
        "res_surface":   0.027,  # 2D surface map: native IBI ~3km
        "res_europe_3d": 0.05,   # 3D Europe volume: 5km
        "is_3d":  True,
        "nc_vars": ["uo", "vo"],
        "priority": ["MED", "ATL", "BAL", "BS", "GLO"],
        "products": {
            "MED": "cmems_mod_med_phy-cur_anfc_4.2km_P1D-m",
            "BAL": "cmems_mod_bal_phy_anfc_P1D-m",
            "ATL": "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
            "BS":  "cmems_mod_blk_phy-cur_anfc_2.5km_P1D-m",
            "GLO": "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m"
        }
    },
}
