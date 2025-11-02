# survey_parser.py - Core parsers with better error handling
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import re
import pandas as pd

# Namespaces for LandXML
NS = {
    'l': 'http://www.landxml.org/schema/LandXML-1.2',
    'h': 'http://xml.hexagon.com/schema/HeXML-1.9'
}

def parse_gsi_file(content: str) -> List[Dict]:
    """Parse GSI content to list of dicts."""
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    records = []
    current = {}
    for line in lines:
        words = line.split()
        for word in words:
            parsed = _parse_gsi_word(word)
            if parsed:
                field, val = parsed
                current[field] = val
        if current:  # End of record
            if 'instrument_height' in current:
                current['point_type'] = 'SP'
            elif 'hz_angle' in current:
                current['point_type'] = 'OBS'
            else:
                current['point_type'] = 'COORD'
            records.append(current)
            current = {}
    return records

def _parse_gsi_word(word: str) -> Optional[tuple]:
    if len(word) < 7:
        return None
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
    elif wi == '71':
        return 'code', val_str.strip('+')
    # Add more WI as needed (e.g., 58 for prism_const)
    return None

def parse_landxml_file(filepath: str) -> List[Dict]:
    """Parse LandXML to list of dicts."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        records = []

        # Global temp/pressure (fallback)
        instr_details = root.find('.//l:InstrumentDetails', NS)
        temp = float(instr_details.get('temperature', 15.0)) if instr_details is not None else 15.0
        press = float(instr_details.get('pressure', 1013.0)) if instr_details is not None else 1013.0

        # Setups and observations (simplified)
        for setup in root.findall('.//l:InstrumentSetup', NS):
            instr_pt_ref = setup.find('l:InstrumentPoint', NS).get('pntRef')
            ih = float(setup.get('instrumentHeight', 0))

            # Setup point
            sp = root.find(f".//h:Point[@uniqueID='{instr_pt_ref}']", NS)
            if sp is not None:
                grid = sp.find('.//h:Grid', NS)
                if grid is not None:
                    records.append({
                        'point_id': instr_pt_ref,
                        'point_type': 'SP',
                        'easting': float(grid.get('e', 0)),
                        'northing': float(grid.get('n', 0)),
                        'elevation': float(grid.get('hghthO', 0)),
                        'instrument_height': ih,
                        'temperature': temp,
                        'pressure': press,
                        'timestamp': setup.find('l:InstrumentPoint', NS).get('timeStamp', ''),
                    })

            # Observations (basic)
            for obs in root.findall(f".//l:RawObservation[l:TargetPoint/@pntRef]", NS):
                target_ref = obs.find('l:TargetPoint', NS).get('pntRef')
                target = root.find(f".//h:Point[@uniqueID='{target_ref}']", NS)
                if target is None:
                    continue
                grid = target.find('.//h:Grid', NS)
                if grid is None:
                    continue

                records.append({
                    'point_id': target_ref,
                    'point_type': 'OBS',
                    'easting': float(grid.get('e', 0)),
                    'northing': float(grid.get('n', 0)),
                    'elevation': float(grid.get('hghthO', 0)),
                    'hz_angle': obs.get('horizAngle'),
                    'v_angle': obs.get('zenithAngle'),
                    'slope_dist': float(obs.get('slopeDistance', 0)),
                    'target_height': float(obs.get('targetHeight', 0)),
                    'instrument_height': ih,
                    'prism_const': float(obs.get('reflectorConstant', 0)),
                    'ppm_atm': 12.5,  # Placeholder; calc from temp/press if needed
                    'temperature': temp,
                    'pressure': press,
                    'timestamp': obs.get('timeStamp', ''),
                })

        return records
    except ET.ParseError as e:
        st.error(f"XML parse error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []
