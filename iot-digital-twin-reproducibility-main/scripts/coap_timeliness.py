#!/usr/bin/env python3
"""Delivery versus timeliness of a confirmable CoAP update (RFC 7252 defaults).

Closed-form model used in Section 7.2 of the manuscript, checked by Monte Carlo.

Model
-----
* A confirmable (CON) message is sent at t = 0 (generation time g_k = 0).
* With the default transmission parameters of RFC 7252 (Sec. 4.8):
  ACK_TIMEOUT = 2 s, ACK_RANDOM_FACTOR = 1.5, MAX_RETRANSMIT = 4,
  the initial timeout T0 is drawn uniformly in [2, 3] s and doubles after each
  retransmission (Sec. 4.2). Transmission i (i = 0..4) therefore leaves at
  s_i = (2**i - 1) * T0.
* Each transmission is lost independently with probability p. A lost ACK only
  triggers a duplicate, so the twin receives the reading at the first successful
  transmission K, with P(K = i) = p**i (1 - p).
* d is the one-way network delay (constant).

Then
    P(delivered)       = 1 - p**5
    P(age <= D)        = sum_i p**i (1 - p) * P((2**i - 1) T0 + d <= D)
with P((2**i - 1) T0 <= x) = clip((x / (2**i - 1) - 2) / 1, 0, 1) for i >= 1.

Outputs: coap_timeliness.csv, figures/Figure_coap_timeliness.pdf and a short
summary printed on stdout. Run:  python3 coap_timeliness.py
"""
import csv
import os

import numpy as np

ACK_TIMEOUT, ACK_RANDOM_FACTOR, MAX_RETRANSMIT = 2.0, 1.5, 4
T0_MIN, T0_MAX = ACK_TIMEOUT, ACK_TIMEOUT * ACK_RANDOM_FACTOR
N_TX = MAX_RETRANSMIT + 1
D_ONEWAY = 0.05  # s, one-way network delay


def p_send_by(i, x):
    """P((2**i - 1) * T0 <= x) for T0 ~ U[T0_MIN, T0_MAX]."""
    if i == 0:
        return 1.0 if x >= 0 else 0.0
    t = x / (2 ** i - 1)
    return float(np.clip((t - T0_MIN) / (T0_MAX - T0_MIN), 0.0, 1.0))


def p_delivered(p):
    return 1.0 - p ** N_TX


def p_timely(p, D, d=D_ONEWAY):
    return sum(p ** i * (1 - p) * p_send_by(i, D - d) for i in range(N_TX))


def monte_carlo(p, D, n=400_000, d=D_ONEWAY, seed=1):
    rng = np.random.default_rng(seed)
    t0 = rng.uniform(T0_MIN, T0_MAX, n)
    lost = rng.random((n, N_TX)) < p
    first_ok = np.argmax(~lost, axis=1)
    delivered = (~lost).any(axis=1)
    age = (2.0 ** first_ok - 1.0) * t0 + d
    return delivered.mean(), (delivered & (age <= D)).mean()


def main(outdir="."):
    ps = np.round(np.arange(0.0, 0.501, 0.01), 3)
    Ds = [2.0, 5.0, 10.0, 20.0]
    rows = []
    for p in ps:
        row = {"p": p, "delivered": p_delivered(p)}
        for D in Ds:
            row[f"timely_D{int(D)}"] = p_timely(p, D)
        rows.append(row)
    with open(os.path.join(outdir, "coap_timeliness.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Monte Carlo check of the closed form
    worst = 0.0
    for p in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
        for D in Ds:
            mc_del, mc_tim = monte_carlo(p, D)
            worst = max(worst, abs(mc_del - p_delivered(p)), abs(mc_tim - p_timely(p, D)))
    print(f"max |closed form - Monte Carlo| = {worst:.6f} (400k samples per point)")
    for p in (0.1, 0.2, 0.3):
        print(f"p={p:.1f}: delivered={p_delivered(p):.4f}  "
              + "  ".join(f"timely(D={int(D)}s)={p_timely(p, D):.3f}" for D in Ds))

    # ---- figure -------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "DejaVu Sans"],
        "font.size": 8.5, "axes.linewidth": 0.6, "axes.edgecolor": "#52514e",
        "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.labelcolor": "#0b0b0b",
        "pdf.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(5.2, 2.75))
    ink, muted = "#0b0b0b", "#52514e"
    ax.plot(ps, [r["delivered"] for r in rows], color=ink, lw=2.0,
            label="Delivered, any age ($1-p^5$)")
    styles = {2: ("#2a78d6", "-"), 5: ("#eb6834", "--"), 10: ("#1baf7a", "-."), 20: ("#6250d6", ":")}
    for D in Ds:
        col, ls = styles[int(D)]
        ax.plot(ps, [r[f"timely_D{int(D)}"] for r in rows], color=col, lw=2.0, ls=ls,
                label=f"Delivered with age $\\leq D$ = {int(D)} s")
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0.45, 1.005)
    ax.set_xlabel("Per-transmission loss probability $p$")
    ax.set_ylabel("Probability")
    ax.grid(True, color="#e4e3df", lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # direct label on two curves (selective), plus legend for all
    ax.annotate("$D$ = 2 s: $1-p$\n(first transmission only)", xy=(0.42, p_timely(0.42, 2.0)), xytext=(0.255, 0.53),
                fontsize=8, color=muted, arrowprops=dict(arrowstyle="-", color=muted, lw=0.6))
    ax.legend(loc="lower left", fontsize=7.5, frameon=False, handlelength=2.6)
    fig.tight_layout(pad=0.4)
    os.makedirs(os.path.join(outdir, "figures"), exist_ok=True)
    out = os.path.join(outdir, "figures", "Figure_coap_timeliness.pdf")
    fig.savefig(out)
    fig.savefig(out.replace(".pdf", ".png"), dpi=200)
    print("wrote", out)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
