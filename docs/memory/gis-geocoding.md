# GIS and Geocoding

## GIS Fallback Chain

For each document, the system tries to determine if the location is within a protected area:

```
1. Parse katastralne_uzemia from LLM output
   └── if parcels found:
       cadastral_parcels_ogc.get_geometry_of_a_parcel_set()
           → queries Slovak cadastral OGC API (skgeodesy.sk via proxy)
           → returns GeoDataFrame with parcel polygons
           → get_intersections_with_protected_areas(gdf)
               → intersect with data/protected_areas/ shapefiles
               → sets je_v_chranenom_uzemi in analysis.json

2. If no parcels or OGC returns nothing:
   gis_geocoding.get_geometry_of_a_geoname(nazov_lokality, obec, okres, kraj)
       → Nominatim (OpenStreetMap) geocoding
       → tries several query combinations (locality+obec, locality+okres, etc.)
       → returns GeoDataFrame with polygon/point geometry

3. If Nominatim fails:
   gis_overpass.py queries Overpass API for named areas
```

## Cadastral OGC API (`cadastral_parcels_ogc.py`)

- URL base: `https://kataster.skgeodesy.sk/...` (accessed via proxy)
- **Proxy setup:** set `GIS_PROXY_URL` and `GIS_PROXY_AUTH` env vars. The proxy receives
  the original URL as `?url=<original>` and authenticates with `X-Proxy-Auth: $GIS_PROXY_AUTH`.
- Parcel types: `C` (C-KN, register C) and `E` (E-KN, register E) — both queried separately
- Uses `nationalCadastralZoningReference` (katastrálne územie code) to narrow queries
- Retry logic: HTTP 500 errors are retried with delays [5, 10, 30, 60, 120] seconds

## Protected Areas Data

- Location: `data/protected_areas/` (GITIGNORED — sync from CI artifacts)
- Format: GIS shapefiles (.shp)
- Covers 5th-degree protection reserves (prírodné rezervácie) and Natura 2000 (ÚEV/SKUEV)
- Sync command: `bash analyzer/sync_github_data.sh`

## Nominatim Geocoding (`gis_geocoding.py`)

- Base URL: `https://nominatim.openstreetmap.org/search?format=geojson&polygon_geojson=1&accept-language=sk&q=`
- Requires `User-Agent: VLK_Uradne_Nastenky_Analyzer/1.0` header
- `nazov_lokality_norm` from `analysis.json` is used as query (LLM pre-normalizes it)
- Returns only Polygon/MultiPolygon features (not points) for area intersections
- The function tries multiple query combinations in order (most specific first)

## GIS Libraries

- `geopandas` 1.1.1 — main GIS operations, CRS handling
- `shapely` 2.1.2 — geometry operations
- `pyproj` 3.7.1 — coordinate reference system transformations
- Data stored as `GeoDataFrame` with CRS `EPSG:4326` (WGS84)
