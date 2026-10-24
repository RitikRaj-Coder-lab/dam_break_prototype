# Dam Break Inundation Modelling Prototype

**Title:** Dam Break Inundation Modelling Using Hydrodynamic Modelling of any River 

## Overview
This is a **lightweight, fully working prototype** of a dam-break inundation modelling framework.  
It demonstrates the complete pipeline required by the problem statement on ordinary laptops (no HPC / GPU required).

### Features
- Interactive Streamlit dashboard
- Adjustable dam, breach and river parameters
- Pre-set Indian sample scenarios (Kosi-type, Rishiganga/Chamoli-type, Himalayan)
- Breach outflow hydrograph (Ritter-based)
- Simplified kinematic routing + inundation extent
- Longitudinal profiles, plan-view schematic
- Export: CSV hydrographs/profiles + GeoJSON (shp/kml ready structure)
- Clear upgrade path to full SPH / Delft3D / HEC-RAS + real DEM + Google Earth Engine

## Quick Start

```bash
# From the project root
cd dam_break_prototype

# Install dependencies (if not already present)
pip install streamlit plotly pandas numpy scipy folium streamlit-folium geopandas

# Run the app
streamlit run app/app.py
```

The browser will open automatically at `http://localhost:8501`.

## Project Structure
```
dam_break_prototype/
├── app/
│   └── app.py              # Streamlit dashboard
├── models/
│   └── dam_break_model.py  # Core simplified hydrodynamic engine
├── data/                   # Place real DEMs / sample data here
├── outputs/                # Simulation exports
└── README.md
```

## How the Model Works (Simplified Physics)
1. **Breach hydrograph** – Ritter (1892) analytical peak discharge + linear formation time + exponential volume decay.
2. **Downstream routing** – Kinematic-wave style time lag + attenuation.
3. **Water depth** – Inverted Manning equation for wide channel.
4. **Inundation width** – Simple valley geometry (side slope assumption).

This is intentionally fast and transparent so the team can demonstrate the full workflow live.  
For the final version the core can be swapped for:
- Delft3D-FLOW
- DualSPHysics / SWE-SPHysics
- HEC-RAS 2D
- HiPIMS / other GPU shallow-water solvers

while keeping the same GUI and export layer.

## Team Division Suggestion (6 members)
| # | Role |
|---|------|
| 1 | Data acquisition (DEM, satellite, dam inventory) + GEE module |
| 2 | Core hydrodynamic model improvements / validation |
| 3 | GIS export (.shp / .kml) + real DEM inundation mapping |
| 4 | Streamlit / dashboard UI & UX |
| 5 | Documentation, presentation, video demo |
| 6 | Integration, testing, sample Indian case studies |

## Next Steps for Full Solution
1. Replace simplified routing with 1D/2D HEC-RAS or open-source SWE solver on real DEM.
2. Add Google Earth Engine near-real-time flood detection script.
3. Generate proper polygonal inundation from DEM + depth grid → write .shp/.kml.
4. Add comparison of “SPH-style” vs “grid-based” scenarios (pre-computed high-fidelity runs + live surrogate).
5. Package as a desktop or web tool with authentication / scenario library.

## Disclaimer
This prototype is for **demonstration and educational purposes** only.  
It is **not validated for operational emergency decision-making**.  
Always use peer-reviewed, calibrated models and official agencies for real dam-break assessments.

---
*Built for Smart India Hackathon 2026*
