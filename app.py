# file: app.py
import streamlit as st
import pandas as pd
from survey_parser import parse_gsi_file, parse_landxml_file
import tempfile
import os

st.set_page_config(page_title="Survey Data Converter", layout="wide")
st.title("Survey Data → CSV/GeoJSON")
st.caption("Supports GSI (.gsi) and Leica Infinity LandXML (.xml)")

uploaded_file = st.file_uploader(
    "Upload GSI or LandXML file",
    type=['gsi', 'xml', 'GSI', 'XML']
)

if uploaded_file:
    # Save to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    # Parse
    try:
        if uploaded_file.name.lower().endswith('.gsi'):
            text = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            data = parse_gsi_file(text)
        else:
            data = parse_landxml_file(tmp_path)
    except Exception as e:
        st.error(f"Parsing failed: {e}")
        os.unlink(tmp_path)
        st.stop()

    os.unlink(tmp_path)

    if not data:
        st.warning("No data found.")
        st.stop()

    df = pd.DataFrame(data)

    # Clean timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Reorder columns
    cols = ['point_id', 'point_type', 'easting', 'northing', 'elevation',
            'hz_angle', 'v_angle', 'slope_dist', 'target_height', 'instrument_height',
            'prism_const', 'ppm_atm', 'temperature', 'pressure', 'timestamp', 'code']
    df = df[[c for c in cols if c in df.columns]]

    # Display
    st.success(f"Parsed {len(df)} records")
    st.dataframe(df, use_container_width=True)

    # Download CSV
    csv = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        data=csv,
        file_name=f"survey_{uploaded_file.name.split('.')[0]}.csv",
        mime="text/csv"
    )

    # Download GeoJSON
    if all(c in df.columns for c in ['easting', 'northing']):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row.easting, row.northing]
                    },
                    "properties": {k: v for k, v in row.items() if pd.notna(v)}
                }
                for _, row in df.iterrows()
            ]
        }
        import json
        geojson_str = json.dumps(geojson, indent=2)
        st.download_button(
            "Download GeoJSON",
            data=geojson_str,
            file_name=f"survey_{uploaded_file.name.split('.')[0]}.geojson",
            mime="application/json"
        )
