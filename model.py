import math
import pandas as pd

MPH_TO_MPS = 0.44704
MILE_TO_METER = 1609.344

# =========================
# Train database
# =========================
TRAIN_TYPES = {
    "Diesel MBTA": {
        "mass": 467000,
        "a0": 0.51,
        "b": 0.30,
        "power": 2300000,
        "vmax": 127.138,
    },
    "EMU Stadler KISS": {
        "mass": 566400,
        "a0": 0.94,
        "b": 0.80,
        "power": 6000000,
        "vmax": 127.138,
    },
    "Siemens Charger B+AC [Battery Mode]": {
        "mass": 495700,
        "a0": 0.63,
        "b": 0.6,
        "power": 3300000,
        "vmax": 127.138,
    },
}

# =========================
# Physics
# =========================
def accel_distance_time(v_target, mass, force, power):
    if v_target <= 0:
        return 0.0, 0.0

    a0 = force / mass
    v_transition = power / force

    if v_target <= v_transition:
        d_acc = v_target**2 / (2 * a0)
        t_acc = v_target / a0
        return d_acc, t_acc

    d1 = v_transition**2 / (2 * a0)
    t1 = v_transition / a0

    t2 = (mass / (2 * power)) * (v_target**2 - v_transition**2)
    d2 = (mass / (3 * power)) * (v_target**3 - v_transition**3)

    return d1 + d2, t1 + t2


def brake_distance_time(v_target, b):
    if v_target <= 0:
        return 0.0, 0.0

    d_brk = v_target**2 / (2 * b)
    t_brk = v_target / b
    return d_brk, t_brk


def distance_needed_for_peak(v_peak, mass, force, power, b):
    d_acc, _ = accel_distance_time(v_peak, mass, force, power)
    d_brk, _ = brake_distance_time(v_peak, b)
    return d_acc + d_brk


def solve_v_peak(vmax, distance_m, mass, force, power, b):
    v_low = 0.0
    v_high = vmax

    for _ in range(100):
        v_mid = 0.5 * (v_low + v_high)
        needed = distance_needed_for_peak(v_mid, mass, force, power, b)

        if abs(distance_m - needed) < 1e-3:
            return v_mid

        if needed > distance_m:
            v_high = v_mid
        else:
            v_low = v_mid

    return 0.5 * (v_low + v_high)


def travel_time(vmax, distance_m, mass, a0, b, power):
    force = mass * a0

    d_acc_vmax, t_acc_vmax = accel_distance_time(vmax, mass, force, power)
    d_brk_vmax, t_brk_vmax = brake_distance_time(vmax, b)

    if d_acc_vmax + d_brk_vmax <= distance_m:
        d_cruise = distance_m - d_acc_vmax - d_brk_vmax
        t_cruise = d_cruise / vmax if vmax > 0 else 0.0
        return t_acc_vmax + t_cruise + t_brk_vmax

    v_peak = solve_v_peak(vmax, distance_m, mass, force, power, b)
    _, t_acc_peak = accel_distance_time(v_peak, mass, force, power)
    _, t_brk_peak = brake_distance_time(v_peak, b)
    return t_acc_peak + t_brk_peak


# =========================
# Main
# =========================
def run_route_model(df, selected_trains, include_dwell=True):
    results = []

    cumulative_distance_m = 0.0
    cumulative_times = {train: 0.0 for train in selected_trains}

    for i, section in df.iterrows():
        adj_distance_m = float(section["distance_mi"]) * MILE_TO_METER
        cumulative_distance_m += adj_distance_m

        vmax_track = float(section["speed_mph"]) * MPH_TO_MPS
        dwell = float(section["dwell"]) if include_dwell else 0.0

        row = {
            "Stop": section["stop"],
            "Total distance [mi]": cumulative_distance_m / MILE_TO_METER,
        }

        for train in selected_trains:
            params = TRAIN_TYPES[train]

            train_vmax = params["vmax"] * MPH_TO_MPS
            vmax = min(train_vmax, vmax_track)

            run_time = travel_time(
                vmax,
                adj_distance_m,
                params["mass"],
                params["a0"],
                params["b"],
                params["power"],
            )

            dwell_effective = 0.0 if i == 0 else dwell
            cumulative_times[train] += run_time + dwell_effective

            row[f"Travel time {train} [s]"] = run_time
            row[f"Cumulative {train} [s]"] = cumulative_times[train]

        results.append(row)

    return pd.DataFrame(results)