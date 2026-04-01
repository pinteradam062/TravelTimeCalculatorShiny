import math
import pandas as pd

MPH_TO_MPS = 0.44704
MILE_TO_METER = 1609.344


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


def solve_v_peak(vmax, distance_m, mass, force, power, b,
                 max_iter=200, tol=1e-3, relax=0.2, scale=200.0):
    # initial guess from constant-acceleration approximation
    a0 = force / mass
    v_guess = math.sqrt(max(0.0, 2 * distance_m / ((1 / a0) + (1 / b))))
    v_guess = max(0.0, min(v_guess, vmax))

    for _ in range(max_iter):
        needed = distance_needed_for_peak(v_guess, mass, force, power, b)
        error = distance_m - needed

        if abs(error) < tol:
            return v_guess

        v_guess = v_guess + relax * (error / scale)
        v_guess = max(0.0, min(v_guess, vmax))

    # fallback: bisection
    v_low = 0.0
    v_high = vmax

    for _ in range(max_iter):
        v_mid = 0.5 * (v_low + v_high)
        needed = distance_needed_for_peak(v_mid, mass, force, power, b)

        if abs(distance_m - needed) < tol:
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


def run_route_model(df, diesel_params, emu_params, include_dwell=True):
    cumulative_distance_m = 0.0
    cumulative_time_diesel = 0.0
    cumulative_time_emu = 0.0

    results = []

    for _, section in df.iterrows():
        adj_distance_m = float(section["distance_mi"]) * MILE_TO_METER
        cumulative_distance_m += adj_distance_m

        vmax = float(section["speed_mph"]) * MPH_TO_MPS
        dwell = float(section["dwell"]) if include_dwell else 0.0

        run_time_diesel = travel_time(
            vmax,
            adj_distance_m,
            diesel_params["mass"],
            diesel_params["a0"],
            diesel_params["b"],
            diesel_params["power"],
        )

        run_time_emu = travel_time(
            vmax,
            adj_distance_m,
            emu_params["mass"],
            emu_params["a0"],
            emu_params["b"],
            emu_params["power"],
        )

        cumulative_time_diesel += run_time_diesel + dwell
        cumulative_time_emu += run_time_emu + dwell

        results.append({
            "Stop": section["stop"],
            "Total distance [mi]": cumulative_distance_m / MILE_TO_METER,
            "Adjacent distance [mi]": float(section["distance_mi"]),
            "Top speed [mph]": float(section["speed_mph"]),
            "Travel time Diesel [s]": run_time_diesel,
            "Travel time EMU [s]": run_time_emu,
            "Dwell [s]": dwell,
            "Cumulative Diesel [s]": cumulative_time_diesel,
            "Cumulative EMU [s]": cumulative_time_emu
        })

    return pd.DataFrame(results)