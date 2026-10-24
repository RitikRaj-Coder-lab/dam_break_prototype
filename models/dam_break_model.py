"""
Simplified Dam Break Inundation Model
=====================================
Uses analytical breach hydrograph (Ritter / broad-crested weir style)
+ kinematic wave / simplified 1D routing + DEM-based inundation extent.

Designed for rapid prototype demonstration on ordinary laptops.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Optional


@dataclass
class DamParams:
    height_m: float = 30.0          # Dam height above river bed
    crest_length_m: float = 100.0   # Crest length
    reservoir_volume_mcm: float = 50.0  # Million cubic metres
    breach_width_final_m: float = 40.0
    breach_formation_time_hr: float = 1.0
    initial_water_level_m: float = 28.0  # relative to bed


@dataclass
class RiverParams:
    slope: float = 0.001            # bed slope
    manning_n: float = 0.035
    channel_width_m: float = 80.0
    floodplain_width_m: float = 500.0
    reach_length_km: float = 20.0


def ritter_peak_discharge(height_m: float, width_m: float) -> float:
    """
    Ritter (1892) analytical solution for instantaneous dam break peak discharge
    Qp = (8/27) * b * sqrt(g) * H^{1.5}
    """
    g = 9.81
    return (8.0 / 27.0) * width_m * np.sqrt(g) * (height_m ** 1.5)


def broad_crested_weir_discharge(H: float, b: float, Cd: float = 1.7) -> float:
    """Simple broad-crested weir formula Q = Cd * b * H^{1.5}"""
    return Cd * b * (H ** 1.5)


def generate_breach_hydrograph(
    dam: DamParams,
    dt_min: float = 5.0,
    total_time_hr: float = 6.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a triangular / trapezoidal breach hydrograph.
    Peak based on Ritter formula, linear rise during formation time,
    then exponential decay based on remaining volume.
    """
    times = np.arange(0, total_time_hr * 60 + dt_min, dt_min)  # minutes
    Q = np.zeros_like(times, dtype=float)

    t_form = dam.breach_formation_time_hr * 60  # minutes
    Qp = ritter_peak_discharge(dam.initial_water_level_m, dam.breach_width_final_m)

    # Volume available (m3)
    V0 = dam.reservoir_volume_mcm * 1e6

    for i, t in enumerate(times):
        if t <= t_form:
            # Linear rise to peak
            Q[i] = Qp * (t / t_form)
        else:
            # Simple exponential decay after peak
            # Approximate remaining volume depletion
            tau = 90.0  # characteristic decay time (min) – tunable
            Q[i] = Qp * np.exp(-(t - t_form) / tau)

    # Scale so that total volume is roughly conserved (crude)
    vol_sim = np.trapezoid(Q, times) * 60  # m3
    if vol_sim > 0:
        scale = min(1.5, V0 / vol_sim)  # allow some overshoot
        Q *= scale

    return times, Q


def route_kinematic(
    times_min: np.ndarray,
    Q_upstream: np.ndarray,
    river: RiverParams,
    dx_km: float = 1.0
) -> Dict[str, np.ndarray]:
    """
    Very simplified kinematic wave routing along the reach.
    Returns discharge and approximate water depth at successive sections.
    """
    n_sections = int(river.reach_length_km / dx_km) + 1
    x = np.arange(0, n_sections) * dx_km  # km

    # Travel time approximation (Cunge-type / kinematic celerity)
    # c ≈ (5/3) * V for wide rectangular; use simple lag
    # Assume average velocity ~ 2-4 m/s for flood wave
    avg_vel_ms = 3.0
    lag_min_per_km = (1000.0 / avg_vel_ms) / 60.0  # minutes per km

    Q_sections = []
    depth_sections = []

    for i, xi in enumerate(x):
        lag = xi * lag_min_per_km
        # Shift hydrograph
        Q_shifted = np.interp(times_min - lag, times_min, Q_upstream, left=0, right=0)
        # Attenuation (simple exponential smoothing)
        atten = np.exp(-0.05 * xi)
        Q_i = Q_shifted * atten
        Q_sections.append(Q_i)

        # Approximate depth from Manning (wide rectangular)
        # Q = (1/n) * A * R^{2/3} * S^{1/2}
        # For wide channel R ≈ y, A = w * y
        w = river.channel_width_m + 0.3 * river.floodplain_width_m  # effective
        S = river.slope
        n = river.manning_n
        # Solve for y roughly: Q ≈ (1/n) * w * y^{5/3} * sqrt(S)
        # y ≈ [ Q * n / (w * sqrt(S)) ]^{0.6}
        with np.errstate(divide="ignore", invalid="ignore"):
            y = (Q_i * n / (w * np.sqrt(S) + 1e-9)) ** 0.6
            y = np.nan_to_num(y, nan=0.0)
        depth_sections.append(y)

    return {
        "x_km": x,
        "times_min": times_min,
        "Q": np.array(Q_sections),          # shape (n_sec, n_time)
        "depth_m": np.array(depth_sections)
    }


def estimate_inundation_extent(
    max_depth_m: np.ndarray,
    x_km: np.ndarray,
    river: RiverParams,
    dem_slope_side: float = 0.02
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crude inundation width from max depth assuming simple V-shaped / trapezoidal valley.
    Returns left and right inundation half-widths (m) along the reach.
    """
    # Effective top width ≈ channel + 2 * (depth / side_slope)
    half_width = river.channel_width_m / 2 + max_depth_m / (dem_slope_side + 1e-6)
    half_width = np.clip(half_width, river.channel_width_m / 2, river.floodplain_width_m)
    return half_width, half_width


def run_full_simulation(
    dam: Optional[DamParams] = None,
    river: Optional[RiverParams] = None,
    dt_min: float = 5.0
) -> Dict:
    """
    End-to-end simplified dam-break simulation.
    Returns hydrograph, routed results, max inundation summary.
    """
    dam = dam or DamParams()
    river = river or RiverParams()

    times, Q = generate_breach_hydrograph(dam, dt_min=dt_min)
    routed = route_kinematic(times, Q, river)

    max_Q = routed["Q"].max(axis=1)
    max_depth = routed["depth_m"].max(axis=1)
    left_w, right_w = estimate_inundation_extent(max_depth, routed["x_km"], river)

    peak_arrival = []
    for i in range(len(routed["x_km"])):
        idx = np.argmax(routed["Q"][i])
        peak_arrival.append(times[idx])

    summary = {
        "peak_discharge_m3s": float(Q.max()),
        "max_depth_along_reach_m": max_depth.tolist(),
        "inundation_half_width_m": left_w.tolist(),
        "peak_arrival_min": peak_arrival,
        "total_inundated_area_km2": float(
            np.trapezoid(left_w + right_w, routed["x_km"]) / 1000.0  # rough
        ),
    }

    return {
        "dam": dam,
        "river": river,
        "times_min": times,
        "Q_breach": Q,
        "routed": routed,
        "summary": summary,
    }


if __name__ == "__main__":
    # Quick test
    results = run_full_simulation()
    print("Peak discharge:", results["summary"]["peak_discharge_m3s"], "m³/s")
    print("Approx inundated area:", results["summary"]["total_inundated_area_km2"], "km²")
    print("Max depth at dam toe:", results["summary"]["max_depth_along_reach_m"][0], "m")
