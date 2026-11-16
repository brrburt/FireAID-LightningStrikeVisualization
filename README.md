# FireAID: Lightning Strike and Wildfire Prediction

Historical Wildfire, Lightning Strike, and Satellite Embedding Visualization

Bryan Burton, 2026

## Software Requirements
python >=3.14.10

Google Earth Engine

## How to Run

1. Create a python virtual environment; install the packages in ``requirements.txt``
2. Create project on Google Earth Engine
3. Copy the project ID and paste into ``PROJECT_ID``
4. Download the GeoJSON datasets from the [Alaska Interagency Coordination Center](https://fire.ak.blm.gov/predsvcs/maps.php)
   * [Alaska Fire History - Location Points](https://fire.ak.blm.gov/content/maps/aicc/Data/Data%20(zipped%20geojson)/AlaskaFireHistory_LocationPoints_NAD83_geojson.zip)
   * [Historical Lightning Points, 1986 - 2012](https://fire.ak.blm.gov/content/maps/aicc/Data/Data%20(zipped%20geojson)/Historical_Lightning_Points_1986_2012_geojson.zip)
   * [Alaska Fire History - Perimeter Polygons](https://fire.ak.blm.gov/content/maps/aicc/Data/Data%20(zipped%20geojson)/AlaskaFireHistory_PerimeterPolygons_AKAlbersNAD83_geojson.zip)
5. Place downloaded GeoJSON datasets into the ``Datasets`` directory
6. Launch the visualization using ``streamlit run LightningStrikeVisStreamlit.py``


