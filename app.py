# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import networkx as nx
import re

st.set_page_config(page_title="Surveyor Pro", layout="wide")
st.title("Surveyor Pro - GSI to Network")

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload GSI or CSV", type=["gsi", "csv"])
if uploaded_file:
    if uploaded_file.name.endswith('.gsi'):
        content = uploaded_file.read().decode('utf-8', errors='ignore')
        lines = [l for l in content.splitlines() if l.startswith('*')]
        data = []
        current_from = "A"
        for line in lines:
            words = line.split()
            row = {'From': current_from, 'To': None, 'Slope_Dist_m': None, 'Measured_Hz_Angle_deg': None}
            for w in words:
                m = re.search(r'(\d{2})\.\.(\d{2})([+-]\d+)', w)
                if m:
                    wi, _, val = m.groups()
                    val = int(val) / 1e5 if wi in ['21','22'] else int(val) / 1e4
                    if wi == '11': 
                        row['To'] = str(abs(int(val)))
                        if 'DR' in line: current_from = row['To']
                    elif wi == '21': row['Measured_Hz_Angle_deg'] = val
                    elif wi == '31': row['Slope_Dist_m'] = val
            if row['To']: data.append(row)
        df = pd.DataFrame(data).dropna()
        st.success(f"Parsed {len(df)} observations")
    else:
        df = pd.read_csv(uploaded_file)
else:
    st.info("Upload your GSI file")
    df = pd.DataFrame([{'From': 'A', 'To': 'B', 'Slope_Dist_m': 100.0, 'Measured_Hz_Angle_deg': 45.0}])

# --- COMPUTED AZIMUTH ---
bs_az = st.number_input("Backsight Azimuth (°)", value=0.0)
df['Computed_Azimuth_deg'] = (df['Measured_Hz_Angle_deg'] + bs_az) % 360

# --- PLOT ---
G = nx.DiGraph()
for _, r in df.iterrows():
    if pd.notna(r['Computed_Azimuth_deg']) and pd.notna(r['Slope_Dist_m']):
        G.add_edge(r['From'], r['To'], dist=r['Slope_Dist_m'])
pos = nx.spring_layout(G, seed=42)
edge_traces = [go.Scatter(x=[pos[u][0], pos[v][0], None], y=[pos[u][1], pos[v][1], None], mode='lines') 
               for u, v in G.edges()]
node_trace = go.Scatter(x=[pos[n][0] for n in G.nodes], y=[pos[n][1] for n in G.nodes],
                        mode='markers+text', text=list(G.nodes), marker=dict(size=20))
fig = go.Figure(data=edge_traces + [node_trace], layout=go.Layout(height=600))
st.plotly_chart(fig, use_container_width=True)

# --- TABLE ---
st.data_editor(df[['From','To','Slope_Dist_m','Measured_Hz_Angle_deg','Computed_Azimuth_deg']])