import streamlit as st
import pandas as pd
from survey_parser import parse_gsi_file, parse_landxml_file
import tempfile
import os
import json

st.set_page_config(page_title="Survey Data Converter", layout="wide")
st.title("Survey Data → CSV/GeoJSON")
st.caption("Supports GSI (.gsi) and Leica Infinity LandXML (.xml)")

file = st.file_uploader("Upload GSI or LandXML", type=['gsi', 'xml'])

if file:
    source_file_name = file.name  # Capture the file name here

    if file.name.endswith('.gsi'):
        text = file.read().decode('utf-8', errors='ignore')
        data = parse_gsi_file(text)
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name
        data = parse_landxml_file(tmp_path)
        os.unlink(tmp_path)

    # Add source_file to each record
    for record in data:
        record['source_file'] = source_file_name

    if not data:
        st.warning("No data found.")
    else:
        df = pd.DataFrame(data)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

        keys = ['point_id', 'point_type', 'easting', 'northing', 'elevation', 'hz_angle', 'v_angle', 'slope_dist', 'target_height', 'instrument_height', 'prism_const', 'ppm_atm', 'temperature', 'pressure', 'timestamp', 'code', 'source_file']
        df = df[keys]

        st.success(f"Parsed {len(df)} records")
        st.dataframe(df)

        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "survey.csv", "text/csv")

        if 'easting' in df.columns and 'northing' in df.columns:
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [row.easting, row.northing]}, "properties": dict(row)}
                    for _, row in df.iterrows()
                ]
            }
            st.download_button("Download GeoJSON", json.dumps(geojson, indent=4), "survey.geojson", "application/json")
