import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import re
import pandas as pd

# Namespaces
NS = {
    'l': 'http://www.landxml.org/schema/LandXML-1.2',
    'h': 'http://xml.hexagon.com/schema/HeXML-1.9'
}

def parse_gsi_file(content: str) -> List[Dict]:
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    points = []
    current_point = {}

    for line in lines:
        words = line.split()
        for word in words:
            field, val = _parse_gsi_word(word)
            if field and val is not None:
                current_point[field] = val
        if current_point:  # Append if we have data
            points.append(current_point)
            current_point = {}

    return points

def _parse_gsi_word(word: str) -> Optional[tuple]:
    if len(word) < 7: return None
    wi = word[0:2].lstrip('*')
    sign = word[6]
    val_str = sign + word[7:].strip()

    if wi == '11':
        return 'point_id', val_str.lstrip('+0')
    elif wi == '81':
        return 'easting', float(val_str) / 1000
    elif wi == '82':
        return 'northing', float(val_str) / 1000
    elif wi == '83':
        return 'elevation', float(val_str) / 1000
    elif wi == '87':
        return 'target_height', float(val_str) / 1000
    elif wi == '88':
        return 'instrument_height', float(val_str) / 1000
    elif wi == '21':
        return 'hz_angle', float(val_str) / 100000
    elif wi == '22':
        return 'v_angle', float(val_str) / 100000
    elif wi == '31':
        return 'slope_dist', float(val_str) / 1000
    elif wi == '58':
        return 'prism_const', float(val_str) / 10000  # mm
    elif wi == '71':
        return 'code', val_str.lstrip('+').lstrip('0') or '0'  # Point code, default to '0' if empty
    elif wi == '19':
        val = val_str.lstrip('+')
        if len(val) >= 8:  # MMDDHHMM format
            month = val[0:2]
            day = val[2:4]
            hour = val[4:6]
            minute = val[6:8]
            try:
                dt = datetime(2025, int(month), int(day), int(hour), int(minute))  # Use current year
                val = dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                val = val  # Fallback to raw if invalid
        return 'timestamp', val
    return None

def parse_landxml_file(filepath: str) -> List[Dict]:
    # (Unchanged from previous version for now, as focus is on GSI; add similar timestamp parsing if needed for XML)
    with open(filepath, 'r') as f:
        content = f.read()
    # ... (rest of the XML parser code as before)
    return records  # Assuming your original has this

# (Rest of file unchanged if you have more)
