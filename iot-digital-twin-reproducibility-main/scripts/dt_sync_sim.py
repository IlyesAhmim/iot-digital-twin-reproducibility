#!/usr/bin/env python3
"""Discrete-event simulation of the manufacturing-cell attack path (Section 8).

The simulation reproduces the illustrative scenario of the manuscript: a
vibration sensor reports through a gateway and a broker to an edge twin that
decides on a protective stop. The gateway is compromised (assumption A5) and
mounts a replay or a delay attack; a third attack spoofs the sensor itself
(physical layer, threat T1). Four twin-side configurations are compared:

  C0  TLS only: timestamps and sequence numbers added by the gateway (A2).
  C1  C0 + source-side signatures over (sequence number, timestamp, value),
      verified at the twin with a monotone sequence check; failures raise an alert.
  C2  C1 + staleness-aware ingestion: updates older than D are rejected and an
      alert (with a fail-safe hold) is raised when the state age exceeds D.
  C3  C2 + a physical-consistency check between vibration and spindle current
      read over an independent path; a residual alarm triggers the hold.

The model is deliberately simple and every parameter is defined in the Params
dataclass. The outputs are indicator values (Table 12 of the manuscript) computed from the
simulated traces, with the ground truth that only a simulation provides.

Run:  python3 dt_sync_sim.py [outdir]     (about one minute on a laptop)
Outputs: sim_results.csv, sim_summary.json, sim_table.tex,
         figures/Figure_sim_traces.pdf, false-alarm check on stdout.
"""
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, asdict

import numpy as np


@dataclass
class Params:
    T_END: float = 600.0          # s, run length
    P: float = 0.5                # s, sensor (and current) reporting period
    D: float = 2.0                # s, freshness bound of the protective decision
    T_COMPROMISE: float = 100.0   # s, gateway compromised, starts recording (S1)
    T_ATTACK: float = 200.0       # s, attack start
    T_ATTACK_END: float = 450.0   # s, attack end
    T_DEG: float = 300.0          # s, bearing degradation starts
    V0: float = 2.0               # mm/s, normal vibration velocity (RMS)
    DEG_RATE: float = 0.1         # mm/s per s after T_DEG
    V_TH: float = 4.5             # mm/s, protective-stop threshold
    SIGMA_V: float = 0.10         # mm/s, vibration measurement noise
    I0: float = 5.0               # A, spindle current at V0
    K_I: float = 0.8              # A per mm/s, physical coupling vibration -> current
    SIGMA_I: float = 0.05         # A, current measurement noise
    LOSS: float = 0.01            # loss probability per update on the field link
    DELAY_ATTACK: float = 8.0     # s, delay injected by the gateway (T5)
    RESID_W: int = 10             # samples in the residual window (5 s)
    RESID_Z: float = 5.0          # z-score of the residual alarm
    HOLD: float = 5.0             # s, hold period used for recovery time I10
    CLOCK_ERR: float = 0.005      # s, max |clock offset| of sensor and gateway
    N_SEEDS: int = 30


PARAMS = Params()
CONFIGS = ["C0", "C1", "C2", "C3"]
ATTACKS = ["none", "replay", "delay", "spoof"]
ATTACK_LABEL = {"none": "No attack", "replay": "Replay + timestamp rewriting (T4, T6)",
                "delay": "Selective delay of 8 s (T5, T6)", "spoof": "Sensor spoofing (T1)"}


def v_true(t, p=PARAMS, degrade=True):
    if not degrade:
        return np.full_like(np.asarray(t, dtype=float), p.V0)
    t = np.asarray(t, dtype=float)
    return p.V0 + p.DEG_RATE * np.clip(t - p.T_DEG, 0.0, None)


def lognorm(rng, median, s, n=None):
    return median * np.exp(s * rng.standard_normal(n))


def simulate(attack, config, seed, p=PARAMS, t_end=None, degrade=True, trace=False,
             freshness_margin=0.0, rewrite_replay_timestamp=True):
    """Simulate one run; return indicators (and traces if asked).

    The default preserves the archived model's estimated-age decision. Set
    freshness_margin=p.CLOCK_ERR to implement the conservative clock-error
    guard in Eq. (1); this optional audit variant does not change the archive.
    Set rewrite_replay_timestamp=False to replay an intact source-signed object
    and isolate sequence rejection; gateway evidence is still rewritten.
    """
    if not 0 <= freshness_margin < p.D:
        raise ValueError("freshness_margin must satisfy 0 <= margin < D")
    ingest_bound = p.D - freshness_margin
    rng = np.random.default_rng(seed)
    t_end = p.T_END if t_end is None else t_end
    n = int(t_end / p.P)
    theta_s = rng.uniform(-p.CLOCK_ERR, p.CLOCK_ERR)   # sensor clock offset
    theta_g = rng.uniform(-p.CLOCK_ERR, p.CLOCK_ERR)   # gateway clock offset

    # ---- sensor: genuine vibration observations -------------------------------
    g = np.arange(n) * p.P + 0.01                       # true generation times
    vt = v_true(g, p, degrade)
    meas = vt + p.SIGMA_V * rng.standard_normal(n)
    if attack == "spoof":                               # T1: transducer sees a fake signal
        spoofed = (g >= p.T_ATTACK) & (g < p.T_ATTACK_END)
        meas[spoofed] = p.V0 + p.SIGMA_V * rng.standard_normal(spoofed.sum())
    lost = rng.random(n) < p.LOSS
    field = 0.005 + lognorm(rng, 0.010, 0.5, n)         # sensor -> gateway
    upstream = 0.010 + lognorm(rng, 0.010, 0.5, n)      # gateway -> broker -> twin
    t_gw = g + field                                    # reception at the gateway

    msgs = []   # (arrival, seq_src, ts_src, sig_ok, seq_gw, ts_gw, value, g_true, injected, genuine)
    seq_gw = 0
    # The gateway forwards in FIFO order and the gateway-broker-twin path runs
    # over TCP (MQTT over TLS), so messages leave and arrive in order.
    fifo = {"fwd": -1.0, "arr": -1.0}

    def send(fwd, k):
        fwd = max(fwd, fifo["fwd"] + 1e-4)
        arr = max(fwd + upstream[k], fifo["arr"] + 1e-4)
        fifo["fwd"], fifo["arr"] = fwd, arr
        return fwd, arr

    recorded = [k for k in range(n) if p.T_COMPROMISE <= t_gw[k] < p.T_ATTACK and not lost[k]]
    rep_i = 0
    for k in range(n):
        if lost[k]:
            continue
        in_attack = p.T_ATTACK <= t_gw[k] < p.T_ATTACK_END
        if attack == "replay" and in_attack:
            # drop the genuine update, send a recorded one instead with a fresh
            # gateway timestamp (C0 cannot tell). The source timestamp is
            # rewritten too, which breaks the source signature (C1+ reject).
            j = recorded[rep_i % len(recorded)]
            rep_i += 1
            seq_gw += 1
            fwd, arr = send(t_gw[k] + 0.001, k)
            replay_ts = fwd + theta_g if rewrite_replay_timestamp else g[j] + theta_s
            msgs.append((arr, j, replay_ts, not rewrite_replay_timestamp, seq_gw, fwd + theta_g,
                         meas[j], g[j], True, False))
            continue
        if attack == "delay" and in_attack:
            fwd, arr = send(t_gw[k] + 0.001 + p.DELAY_ATTACK, k)
            seq_gw += 1
            # the compromised gateway stamps at forwarding, hiding the delay in C0;
            # the source timestamp is signed and therefore preserved
            msgs.append((arr, k, g[k] + theta_s, True, seq_gw, fwd + theta_g,
                         meas[k], g[k], True, True))
            continue
        seq_gw += 1
        fwd, arr = send(t_gw[k] + 0.001, k)
        # an honest gateway stamps at reception (assumption A2); a compromised one
        # replaying or delaying stamps at forwarding (above)
        ts_gw = (t_gw[k] if fwd - t_gw[k] < 0.01 else fwd) + theta_g
        msgs.append((arr, k, g[k] + theta_s, True, seq_gw, ts_gw,
                     meas[k], g[k], False, True))
    msgs.sort(key=lambda m: m[0])

    # ---- spindle current over an independent path (controller -> twin) --------
    gi = np.arange(n) * p.P + 0.26
    cur = p.I0 + p.K_I * (v_true(gi, p, degrade) - p.V0) + p.SIGMA_I * rng.standard_normal(n)
    cur_arr = gi + 0.010 + lognorm(rng, 0.010, 0.5, n)
    cur_ok = rng.random(n) >= p.LOSS
    sigma_r = math.sqrt(p.SIGMA_V ** 2 + (p.SIGMA_I / p.K_I) ** 2)
    tau = p.RESID_Z * sigma_r / math.sqrt(p.RESID_W)    # alarm threshold on the mean residual

    # ---- twin ingestion --------------------------------------------------------
    applied = []        # (a_k, ts_used, g_true, value, injected, genuine)
    alerts = []         # (time, kind)
    last_seq_src, last_seq_gw = -1, 0
    state_ts = None
    resid_buf, resid_trace = [], []
    ci = 0              # index into current samples
    stale_raised = False
    for (arr, seq_src, ts_src, sig_ok, sgw, ts_gw, val, gtrue, inj, gen) in msgs:
        a = arr + 0.001
        # staleness monitor between arrivals (C2, C3): one alert per episode
        if (config in ("C2", "C3") and state_ts is not None and not stale_raised
                and a - state_ts > ingest_bound):
            alerts.append((state_ts + ingest_bound, "stale-state"))
            stale_raised = True
        if config == "C0":
            if sgw <= last_seq_gw:
                continue
            last_seq_gw = sgw
            applied.append((a, ts_gw, gtrue, val, inj, gen))
            state_ts = ts_gw
            continue
        # C1, C2, C3: source evidence
        if not sig_ok or seq_src <= last_seq_src:
            alerts.append((a, "integrity/replay"))
            continue
        if config in ("C2", "C3") and a - ts_src > ingest_bound:
            alerts.append((a, "stale-update"))
            continue
        last_seq_src = seq_src
        applied.append((a, ts_src, gtrue, val, inj, gen))
        state_ts = ts_src
        stale_raised = False
        if config == "C3":
            while ci + 1 < n and cur_arr[ci + 1] <= a:
                ci += 1
            while ci > 0 and not cur_ok[ci]:
                ci -= 1
            if cur_ok[ci] and cur_arr[ci] <= a and abs(gi[ci] - ts_src) <= p.D:
                r = val - (p.V0 + (cur[ci] - p.I0) / p.K_I)
                resid_buf.append(r)
                if len(resid_buf) > p.RESID_W:
                    resid_buf.pop(0)
                if len(resid_buf) == p.RESID_W:
                    m = float(np.mean(resid_buf))
                    resid_trace.append((a, m / tau))
                    if abs(m) > tau:
                        alerts.append((a, "consistency"))
    if (config in ("C2", "C3") and state_ts is not None and not stale_raised
            and t_end - state_ts > ingest_bound):
        alerts.append((state_ts + ingest_bound, "stale-state"))
    alerts.sort()

    # ---- indicators ------------------------------------------------------------
    A = np.array([x[0] for x in applied])
    TS = np.array([x[1] for x in applied])
    GT = np.array([x[2] for x in applied])
    VAL = np.array([x[3] for x in applied])
    INJ = np.array([x[4] for x in applied], dtype=bool)
    GEN = np.array([x[5] for x in applied], dtype=bool)

    step = 0.01 if t_end <= 1000 else 0.1
    grid = np.arange(0.0, t_end, step)
    idx = np.searchsorted(A, grid, side="right") - 1
    valid = idx >= 0
    age_meas = np.where(valid, grid - TS[np.clip(idx, 0, None)], np.nan)
    age_true = np.where(valid, grid - GT[np.clip(idx, 0, None)], np.nan)
    state_v = np.where(valid, VAL[np.clip(idx, 0, None)], np.nan)

    w = (grid >= p.T_ATTACK) & (grid < p.T_ATTACK_END)
    inw = (A >= p.T_ATTACK) & (A < p.T_ATTACK_END)
    n_expected = (p.T_ATTACK_END - p.T_ATTACK) / p.P
    res = {
        "attack": attack, "config": config, "seed": seed,
        "I1_meas_mean": float(np.nanmean(age_meas[w])), "I1_meas_peak": float(np.nanmax(age_meas[w])),
        "age_true_mean": float(np.nanmean(age_true[w])), "age_true_peak": float(np.nanmax(age_true[w])),
        "I2_meas": float(np.mean((A[inw] - TS[inw]) > p.D)) if inw.any() else float("nan"),
        "I2_true": float(np.mean((A[inw] - GT[inw]) > p.D)) if inw.any() else float("nan"),
        "I3_apparent": float(1 - inw.sum() / n_expected),
        "I3_true": float(1 - (inw & GEN).sum() / n_expected),
    }
    n_inj = sum(1 for m in msgs if m[8])
    res["I4"] = float(INJ.sum() / n_inj) if n_inj else float("nan")
    first_alert = alerts[0] if alerts else None
    res["first_alert_time"] = first_alert[0] if first_alert else float("nan")
    res["first_alert_kind"] = first_alert[1] if first_alert else ""
    res["alerts_in_attack"] = sum(1 for t, _ in alerts if p.T_ATTACK <= t < p.T_ATTACK_END)
    onset = p.T_DEG if attack == "spoof" else p.T_ATTACK
    res["I5"] = (first_alert[0] - onset) if (first_alert and attack != "none") else float("nan")
    # protective action: threshold on the twin state, or fail-safe hold on a C2/C3 alert
    t_thr = A[np.argmax(VAL > p.V_TH)] if (VAL > p.V_TH).any() else float("inf")
    t_fs = float("inf")
    if config in ("C2", "C3"):
        fs = [t for t, kind in alerts if kind in ("stale-state", "stale-update", "consistency")]
        t_fs = fs[0] if fs else float("inf")
    t_action = min(t_thr, t_fs)
    t_star = p.T_DEG + (p.V_TH - p.V0) / p.DEG_RATE if degrade else float("inf")
    res["t_star"] = t_star
    res["t_action"] = t_action
    res["action_cause"] = "fail-safe" if t_fs < t_thr else ("threshold" if math.isfinite(t_thr) else "none")
    res["action_minus_tstar"] = t_action - t_star
    dg = (grid >= p.T_DEG) & (grid < p.T_ATTACK_END)
    res["I7_rmse"] = float(np.sqrt(np.nanmean((state_v[dg] - v_true(grid[dg], p, degrade)) ** 2))) if degrade else float("nan")
    # recovery time I10 after the attack ends: age <= D continuously for HOLD
    after = grid >= p.T_ATTACK_END
    ok = age_meas[after] <= p.D
    rec = float("nan")
    need = int(round(p.HOLD / step))
    run = 0
    for i, flag in enumerate(ok):
        run = run + 1 if flag else 0
        if run >= need:
            rec = (i - need + 1) * step
            break
    res["I10"] = rec
    res["n_alerts"] = len(alerts)
    if trace:
        res["_trace"] = {"t": grid, "age_meas": age_meas, "age_true": age_true, "state_v": state_v,
                         "resid": np.array(resid_trace), "alerts": alerts}
    return res


def ci95(x):
    x = np.asarray([v for v in x if not (isinstance(v, float) and math.isnan(v))], dtype=float)
    if x.size == 0:
        return float("nan"), float("nan")
    if x.size == 1:
        return float(x[0]), 0.0
    return float(x.mean()), float(1.96 * x.std(ddof=1) / math.sqrt(x.size))


def fmt(m, h=None, nd=2):
    if m is None or (isinstance(m, float) and (math.isnan(m) or math.isinf(m))):
        return "--"
    return f"{m:.{nd}f}"


def main(outdir="."):
    p = PARAMS
    rows = []
    for attack in ATTACKS:
        for config in CONFIGS:
            for seed in range(1, p.N_SEEDS + 1):
                rows.append(simulate(attack, config, 1000 * ATTACKS.index(attack) + seed))
    keys = [k for k in rows[0].keys()]
    with open(os.path.join(outdir, "sim_results.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        wr.writerows(rows)

    summary = {"params": asdict(p), "cells": {}}
    for attack in ATTACKS:
        for config in CONFIGS:
            rs = [r for r in rows if r["attack"] == attack and r["config"] == config]
            cell = {}
            for k in ["I1_meas_mean", "I1_meas_peak", "age_true_mean", "age_true_peak", "I2_meas", "I2_true",
                      "I3_apparent", "I3_true", "I4", "I5", "I7_rmse", "I10", "action_minus_tstar",
                      "alerts_in_attack", "n_alerts"]:
                vals = [r[k] for r in rs if not (isinstance(r[k], float) and math.isinf(r[k]))]
                cell[k] = ci95(vals)
            cell["detected_runs"] = sum(1 for r in rs if r["first_alert_kind"]) / len(rs)
            cell["first_alert_kind"] = max(set(r["first_alert_kind"] for r in rs),
                                           key=lambda s: sum(1 for r in rs if r["first_alert_kind"] == s))
            causes = [r["action_cause"] for r in rs]
            cell["action_cause"] = max(set(causes), key=causes.count)
            cell["action_in_attack_runs"] = sum(1 for r in rs if r["t_action"] < p.T_ATTACK_END) / len(rs)
            summary["cells"][f"{attack}/{config}"] = cell
    with open(os.path.join(outdir, "sim_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    # ---- console report ----------------------------------------------------------
    for attack in ATTACKS:
        print("\n==", ATTACK_LABEL[attack])
        for config in CONFIGS:
            c = summary["cells"][f"{attack}/{config}"]
            print(f"  {config}: I1meas={fmt(c['I1_meas_mean'][0])}s trueAge={fmt(c['age_true_mean'][0])}s "
                  f"I2m={fmt(c['I2_meas'][0])} I2t={fmt(c['I2_true'][0])} I3app={fmt(c['I3_apparent'][0],nd=3)} "
                  f"I3true={fmt(c['I3_true'][0],nd=3)} I4={fmt(c['I4'][0])} det={c['detected_runs']:.2f} "
                  f"({c['first_alert_kind']}) I5={fmt(c['I5'][0])}±{fmt(c['I5'][1])} "
                  f"act-t*={fmt(c['action_minus_tstar'][0],nd=1)}±{fmt(c['action_minus_tstar'][1],nd=1)} "
                  f"[{c['action_cause']}] I7={fmt(c['I7_rmse'][0])} I10={fmt(c['I10'][0])}")

    # ---- false-alarm check: 10 h without attack and without degradation -------
    fa = {}
    for config in ("C2", "C3"):
        r = simulate("none", config, 99, t_end=36000.0, degrade=False)
        fa[config] = r["n_alerts"]
    print("\nalerts in 10 h of normal operation without degradation:", fa)
    summary["false_alarms_10h"] = fa
    with open(os.path.join(outdir, "sim_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    write_table(summary, os.path.join(outdir, "sim_table.tex"))
    make_figure(outdir)


def write_table(summary, path):
    p = PARAMS

    def num(x, nd):
        txt = f"{x:.{nd}f}"
        return f"$-${txt[1:]}" if txt.startswith("-") else txt

    lines = []
    labels = {"replay": "Replay with rewritten timestamps (T4, T6)",
              "delay": "Selective delay of 8\\,s (T5, T6)",
              "spoof": "Sensor spoofing (T1)"}
    for attack in ["replay", "delay", "spoof"]:
        for i, config in enumerate(CONFIGS):
            c = summary["cells"][f"{attack}/{config}"]
            lab = (f"\\multirow{{4}}{{*}}{{\\parbox{{2.25cm}}{{\\raggedright {labels[attack]}}}}}" if i == 0 else "")
            i1 = num(c["I1_meas_mean"][0], 2)
            tr = num(c["age_true_mean"][0], 1 if c["age_true_mean"][0] >= 10 else 2)
            i2 = ("--" if math.isnan(c["I2_meas"][0])
                  else f"{100*c['I2_meas'][0]:.0f} / {100*c['I2_true'][0]:.0f}")
            i3 = f"{100*c['I3_apparent'][0]:.0f} / {100*c['I3_true'][0]:.0f}"
            i4 = "--" if math.isnan(c["I4"][0]) else f"{100*c['I4'][0]:.0f}"
            if c["detected_runs"] > 0:
                kind = {"integrity/replay": "integrity", "stale-state": "staleness",
                        "stale-update": "staleness", "consistency": "consistency"}[c["first_alert_kind"]]
                i5 = f"{num(c['I5'][0], 2)} ({kind})"
            else:
                i5 = "none"
            amt = c["action_minus_tstar"][0]
            sgn = "+" if amt > 0 else ""
            if c["action_in_attack_runs"] < 0.5:
                act = f"after attack ends ({sgn}{num(amt, 0)}\\,s)"
            elif c["action_cause"] == "fail-safe":
                act = f"fail-safe hold ({num(amt, 0)}\\,s)"
            else:
                act = f"threshold ({sgn}{num(amt, 1)}\\,s)"
            i7 = num(c["I7_rmse"][0], 2)
            lines.append(f"{lab} & {config} & {i1} & {tr} & {i2} & {i3} & {i4} & {i5} & {act} & {i7} \\\\")
        lines.append("\\addlinespace")
    b = summary["cells"]["none/C0"]
    fa = summary.get("false_alarms_10h", {})
    lines.append(f"No attack & C0--C3 & {num(b['I1_meas_mean'][0], 2)} & {num(b['age_true_mean'][0], 2)} & "
                 f"0 / 0 & {100*b['I3_apparent'][0]:.0f} / {100*b['I3_true'][0]:.0f} & -- & "
                 f"none ({sum(fa.values())} in 10\\,h) & threshold ({num(b['action_minus_tstar'][0], 1)}\\,s) & "
                 f"{num(b['I7_rmse'][0], 2)} \\\\")
    with open(path, "w") as f:
        f.write("% generated by dt_sync_sim.py -- do not edit by hand\n")
        f.write("\n".join(lines) + "\n")
    print("wrote", path)


def make_figure(outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.ndimage import maximum_filter1d
    p = PARAMS
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "DejaVu Sans"],
        "font.size": 8, "axes.linewidth": 0.6, "axes.edgecolor": "#52514e",
        "xtick.color": "#52514e", "ytick.color": "#52514e", "pdf.fonttype": 42,
    })
    blue, orange, aqua, ink, muted, gridc, band = ("#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b",
                                                  "#52514e", "#e4e3df", "#f0efec")
    rep0 = simulate("replay", "C0", 7, trace=True)["_trace"]
    rep2 = simulate("replay", "C2", 7, trace=True)["_trace"]
    sp0 = simulate("spoof", "C0", 7, trace=True)["_trace"]
    sp3 = simulate("spoof", "C3", 7, trace=True)

    def envelope(y):          # 2 s running maximum: the peak age seen by a reader
        y = np.nan_to_num(y, nan=0.0)
        return maximum_filter1d(y, size=200, mode="nearest")

    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.45), gridspec_kw={"width_ratios": [1.15, 1, 1]})
    # (a) age under replay with rewritten timestamps
    ax = axs[0]
    t = rep0["t"]
    ax.axvspan(p.T_ATTACK, p.T_ATTACK_END, color=band, lw=0)
    ax.plot(t, envelope(rep0["age_true"]), color=orange, lw=1.6, ls="--", label="C0: true age")
    ax.plot(t, envelope(rep2["age_meas"]), color=blue, lw=1.6, label="C2: age from source timestamps")
    ax.plot(t, envelope(rep0["age_meas"]), color=ink, lw=1.4, label="C0: age from gateway timestamps")
    ax.axhline(p.D, color=muted, lw=0.8, ls=":")
    ax.text(470, p.D * 1.3, "$D$", color=muted, fontsize=7.5)
    ax.text(325, 0.045, "attack window", color=muted, fontsize=7, ha="center")
    ax.set_yscale("log")
    ax.set_ylim(0.03, 2000)
    ax.set_xlim(150, 500)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Age of twin state (s)")
    ax.set_title("(a) Replay with rewritten timestamps", fontsize=8, loc="left", color=ink)
    # direct labels (text in ink, next to the line it names)
    ax.text(205, 450, "C0: true age", fontsize=6.6, color=ink)
    ax.text(262, 12, "C2: age from\nsource timestamps", fontsize=6.6, color=ink)
    ax.text(205, 0.17, "C0: age from gateway timestamps", fontsize=6.6, color=ink)
    # (b) twin state vs process under sensor spoofing
    ax = axs[1]
    t = sp0["t"]
    ax.axvspan(p.T_ATTACK, p.T_ATTACK_END, color=band, lw=0)
    ax.plot(t, v_true(t), color=orange, lw=1.6, ls="--", label="True vibration")
    ax.plot(t, sp0["state_v"], color=ink, lw=0.9, label="Twin state, C0–C2")
    ax.axhline(p.V_TH, color=muted, lw=0.8, ls=":")
    ax.text(155, p.V_TH + 0.35, "stop threshold", color=muted, fontsize=7.5)
    ax.set_xlim(150, 500)
    ax.set_ylim(1.0, 18.0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Vibration velocity (mm/s)")
    ax.set_title("(b) Sensor spoofing: state vs. process", fontsize=8, loc="left", color=ink)
    ax.legend(fontsize=6.3, frameon=False, loc="upper left", handlelength=2.4)
    # (c) C3 residual around the degradation onset (zoom)
    ax = axs[2]
    rt = sp3["_trace"]["resid"]
    ax.plot(rt[:, 0], np.abs(rt[:, 1]), color=blue, lw=1.4, marker="o", ms=2.2,
            label="C3: |mean residual| / threshold")
    ax.axhline(1.0, color=muted, lw=0.8, ls=":")
    ta = sp3["first_alert_time"]
    ax.annotate(f"alarm at {ta:.1f} s", xy=(ta, 1.0), xytext=(ta + 6.0, 1.35), fontsize=7, color=ink,
                arrowprops=dict(arrowstyle="-", color=muted, lw=0.6))
    ax.axvline(p.T_DEG, color=muted, lw=0.6, ls="--")
    ax.text(p.T_DEG - 0.6, 5.85, "degradation\nonset", color=muted, fontsize=6.6, va="top", ha="right")
    ax.axvline(sp3["t_star"], color=muted, lw=0.6, ls="--")
    ax.text(sp3["t_star"] + 0.6, 5.85, "true threshold\ncrossing $t^*$", color=muted, fontsize=6.6, va="top")
    ax.set_xlim(290, 332)
    ax.set_ylim(0, 6)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("C3 |mean residual| / threshold")
    ax.set_title("(c) Sensor spoofing: C3 check (zoom)", fontsize=8, loc="left", color=ink)
    for ax in axs:
        ax.grid(True, color=gridc, lw=0.5)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.4, w_pad=0.9)
    os.makedirs(os.path.join(outdir, "figures"), exist_ok=True)
    out = os.path.join(outdir, "figures", "Figure_sim_traces.pdf")
    fig.savefig(out)
    fig.savefig(out.replace(".pdf", ".png"), dpi=200)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
