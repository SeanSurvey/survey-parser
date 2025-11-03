import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional

NS = {
    'l': 'http://www.landxml.org/schema/LandXML-1.2',
    'h': 'http://xml.hexagon.com/schema/HeXML-1.9'
}

WI_MAP = {
    '11': ('point_id', str),
    '19': ('timestamp', str),  # Parsed to datetime
    '21': ('hz_angle', lambda v: float(v) / 100000),
    '22': ('v_angle', lambda v: float(v) / 100000),
    '31': ('slope_dist', lambda v: float(v) / 1000),
    '58': ('prism_const', lambda v: float(v) / 10000),
    '71': ('code', str),
    '81': ('easting', lambda v: float(v) / 1000),
    '82': ('northing', lambda v: float(v) / 1000),
    '83': ('elevation', lambda v: float(v) / 1000),
    '87': ('target_height', lambda v: float(v) / 1000),
    '88': ('instrument_height', lambda v: float(v) / 1000),
}

def parse_gsi_file(content: str) -> List[Dict]:
    lines = content.splitlines()
    points = []
    current_point = {}

    for line in lines:
        if not line.strip(): continue
        words = line.split()
        for word in words:
            field, val = _parse_gsi_word(word)
            if field:
                current_point[field] = val
        if current_point:
            # Infer point_type
            current_point['point_type'] = 'SP' if 'instrument_height' in current_point else 'OBS' if 'hz_angle' in current_point else 'COORD'
            points.append(current_point)
            current_point = {}

    return points

def _parse_gsi_word(word: str) -> Optional[tuple]:
    if len(word) < 7: return None
    wi = word[0:2].lstrip('*')
    if wi not in WI_MAP: return None
    sign = word[6]
    val_str = (sign + word[7:]).strip()
    field, converter = WI_MAP[wi]

    try:
        if wi == '11':
            val = val_str.lstrip('+0')
        elif wi == '71':
            val = val_str.lstrip('+').lstrip('0') or '0'
        elif wi == '19':
            val = val_str.lstrip('+')
            if len(val) >= 8:
                month, day, hour, minute = int(val[0:2]), int(val[2:4]), int(val[4:6]), int(val[6:8])
                dt = datetime(2025, month, day, hour, minute)
                val = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            val = converter(val_str)
        return field, val
    except ValueError:
        return None  # Skip invalid numeric conversions

def parse_landxml_file(filepath: str) -> List[Dict]:
    tree = ET.parse(filepath)
    root = tree.getroot()
    records = []
    # Instrument details for temp/pressure
    instr = root.find('.//l:InstrumentDetails', NS)
    temp = float(instr.get('temperature', 0))
