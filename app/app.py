"""
Dam Break Inundation Modelling Prototype
========================================
Easy-to-understand version + Bhakra-Nangal style coloured inundation map.
SIH Problem Statement 26161 | NTRO
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from models.dam_break_model import DamParams, RiverParams, run_full_simulation

st.set_page_config(
    page_title="Dam Break Flood Visualiser",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title { font-size: 2.1rem; font-weight: 700; color: #0d47a1; margin-bottom: 0.1rem; }
    .sub-title  { font-size: 1.05rem; color: #546e7a; margin-bottom: 1.2rem; }
    .explain-box {
        background: #e3f2fd; border-left: 5px solid #1565c0;
        padding: 0.9rem 1.1rem; border-radius: 0 8px 8px 0;
        margin: 0.8rem 0 1.2rem 0; font-size: 0.95rem;
    }
    .warning-box {
        background: #fff3e0; border-left: 5px solid #ef6c00;
        padding: 0.9rem 1.1rem; border-radius: 0 8px 8px 0; margin: 0.8rem 0;
    }
    .success-box {
        background: #e8f5e9; border-left: 5px solid #2e7d32;
        padding: 0.9rem 1.1rem; border-radius: 0 8px 8px 0; margin: 0.8rem 0;
    }
    .location-box {
        background: #f3e5f5; border-left: 5px solid #7b1fa2;
        padding: 0.8rem 1.1rem; border-radius: 0 8px 8px 0; margin: 0.6rem 0;
        font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Scenario definitions with real locations
# -------------------------------------------------
SCENARIO_LOCATIONS = {
    "Bhakra-Nangal (Sutlej) – Recommended": {
        "name": "Bhakra Dam → Sutlej River corridor (Himachal → Punjab)",
        "dam_lat": 31.4108, "dam_lon": 76.4333,
        "zoom": 9,
        "note": "Real Bhakra Dam location. Downstream corridor follows the Sutlej towards Nangal, Ropar, and further into Punjab plains. Style inspired by professional dam-break inundation maps.",
        "towns": [
            {"name": "Bhakra Dam", "lat": 31.4108, "lon": 76.4333, "arrival": "0 h"},
            {"name": "Nangal", "lat": 31.37, "lon": 76.38, "arrival": "0–0.5 h"},
            {"name": "Anandpur Sahib", "lat": 31.24, "lon": 76.50, "arrival": "0.5–1 h"},
            {"name": "Ropar (Rupnagar)", "lat": 30.97, "lon": 76.52, "arrival": "1–2 h"},
            {"name": "Morinda", "lat": 30.79, "lon": 76.50, "arrival": "2–3 h"},
            {"name": "Sirhind / Fatehgarh", "lat": 30.65, "lon": 76.40, "arrival": "3–5 h"},
            {"name": "Chandigarh area", "lat": 30.74, "lon": 76.78, "arrival": "—"},
            {"name": "Patiala direction", "lat": 30.34, "lon": 76.38, "arrival": "5–8 h"},
        ]
    },
    "Rishiganga / Chamoli-type (Himalaya)": {
        "name": "Rishiganga – Dhauliganga area (Chamoli, Uttarakhand)",
        "dam_lat": 30.48, "dam_lon": 79.62,
        "zoom": 11,
        "note": "Near the actual Rishiganga valley (2021 flood area). Steep Himalayan terrain.",
        "towns": []
    },
    "Kosi-type (Bihar plains)": {
        "name": "Kosi River region (near Birpur / Bhimnagar, Bihar-Nepal border)",
        "dam_lat": 26.52, "dam_lon": 86.93,
        "zoom": 10,
        "note": "Wide alluvial plain of the Kosi system.",
        "towns": []
    },
    "Generic Himalayan river": {
        "name": "Bhagirathi / Tehri region (Uttarakhand)",
        "dam_lat": 30.38, "dam_lon": 78.48,
        "zoom": 11,
        "note": "Near Tehri Dam area on the Bhagirathi river.",
        "towns": []
    },
    "Custom (adjust yourself)": {
        "name": "Generic Himalayan Valley (near Joshimath / Alaknanda)",
        "dam_lat": 30.55, "dam_lon": 79.55,
        "zoom": 11,
        "note": "Typical Himalayan river valley for custom testing.",
        "towns": []
    }
}


def depth_to_color(depth_m):
    """Return a colour similar to the reference Bhakra map (red = deep, blue = shallow)."""
    if depth_m > 12:
        return "#b71c1c"      # deep red
    elif depth_m > 8:
        return "#e65100"      # orange-red
    elif depth_m > 5:
        return "#ff8f00"      # orange
    elif depth_m > 3:
        return "#fbc02d"      # yellow
    elif depth_m > 1.5:
        return "#29b6f6"      # light blue
    elif depth_m > 0.5:
        return "#0288d1"      # medium blue
    else:
        return "#01579b"      # dark blue


def create_flood_map(reach_km, half_widths, max_depths, peak_arrivals, scenario_key):
    """
    Create a Folium map. For Bhakra-Nangal we draw a long coloured corridor
    that visually resembles professional dam-break inundation maps.
    """
    loc = SCENARIO_LOCATIONS.get(scenario_key, SCENARIO_LOCATIONS["Custom (adjust yourself)"])
    dam_lat = loc["dam_lat"]
    dam_lon = loc["dam_lon"]
    zoom = loc["zoom"]

    m = folium.Map(
        location=[dam_lat - 0.6, dam_lon + 0.15],  # slightly shifted to show corridor
        zoom_start=zoom,
        tiles=None,
        control_scale=True
    )

    # Satellite basemap
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite View",
        overlay=False,
        control=True,
        max_zoom=16
    ).add_to(m)

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street Map",
        overlay=False,
        control=True
    ).add_to(m)

    # Dam marker
    folium.Marker(
        location=[dam_lat, dam_lon],
        popup=f"<b>Dam / Breach Location</b><br>{loc['name']}",
        tooltip="Dam (Breach starts here)",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    n = len(reach_km)

    # Direction: for Bhakra we go roughly south-east along Sutlej
    if "Bhakra" in scenario_key:
        dlat = -0.011      # south
        dlon = 0.0065     # east
    else:
        dlat = -0.0085
        dlon = 0.004

    # Draw coloured segments (depth colour ramp)
    for i in range(n - 1):
        dist1 = reach_km[i]
        dist2 = reach_km[i + 1]
        lat1 = dam_lat + dist1 * dlat
        lon1 = dam_lon + dist1 * dlon
        lat2 = dam_lat + dist2 * dlat
        lon2 = dam_lon + dist2 * dlon

        # Average depth of the segment for colour
        depth = (max_depths[i] + max_depths[i + 1]) / 2.0
        color = depth_to_color(depth)

        # Width in degrees
        half1 = max(half_widths[i] / 111000.0, 0.0015)
        half2 = max(half_widths[i + 1] / 111000.0, 0.0015)

        # Quadrilateral for this segment
        poly = [
            (lat1, lon1 + half1),
            (lat2, lon2 + half2),
            (lat2, lon2 - half2),
            (lat1, lon1 - half1),
        ]
        folium.Polygon(
            locations=poly,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.55,
            popup=f"Depth ≈ {depth:.1f} m<br>Distance {dist1:.0f}–{dist2:.0f} km"
        ).add_to(m)

    # Check-point markers with depth & time
    for i in [0, n // 4, n // 2, 3 * n // 4, n - 1]:
        dist = reach_km[i]
        lat = dam_lat + dist * dlat
        lon = dam_lon + dist * dlon
        depth = max_depths[i]
        arrival = peak_arrivals[i]
        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="#212121",
            fill=True,
            fill_color="#ff6f00",
            fill_opacity=0.95,
            popup=(
                f"<b>Distance from dam:</b> {dist:.1f} km<br>"
                f"<b>Max water depth:</b> {depth:.1f} m<br>"
                f"<b>Peak arrives in:</b> {arrival:.0f} min"
            ),
            tooltip=f"{dist:.0f} km → {depth:.1f} m"
        ).add_to(m)

    # Town markers (especially useful for Bhakra)
    for t in loc.get("towns", []):
        folium.CircleMarker(
            location=[t["lat"], t["lon"]],
            radius=5,
            color="#ffffff",
            fill=True,
            fill_color="#fdd835",
            fill_opacity=0.95,
            popup=f"<b>{t['name']}</b><br>Approx. arrival: {t['arrival']}",
            tooltip=t["name"]
        ).add_to(m)
        folium.Marker(
            location=[t["lat"], t["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:11px;font-weight:600;color:#fff;text-shadow:1px 1px 2px #000;">{t["name"]}</div>'
            )
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed; bottom:25px; left:25px; z-index:9999;
                background:rgba(0,0,0,0.82); color:white; padding:12px 15px;
                border-radius:8px; font-size:12.5px; line-height:1.45;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.4); max-width:230px;">
        <b style="font-size:13px;">Inundation Depth (m)</b><br>
        <span style="color:#b71c1c;">■■</span> &gt; 12 m (very deep)<br>
        <span style="color:#e65100;">■■</span> 8 – 12 m<br>
        <span style="color:#ff8f00;">■■</span> 5 – 8 m<br>
        <span style="color:#fbc02d;">■■</span> 3 – 5 m<br>
        <span style="color:#29b6f6;">■■</span> 1.5 – 3 m<br>
        <span style="color:#0288d1;">■■</span> 0.5 – 1.5 m<br>
        <span style="color:#01579b;">■■</span> &lt; 0.5 m<br>
        <hr style="margin:6px 0;border-color:#555;">
        🔴 Red pin = Dam<br>
        🟠 Orange dots = Depth check points<br>
        🟡 Yellow dots = Towns
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(position="topright").add_to(m)
    return m, loc


def main():
    st.markdown('<p class="main-title">🌊 Dam Break Flood Visualiser</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">Professional-looking inundation map on real satellite imagery • Runs on any laptop • SIH 26161 | NTRO</p>',
        unsafe_allow_html=True
    )

    # ---------- Sidebar ----------
    st.sidebar.header("1️⃣ Choose Scenario")
    sample = st.sidebar.selectbox(
        "Pick a sample situation",
        list(SCENARIO_LOCATIONS.keys()),
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.header("2️⃣ Dam & River Settings")
    st.sidebar.caption("Move the sliders to change the situation")

    if "Bhakra" in sample:
        d_h, d_w, d_vol, d_bw, d_ft = 120.0, 100.0, 400.0, 80.0, 1.5
        r_s, r_n, r_cw, r_fp, r_len = 0.0006, 0.030, 150.0, 1200.0, 80.0
    elif sample == "Kosi-type (Bihar plains)":
        d_h, d_w, d_vol, d_bw, d_ft = 25.0, 22.0, 120.0, 60.0, 1.5
        r_s, r_n, r_cw, r_fp, r_len = 0.0008, 0.035, 120.0, 800.0, 30.0
    elif sample == "Rishiganga / Chamoli-type (Himalaya)":
        d_h, d_w, d_vol, d_bw, d_ft = 40.0, 35.0, 40.0, 45.0, 0.8
        r_s, r_n, r_cw, r_fp, r_len = 0.004, 0.04, 60.0, 300.0, 15.0
    elif sample == "Generic Himalayan river":
        d_h, d_w, d_vol, d_bw, d_ft = 50.0, 45.0, 60.0, 55.0, 1.0
        r_s, r_n, r_cw, r_fp, r_len = 0.003, 0.038, 80.0, 450.0, 20.0
    else:
        d_h, d_w, d_vol, d_bw, d_ft = 35.0, 32.0, 80.0, 50.0, 1.0
        r_s, r_n, r_cw, r_fp, r_len = 0.0015, 0.035, 90.0, 600.0, 25.0

    dam_height = st.sidebar.slider("Dam Height (metres)", 10.0, 250.0, float(d_h), 1.0)
    water_level = st.sidebar.slider("Water Level in Reservoir (m)", 5.0, dam_height, float(d_w), 0.5)
    volume_mcm = st.sidebar.slider("Reservoir Volume (Million m³)", 5.0, 1000.0, float(d_vol), 5.0)
    breach_width = st.sidebar.slider("How wide does the breach become? (m)", 10.0, 200.0, float(d_bw), 5.0)
    form_time = st.sidebar.slider("Time for breach to fully open (hours)", 0.25, 5.0, float(d_ft), 0.25)

    st.sidebar.markdown("**River settings**")
    slope = st.sidebar.slider("River bed slope (steepness)", 0.0002, 0.01, float(r_s), 0.0001, format="%.4f")
    manning = st.sidebar.slider("River roughness (Manning n)", 0.02, 0.08, float(r_n), 0.005)
    channel_w = st.sidebar.slider("Normal river width (m)", 20.0, 300.0, float(r_cw), 5.0)
    fp_w = st.sidebar.slider("Floodplain width (m)", 100.0, 3000.0, float(r_fp), 50.0)
    reach_km = st.sidebar.slider("How far downstream to study (km)", 5.0, 120.0, float(r_len), 1.0)

    run_btn = st.sidebar.button("▶️ Run Simulation", use_container_width=True, type="primary")

    # ---------- Run model ----------
    if "results" not in st.session_state or run_btn:
        with st.spinner("Calculating flood wave... please wait a few seconds"):
            dam = DamParams(
                height_m=dam_height,
                crest_length_m=200.0,
                reservoir_volume_mcm=volume_mcm,
                breach_width_final_m=breach_width,
                breach_formation_time_hr=form_time,
                initial_water_level_m=water_level
            )
            river = RiverParams(
                slope=slope,
                manning_n=manning,
                channel_width_m=channel_w,
                floodplain_width_m=fp_w,
                reach_length_km=reach_km
            )
            st.session_state.results = run_full_simulation(dam, river)
            st.session_state.scenario = sample

    results = st.session_state.results
    scenario = st.session_state.get("scenario", sample)
    summary = results["summary"]
    times = results["times_min"]
    Qb = results["Q_breach"]
    routed = results["routed"]
    max_depths = summary["max_depth_along_reach_m"]
    half_widths = summary["inundation_half_width_m"]
    peak_arrivals = summary["peak_arrival_min"]

    # ---------- Tabs ----------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Satellite Map & Flood Zone",
        "📊 What Happens (Simple Numbers)",
        "📈 Graphs Explained",
        "📁 Download Results",
        "❓ How to Use This App"
    ])

    # ==================== TAB 1: MAP ====================
    with tab1:
        st.subheader("Satellite View – Coloured Inundation Map")

        flood_map, loc_info = create_flood_map(
            routed["x_km"], half_widths, max_depths, peak_arrivals, scenario
        )

        st.markdown(f"""
        <div class="location-box">
        <b>📍 Current map location:</b> {loc_info['name']}<br>
        {loc_info['note']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="explain-box">
        <b>How to read the map (same style as professional dam-break maps):</b><br>
        • <b>Colour</b> = water depth (red/orange = very deep near the dam, yellow = medium, blue = shallower farther away)<br>
        • <b>Red pin</b> = Dam / breach location<br>
        • <b>Orange dots</b> = Click for exact depth and arrival time at that point<br>
        • <b>Yellow labels</b> = Towns / important places (shown for Bhakra-Nangal scenario)<br>
        • Switch between Satellite and Street Map with the control on the top-right
        </div>
        """, unsafe_allow_html=True)

        st_folium(flood_map, width=None, height=560, returned_objects=[])

        st.markdown("""
        <div class="warning-box">
        <b>Important note about accuracy:</b><br>
        This map uses a <b>simplified hydrodynamic model</b> so it runs instantly on any laptop.  
        The colour corridor follows the general direction of the river and uses calculated depths.  
        A fully accurate map like the official Bhakra-Nangal example requires a real high-resolution DEM 
        + 2D model (HEC-RAS / Delft3D). That can be added later as the high-fidelity engine; 
        the current version is perfect for demonstration, teaching and quick scenario testing.
        </div>
        """, unsafe_allow_html=True)

    # ==================== TAB 2: SIMPLE NUMBERS ====================
    with tab2:
        st.subheader("Key Results – Easy to understand")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Peak Water Flow", f"{summary['peak_discharge_m3s']:,.0f} m³/s")
        with c2:
            st.metric("Deepest Water (near dam)", f"{max_depths[0]:.1f} metres")
        with c3:
            st.metric("Approx. Flooded Area", f"{summary['total_inundated_area_km2']:.1f} km²")
        with c4:
            st.metric("Time to Peak Flow", f"{times[np.argmax(Qb)]:.0f} minutes")

        st.markdown("---")
        st.subheader("What do these numbers mean for people?")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            <div class="explain-box">
            <b>Peak Discharge (m³/s)</b><br>
            Think of it as “how many Olympic swimming pools of water are released every second at the worst moment”.  
            Higher number = more dangerous and faster flood wave.
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            st.markdown("""
            <div class="explain-box">
            <b>Max Depth</b><br>
            Water depth of 1–2 m can already sweep cars and people.  
            Depth above 3–4 m is extremely dangerous for buildings and life.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="success-box">
        <b>Arrival Time</b> (shown on the map when you click orange dots)<br>
        This is the most important number for evacuation.  
        If the peak arrives in 30–40 minutes at a village 10 km away, people need to move to higher ground very quickly.
        </div>
        """, unsafe_allow_html=True)

        st.subheader("Flood strength at different distances")
        df = pd.DataFrame({
            "Distance from Dam (km)": [f"{x:.1f}" for x in routed["x_km"]],
            "Max Water Depth (m)": [f"{d:.1f}" for d in max_depths],
            "Approx. Flood Width each side (m)": [f"{w:.0f}" for w in half_widths],
            "Peak arrives after (minutes)": [f"{t:.0f}" for t in peak_arrivals]
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ==================== TAB 3: GRAPHS EXPLAINED ====================
    with tab3:
        st.subheader("Graphs – What they tell us")

        st.markdown("#### Graph 1: Water coming out of the dam (Breach Hydrograph)")
        st.markdown("""
        <div class="explain-box">
        <b>How to read this graph:</b><br>
        • Horizontal axis = Time after the dam starts breaking (in hours)<br>
        • Vertical axis = How much water is flowing out (m³ per second)<br>
        • The curve starts low → rises to a high peak → then falls down<br>
        • The highest point is the most dangerous moment of the flood
        </div>
        """, unsafe_allow_html=True)

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=times/60, y=Qb, fill="tozeroy",
            name="Water flowing out",
            line=dict(color="#c62828", width=3)
        ))
        fig1.update_layout(
            xaxis_title="Time after breach starts (hours)",
            yaxis_title="Water flow (m³/s)",
            height=380, template="plotly_white",
            title="Breach Outflow Hydrograph"
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown("#### Graph 2: Flood wave travelling downstream")
        st.markdown("""
        <div class="explain-box">
        <b>How to read this graph:</b><br>
        • Different coloured lines = different places along the river<br>
        • You can see the flood peak becomes smaller and arrives later as we go farther from the dam<br>
        • This is called “attenuation” – nature reduces the force of the flood wave with distance
        </div>
        """, unsafe_allow_html=True)

        fig2 = go.Figure()
        colors = ["#b71c1c", "#e65100", "#1565c0", "#2e7d32"]
        labels = ["Near Dam", "1/3 of the way", "2/3 of the way", "End of study reach"]
        sections = [0, len(routed["x_km"])//3, 2*len(routed["x_km"])//3, -1]
        for idx, s in enumerate(sections):
            fig2.add_trace(go.Scatter(
                x=times/60, y=routed["Q"][s],
                name=f"{labels[idx]} ({routed['x_km'][s]:.1f} km)",
                line=dict(color=colors[idx], width=2.5)
            ))
        fig2.update_layout(
            xaxis_title="Time after breach starts (hours)",
            yaxis_title="Water flow (m³/s)",
            height=400, template="plotly_white",
            legend=dict(orientation="h", y=1.12),
            title="How the flood wave changes as it travels"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Graph 3: How deep and how wide the flood becomes")
        st.markdown("""
        <div class="explain-box">
        <b>How to read this graph:</b><br>
        • Blue line = Maximum water depth at each distance from the dam<br>
        • Orange dashed line = How wide the flood spreads on each side of the river (scaled for display)<br>
        • Both depth and width are highest near the dam and reduce downstream
        </div>
        """, unsafe_allow_html=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=routed["x_km"], y=max_depths,
            mode="lines+markers", name="Max Depth (m)",
            line=dict(color="#1565c0", width=3)
        ))
        fig3.add_trace(go.Scatter(
            x=routed["x_km"], y=np.array(half_widths)/40,
            mode="lines", name="Flood width each side (scaled)",
            line=dict(color="#ef6c00", width=2, dash="dash"),
            yaxis="y2"
        ))
        fig3.update_layout(
            xaxis_title="Distance downstream from dam (km)",
            yaxis_title="Maximum Water Depth (metres)",
            yaxis2=dict(title="Half-width (m / 40)", overlaying="y", side="right"),
            height=400, template="plotly_white",
            legend=dict(orientation="h", y=1.12),
            title="Depth and width of flooding along the river"
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ==================== TAB 4: DOWNLOAD ====================
    with tab4:
        st.subheader("Download the results")
        st.write("You can save the numbers and use them in reports or GIS software.")

        df_export = pd.DataFrame({
            "Distance_km": routed["x_km"],
            "Max_Depth_m": max_depths,
            "Inundation_HalfWidth_m": half_widths,
            "Peak_Arrival_min": peak_arrivals
        })
        csv1 = df_export.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Flood Profile (CSV)", csv1, "flood_profile.csv", "text/csv")

        df_hydro = pd.DataFrame({"Time_minutes": times, "Discharge_m3s": Qb})
        csv2 = df_hydro.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Breach Hydrograph (CSV)", csv2, "breach_hydrograph.csv", "text/csv")

        st.markdown("""
        <div class="success-box">
        In the full professional version we will also give you:<br>
        • Shapefile (.shp) and KML (.kml) of the exact flooded polygon<br>
        • Depth grid that can be opened in QGIS / ArcGIS<br>
        • Google Earth ready files
        </div>
        """, unsafe_allow_html=True)

    # ==================== TAB 5: HOW TO USE ====================
    with tab5:
        st.subheader("How to use this web app (step by step)")
        st.markdown("""
        ### Recommended first try

        1. In the sidebar choose **“Bhakra-Nangal (Sutlej) – Recommended”**
        2. Click **Run Simulation**
        3. Open the first tab **“Satellite Map & Flood Zone”**
        4. You will see a coloured flood corridor starting from the real Bhakra Dam location, 
           similar in style to professional dam-break maps (deep colours near the dam, lighter farther away).
        5. Click the orange dots and yellow town labels for details.

        ### Other scenarios
        - Rishiganga / Chamoli-type → steep Himalayan valley
        - Kosi-type → wide Bihar plains
        - Custom → adjust all parameters yourself

        ---
        ### About real DEM vs this prototype
        The colourful map you saw in the reference image was produced with a full 2D hydrodynamic model 
        (usually HEC-RAS) on a real DEM. That process is accurate but needs more computing power and time.

        This prototype uses a fast simplified model so that:
        - It runs on any normal laptop in a few seconds
        - Students and judges can change parameters and instantly see the effect
        - The visual style (colour by depth, towns, arrival times) is already close to professional maps

        Later the same dashboard can be connected to a real DEM + 2D engine for the final high-fidelity results.
        """)

        st.markdown("---")
        st.caption("Prototype for Smart India Hackathon 2026 • Problem Statement 26161 • National Technical Research Organisation (NTRO)")


if __name__ == "__main__":
    main()
