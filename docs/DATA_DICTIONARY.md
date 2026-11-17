# Data dictionary

All numerical data are synthetic or analytically computed. Parameters are defined
in `scripts/dt_sync_sim.py` (`Params`) and saved in `sim_summary.json` under `params`.
Time is measured in seconds unless otherwise indicated; probabilities and ratios
are stored as fractions, not percentages.

## coap_timeliness.csv

51 rows, with `p` ranging from 0 to 0.5 in steps of 0.01.

| Column | Meaning |
| --- | --- |
| `p` | Independent loss probability per transmission |
| `delivered` | Delivery probability over at most five transmissions, `1 - p**5` |
| `timely_D2`, `timely_D5`, `timely_D10`, `timely_D20` | Unconditional probability of delivery within the named bound in seconds |

The initial timeout is uniform on [2, 3] s; one-way delay is 0.05 s.

## sim_results.csv

One row per scenario/configuration/seed combination (480 rows).

| Column | Meaning / unit |
| --- | --- |
| `attack` | `none`, `replay`, `delay`, or `spoof` |
| `config` | `C0`: gateway evidence; `C1`: source authenticity/replay check; `C2`: C1 plus staleness response; `C3`: C2 plus physical consistency |
| `seed` | Actual integer seed passed to NumPy's random generator |
| `I1_meas_mean`, `I1_meas_peak` | Mean/maximum age of held twin state computed from trusted timestamps (s) |
| `age_true_mean`, `age_true_peak` | Mean/maximum age of the same state's true observation (s) |
| `I2_meas`, `I2_true` | Fraction of applied updates missing freshness bound at application (arrival plus 1 ms processing), using trusted/true timestamps |
| `I3_apparent` | One minus number of applied updates divided by expected updates in the evaluation window |
| `I3_true` | One minus number of genuine applied updates divided by expected updates in the evaluation window |
| `I4` | Fraction of gateway-injected replay/delay messages applied; undefined when none are injected |
| `first_alert_time` | Time of first alert anywhere in run (s), undefined if no alert |
| `first_alert_kind` | `integrity/replay`, `stale-state`, `stale-update`, `consistency`, or empty |
| `alerts_in_attack` | Number of alert events within [200, 450) s |
| `I5` | First-alert latency from attack start, or from degradation onset for spoofing (s); undefined without detection or for `none` |
| `t_star` | Ground-truth vibration threshold crossing, 325 s in the default runs |
| `t_action` | Earliest threshold-triggered action or eligible C2/C3 fail-safe action (s) |
| `action_cause` | `threshold`, `fail-safe`, or `none` |
| `action_minus_tstar` | Protective action time minus `t_star` (s); negative means early |
| `I7_rmse` | RMSE between held twin vibration and ground truth in [300, 450) s (mm/s) |
| `I10` | Time after 450 s until the start of 5 s of consecutive samples with measured state age <= D (D = 2 s by default; 0.01 s grid in the 600 s runs) |
| `n_alerts` | Total alert events in the run; may count repeated consistency/update alarms |

I1 and true-age statistics use the state on a 0.01 s grid over [200, 450) s.
I2 and I3 use applied updates whose arrival times lie in that window. Expected
update count is 500. I4 counts injected messages across the full message list.
The `none` scenario uses the same evaluation windows for comparability.
The 10-hour false-alarm runs use a 0.1 s grid and are summarized separately.

An integrity/replay alert by itself does not trigger a fail-safe action; C2/C3 act
on stale-state, stale-update or consistency alerts. Spoofing is performed at the
sensor and is not marked as gateway injection, so I4 is undefined for spoofing.

## sim_summary.json and sim_table.tex

- `params`: model parameters, including 600 s duration, 0.5 s reporting period,
  2 s freshness bound, 200-450 s attack window, and 30 seeds per combination.
- `cells`: 16 keys of the form `scenario/configuration`.
- Most cell indicators are `[mean, 95% confidence-interval half-width]`, with
  half-width `1.96 * sample_standard_deviation / sqrt(n)` after exclusion of
  undefined/infinite values. This is a normal-approximation interval.
- `detected_runs`: fraction of runs with any first alert.
- `first_alert_kind` and `action_cause`: modal categories across runs.
- `action_in_attack_runs`: fraction with protective action before 450 s.
- `false_alarms_10h`: alert counts for the separate C2 and C3 runs using seed 99.

Undefined values are `nan` in CSV and `NaN` in the original Python JSON encoding.
They must not be interpreted as zero. `sim_table.tex` renders selected means and
fractions as rounded text for Table 12; it omits confidence intervals. The combined
no-attack row uses C0 statistics, as in the original table-generation script;
configuration-specific statistics remain available in the CSV and JSON files. The
revised manuscript explicitly shows C0/C1–C3 I1 as 0.28/0.29 s; the original
reference table is retained for reproducibility.

## cose_overhead.json

Keys ending in `_bytes` store exact CBOR/COSE object lengths or differences from
the plain 23-byte payload. Objects include their COSE tag, protected algorithm
header and one-byte key identifier. The payload contains sequence number
1,234,567, timestamp 1,793,000,000,000 ms and a float32 vibration value of 2.0371.
Sizes exclude lower-layer headers and transport overhead.

`host_EdDSA_sign_us` and `host_EdDSA_verify_us` are average host execution times in
microseconds over 2,000 operations. They are machine-dependent and are not the
paper's measurements of constrained devices. The reference values are retained
only as part of the original output file and are excluded from verification.

## Audit outputs in the parent manuscript's `results/`

- `simulation_runs.csv`: exact copy of the newly reproduced original 480 rows.
- `statistical_summary.csv`: run-level Student-t 95% intervals, sample SD, median
  and empirical 95th percentile; Wilson intervals for runs with alerts.
- `paired_comparisons.csv`: configuration contrasts computed within the same seed
  before the Student-t interval; not independent-arm tests.
- `sensitivity_runs.csv`: 1,470 executed additional runs. `family` identifies the
  changed factor. `clock_margin_s=0` preserves the original policy; .005 implements
  the conservative guard. `intact_replay` preserves the authentic source timestamp
  and signature while replaying an old sequence. In normal-operation controls,
  `degradation=False`; attack runs retain the original process trajectory.
- `sensitivity_analysis.csv`: per-cell summaries. `correct_detection` requires an
  attack-appropriate alarm within the attack window; `pre_onset_hold` separately
  identifies holds before attack/degradation onset. `benign_run_alert` is defined
  only for no-attack runs; true staleness due to benign loss is included, so it is
  not necessarily a false freshness detection. Latencies exclude absent detection
  and report the effective sample count. Empty CSV cells mean a field does not
  apply to that row; `nan` means an undefined numeric quantity.
- `coap_independent_checks.csv`: enumeration/quadrature and closed-form comparisons.
- `coap_monte_carlo.csv`: unrounded original Monte Carlo check results.
- `coap_correlated_loss_sensitivity.csv`: illustrative attempt-indexed stationary
  two-state losses; conditional loss probabilities, exact and simulated outcomes.
- `cose_extended_sizes.csv`: tagged COSE encoding with fixed-length placeholder
  signatures, including ML-DSA; confirms serialization sizes, not PQ signing.
- `clock_bound_check.json`: numerical sanity check of the proved clock inequality.
- `audit_environment.json`: actual versions, counts and original CSV hash.

Intervals are marginal, not simultaneous. The unit of replication is a seed/run,
not a time-grid sample or residual window. These intervals quantify Monte Carlo
variation conditional on the stylized model; they do not establish field validity.
