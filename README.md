# ERDDAP - DEGI4ECO

Este proyecto despliega un servidor ERDDAP para la visualización de datos de Temperatura Superficial del Mar (SST) de Europa.

## Descarga de Datos

Los archivos de datos (`.nc`) deben descargarse de la web de **Copernicus Marine Service**. 

### Productos requeridos:
Los siguientes productos son necesarios para recrear el mosaico unificado de SST:

- **Mediterráneo (MED):** `SST_MED_SST_L4_NRT_OBSERVATIONS_010_004_a_V2`
- **Báltico (BAL):** `DMI-BALTIC-SST-L4-NRT-OBS_FULL_TIME_SERIE`
- **Atlántico (ATL):** `IFREMER-ATL-SST-L4-NRT-OBS_FULL_TIME_SERIE`
- **Mar Negro (BS):** `SST_BS_SST_L4_NRT_OBSERVATIONS_010_006_a_V2`
- **Global (GLO):** `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` (Usado como capa de respaldo global OSTIA)

Puedes usar el script proporcionado para automatizar la descarga si tienes configuradas las credenciales de `copernicusmarine`:
```bash
python scripts/fetch_copernicus.py
```

## Ejecución

Para levantar el servidor ERDDAP usando Docker:
```bash
docker compose up -d
```

El servidor estará disponible en: [http://localhost:8080/erddap](http://localhost:8080/erddap)

## Organización del Proyecto

- `conf/`: Archivos de configuración de ERDDAP (`datasets.xml`, `setup.xml`).
- `datasets/`: Directorio donde se almacenan los archivos NetCDF.
- `scripts/`: Scripts para la descarga y procesado de los datos.
