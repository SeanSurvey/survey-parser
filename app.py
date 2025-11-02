import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import os
import io  # For in-memory file handling

# Safe import with fallback
try:
    from survey_parser import parse_gsi_file, parse_landxml_file
    PARSER_AVAILABLE = True
except ImportError as e:
    st.error(f"Parser import failed: {e}. Using fallback GSI parser.")
    PARSER_AVAILABLE = False

    # Fallback simple GSI parser (no XML support)
    def parse_gsi_file(content):
        data = []
        current = {}
        for line_num, line in enumerate(content.splitlines(), 1):
            words = line.strip().split()
            for word in words:
                if len(word) < 7:
                    continue
                wi = word[0:2].lstrip('*')
                sign = word[6]
                val_str = sign + word[7:].strip()
                if wi == '11':
                    current['point_id'] = val_str.lstrip('+0')
                elif wi == '81':
                    current['easting'] = float(val_str) / 1000
                elif wi == '82':
                    current['northing'] = float(val_str) / 1000
                elif wi == '83':
                    current['elevation'] = float(val_str) / 1000
                elif wi == '87':
                    current['target_height'] = float(val_str) / 1000
                elif wi == '88':
                    current['instrument_height'] = float(val_str) / 1000
                    current['point_type'] = 'SP'
                elif wi == '21':
                    current['hz_angle'] = float(val_str) / 100000
                    current['point_type'] = 'OBS'
                elif wi == '31':
                    current['slope_dist'] = float(val_str) / 1000
                elif wi == '71':
                    current['code'] = val_str.strip('+')
            if current and 'point_id' in current:
                data.append(current)
                current = {}
        return data

    def parse_landxml_file(filepath):
        st.warning("XML support disabled in fallback. Upload GSI instead.")
        return []

st.set_page_config(page_title="Survey Data Converter", layout="wide")
st.title("Survey Data → CSV/GeoJSON")
st.caption("Supports GSI (.gsi) and Leica Infinity LandXML (.xml)")

uploaded_file = st.file_uploader(
    "Upload GSI or LandXML file",
    type=['gsi', 'xml', 'GSI', 'XML']
)

if uploaded_file is not None:
    # Handle in-memory for small files
    content = uploaded_file.read()
    file_ext = uploaded_file.name.lower().split('.')[-1]

    # Parse
    try:
        if file_ext == 'gsi':
            text = io.BytesIO(content).read().decode('utf-8', errors='ignore')
            data = parse_gsi_file(text)
        else:
            # Write to temp for XML
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            data = parse_landxml_file(tmp_path)
            os.unlink(tmp_path)

        if not data:
            st.warning("No data found in file.")
            st.stop()

        df = pd.DataFrame(data)

        # Clean timestamp if present
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

        # Reorder columns
        cols = ['point_id', 'point_type', 'easting', 'northing', 'elevation',
                'hz_angle', 'v_angle', 'slope_dist', 'target_height', 'instrument_height',
                'prism_const', 'ppm_atm', 'temperature', 'pressure', 'timestamp', 'code']
        df = df[[c for c in cols if c in df.columns]]

        # Display
        st.success(f"Parsed {len(df)} records")
        st.dataframe(df, use_container_width=True)

        # Download CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()
        st.download_button(
            "Download CSV",
            data=csv_str,
            file_name=f"survey_{uploaded_file.name.split('.')[0]}.csv",
            mime="text/csv"
        )

        # Download GeoJSON (if coords present)
        if 'easting' in df.columns and 'northing' in df.columns:
            import json
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [row.easting, row.northing]},
                        "properties": row.drop(['easting', 'northing']).to_dict()
                    }
                    for _, row in df.iterrows() if pd.notna(row.easting) and pd.notna(row.northing)
                ]
            }
            st.download_button(
                "Download GeoJSON",
                data=json.dumps(geojson, indent=2),
                file_name=f"survey_{uploaded_file.name.split('.')[0]}.geojson",
                mime="application/json"
            )

    except Exception as e:
        st.error(f"Processing failed: {e}")
        st.info("Try a simple GSI file for testing.")
