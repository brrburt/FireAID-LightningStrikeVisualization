import json
from pathlib import Path
import ee
import folium
from folium.plugins import HeatMap
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Page Configuration
st.set_page_config(
    page_title="Alaska Wildfire & Lightning Viewer",
    layout="wide"
)

PROJECT_ID = 'YOUR PROJECT ID HERE'

# Initialize Earth Engine
@st.cache_resource
def init_earth_engine():
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        try:
            ee.Authenticate()
            ee.Initialize(project=PROJECT_ID)
        except Exception as e:
            st.error(f"Earth Engine initialization failed: {e}")

init_earth_engine()

# Load and Cache Dataset Files
@st.cache_data
def load_data():
    def load_geojson_data(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)

    def load_lightning_data(filepath):
        data = load_geojson_data(filepath)
        records = []
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            records.append({
                'lat': props.get('LAT'),
                'lon': props.get('LON'),
                'striketime': props.get('STRIKETIME')
            })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['striketime'])
        return df

    lightning_df = load_lightning_data(Path('./Datasets/ImpactSystemLightning_Points_1986_2012_NAD83.geojson'))
    fire_perimeters_df = load_geojson_data(Path('./Datasets/AlaskaFireHistory_Polygons_AKAlbersNAD83_geojson.geojson'))
    fire_points_df = load_geojson_data(Path('./Datasets/AlaskaFireHistory_Points_NAD83_geojson.geojson'))
    
    return lightning_df, fire_perimeters_df, fire_points_df

lightning_df, fire_perimeters_df, fire_points_df = load_data()

# Streamlit Sidebar Controls
st.sidebar.header("Control Panel")

min_date = lightning_df['time'].dt.date.min()
max_date = lightning_df['time'].dt.date.max()

start_date = st.sidebar.date_input('Start Date', value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input('End Date', value=max_date, min_value=min_date, max_value=max_date)

EMBEDDING_YEARS = list(range(2017, 2025))
selected_embedding_years = st.sidebar.multiselect(
    'Embedding Years',
    options=EMBEDDING_YEARS,
    default=[2023]
)

st.title("Alaska Lightning and Wildfire History Dashboard")

if start_date > end_date:
    st.error('Error: Start date must be before or equal to the end date.')
else:
    # 1. Filter individual lightning strikes by date range
    mask = (lightning_df['time'].dt.date >= start_date) & (lightning_df['time'].dt.date <= end_date)
    filtered_lightning = lightning_df[mask]

    # 2. Filter Wildfire Perimeters GeoJSON by PERIMETERDATE range
    filtered_perim_features = []
    for feature in fire_perimeters_df.get('features', []):
        perim_date_str = feature.get('properties', {}).get('PERIMETERDATE')
        if perim_date_str:
            try:
                perim_date = pd.to_datetime(perim_date_str).date()
                if start_date <= perim_date <= end_date:
                    filtered_perim_features.append(feature)
            except Exception:
                continue

    filtered_perim_geojson = {
        'type': 'FeatureCollection',
        'features': filtered_perim_features,
    }

    # 3. Filter Fire History Point Dataset by DISCOVERYDATETIME range
    filtered_fire_point_features = []
    for feature in fire_points_df.get('features', []):
        props = feature.get('properties', {})
        disc_time_ms = props.get('DISCOVERYDATETIME')
        if disc_time_ms:
            try:
                disc_date = pd.to_datetime(disc_time_ms, unit='ms').date()
                if start_date <= disc_date <= end_date:
                    filtered_fire_point_features.append(feature)
            except Exception:
                continue

    filtered_fire_points_geojson = {
        'type': 'FeatureCollection',
        'features': filtered_fire_point_features,
    }

    # Create Base Map
    m = folium.Map(location=[64.0, -152.0], zoom_start=4, tiles='openstreetmap')

    # Layer 1: Google Earth Engine Satellite Embeddings
    if selected_embedding_years:
        try:
            embeddings_col = (
                ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')
                .filterDate(f'{min(selected_embedding_years)}-01-01', f'{max(selected_embedding_years) + 1}-01-01')
            )
            
            embedding_image = embeddings_col.mean()
            vis_params = {'bands': ['A10', 'A32', 'A55'], 'min': -0.3, 'max': 0.3}

            map_id_dict = embedding_image.getMapId(vis_params)
            tile_url = map_id_dict['tile_fetcher'].url_format

            years_label = ", ".join(map(str, sorted(selected_embedding_years)))
            folium.TileLayer(
                tiles=tile_url,
                attr='Google Earth Engine',
                name=f'Satellite Embeddings ({years_label})',
                overlay=True,
                control=True,
            ).add_to(m)
        except Exception as e:
            st.warning(f"Failed to load GEE layer: {e}")

    # Layer 2: Point Density Heatmap (Lightning Strikes)
    if not filtered_lightning.empty:
        heat_data = filtered_lightning[['lat', 'lon']].values.tolist()
        HeatMap(
            heat_data,
            radius=15,
            blur=12,
            max_opacity=0.8,
            name='Lightning Strike Density',
        ).add_to(m)

    # Layer 3: Wildfire Perimeters
    if filtered_perim_geojson['features']:
        tooltip_perim = folium.GeoJsonTooltip(
            fields=['NAME', 'ACRES', 'FIREYEAR', 'PERIMETERDATE'],
            aliases=['Name:', 'Acres:', 'Fire Year:', 'Date:'],
            localize=True,
            sticky=True,
        )

        folium.GeoJson(
            filtered_perim_geojson,
            name='Wildfire Perimeters',
            style_function=lambda feature: {
                'fillColor': '#ff0000',
                'color': '#990000',
                'weight': 2,
                'fillOpacity': 0.4,
            },
            tooltip=tooltip_perim,
        ).add_to(m)

    # Layer 4: Fire History Point Dataset
    if filtered_fire_points_geojson['features']:
        tooltip_points = folium.GeoJsonTooltip(
            fields=['NAME', 'FIRESEASON', 'GENERALCAUSE', 'ESTIMATEDTOTALACRES'],
            aliases=['Fire Name:', 'Season:', 'Cause:', 'Est. Acres:'],
            localize=True,
            sticky=True,
        )

        folium.GeoJson(
            filtered_fire_points_geojson,
            name='Historical Fire Points',
            marker=folium.CircleMarker(
                radius=6,
                color='#ff7800',
                fill=True,
                fill_color='#ff5500',
                fill_opacity=0.7,
                weight=1
            ),
            tooltip=tooltip_points,
        ).add_to(m)

    folium.LayerControl().add_to(m)

    # Render map in Streamlit
    st_folium(m, width=1200, height=700)