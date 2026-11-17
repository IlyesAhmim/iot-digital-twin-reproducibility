# Simulation validation

Execution dates: 4–6 November 2026. All new output files are backed by executed Python computations. No hardware or live network measurements were made. The original results and their hashes remain preserved.

## Reproduction and provenance

The unmodified scientific scripts were executed first. After adding optional audit controls and improving the Monte Carlo log precision, the entire original workflow was executed again. Both runs reproduced all original numerical results. The second complete log is `reports/reproduction_execution.log`; detailed per-script logs, runtime versions and comparison results are in `iot-digital-twin-reproducibility-main/results/reproduced/`.

| Baseline check | Result |
| --- | --- |
| Manufacturing CSV | All 480 rows match archive at absolute and relative tolerance 1e-9 |
| Manufacturing summary | All 16 cells, parameters and false-alarm counts match |
| Generated table fragment | Exactly matches archived table; the source-table no-attack label issue is identified below |
| CoAP CSV | All 51 rows match archive at tolerance 1e-9 |
| COSE sizes | All seven original byte-count fields match exactly |
| Normal operation | Zero alerts for C2 and C3, each in the original 10-hour seed-99 run |
| Generated figures | PDF and PNG outputs regenerated; existence checks passed; final manuscript visual inspection is handled in the editorial audit |
| Monte Carlo precision | Exact maximum .002110; prior rounded .0021 assertion corrected to .0022 bound |

The 480 original runs use seed `1000*scenario_index + j`, `j=1,...,30`, scenario order none/replay/delay/spoof. Configurations share the same random stream within each scenario. The displayed example traces use seed 7, independently of the summary seed blocks. Their values are therefore illustrative, not mean traces. All default outputs remain unchanged after the optional code changes.

Runtime: Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1, Matplotlib 3.11.2, cbor2 6.2.0.post2 and cryptography 50.0.2. These differ from some archived lock-file versions but reproduce the numerical archive. Missing libraries were installed in a temporary directory; no system Python installation was modified. `results/audit_environment.json` records runtime metadata and the original CSV SHA-256.

## Statistical validation

The independent unit is a run/seed. Time-grid samples and overlapping residual windows are not counted as independent observations. `results/statistical_summary.csv` contains per-cell sample size, mean, sample SD, Student-t 95% confidence interval for the mean, median and empirical 95th percentile. Student-t intervals are approximate uncertainty summaries of seed-to-seed simulation means, not guarantees for a deployed system. Undefined metrics are excluded with the remaining sample count recorded; in particular I2 is undefined when no update is applied.

`results/paired_comparisons.csv` computes within-seed configuration differences before estimating their uncertainty. Intervals are marginal, without multiple-comparison adjustment; no claims of statistical significance are made.

| Representative default metric | Mean | 95% CI for mean |
| --- | ---: | ---: |
| Replay, C0 measured age (s) | 0.27779 | [0.27625, 0.27934] |
| Replay, C0 true age (s) | 180.31854 | [180.22799, 180.40909] |
| Delay, C2 detection latency (s) | 1.51039 | [1.50926, 1.51152] |
| Delay, C2 recovery after attack end (s) | 7.53300 | [7.48590, 7.58010] |
| Spoof, C3 detection after degradation onset (s) | 4.48367 | [4.33163, 4.63571] |

C3 spoof latency has SD .40717 s, median 4.54706 s and empirical 95th percentile 5.04886 s. The 30/30 detected runs have a Wilson 95% detection-probability interval approximately [88.65%,100%], not evidence of perfect population detection. A 0/30 count has upper Wilson limit 11.35%; it does not establish impossibility of an event.

Paired C2-minus-C1 action-time differences are -248.53820 s under replay (95% CI [-248.54039,-248.53602]) and -131.24086 s under delay ([-131.48838,-130.99334]). C3-minus-C2 under spoofing is -145.56511 s ([-145.71772,-145.41250]). These are differences in recorded action times for the common hypothetical trajectory. They do not measure avoided physical damage or continued production.

## Targeted sensitivity: 1,470 additional runs

The saved script `iot-digital-twin-reproducibility-main/scripts/audit_analysis.py` executed all sensitivity cases with 30 seeds per cell. Raw results are `results/sensitivity_runs.csv`; summaries are `results/sensitivity_analysis.csv`; execution log is `reports/sensitivity_execution.log`.

The design is one factor at a time:

- Freshness bound D = .5, 1, 2, 5 s, for C2/C3 and all four scenarios: 960 runs.
- Both measurement-noise SDs scaled by .5 and 2 with the C3 threshold recalibrated, for normal operation and spoofing: 120 runs.
- Both SDs doubled with the threshold retained at its nominal value, for normal operation and spoofing: 60 runs.
- A conservative 5 ms clock guard for C2/C3 and all scenarios: 240 runs.
- Intact source signatures/timestamps on gateway replay, isolating rejection by the old source sequence number, for C1/C2/C3: 90 runs.

Normal-operation sensitivity runs last 600 s and disable degradation as well as attacks. They use the same normal-noise seeds across settings. Attack runs retain the original 600 s trajectory, including degradation. Correct detection is defined by an appropriate alarm class during the attack, with spoof consistency latency measured from degradation onset. Pre-onset alarms/holds are separately counted; they are never turned into negative detection latencies or claimed as successful attack detection.

### Freshness and availability

| D (s) | Benign runs with an alarm, per C2/C3 (of 30) | Mean C2/C3 delay-attack detection (s) |
| --- | ---: | ---: |
| .5 | 30 | .01039 |
| 1 | 30 | .51039 |
| 2 | 0 | 1.51039 |
| 5 | 0 | 4.51039 |

At .5 s, the freshness bound equals the reporting period, leaving no allowance for nonzero transport delay. At 1 s, occasional lost updates create genuine stale-state episodes. The alarms are thus **benign-network staleness alarms**, not necessarily false detections of freshness violations. The policy would nevertheless interrupt availability. Tight-bound attacked runs frequently held before the attack, so their apparent early action cannot be credited to attack detection. At D=2 and 5, all 30 attacked C2/C3 runs had no pre-onset hold; replay/delay detection and C3 spoof detection remain effective in this stylized model.

### Noise calibration

| Both noise SDs | C3 threshold | Mean spoof latency (s), 95% CI | Benign runs with any alarm |
| --- | --- | --- | ---: |
| .5 × nominal | Recalibrated | 3.24952 [3.14331,3.35573] | 0/30 |
| Nominal | Nominal | 4.48367 [4.33163,4.63571] | 0/30 |
| 2 × nominal | Recalibrated | 6.35081 [6.05871,6.64291] | 0/30 |
| 2 × nominal | Fixed nominal threshold | 4.39968 [4.04930,4.75005] | 30/30 |

All 30 spoof runs in each setting produced an appropriate post-onset consistency alarm. In the mismatched-noise case, however, every spoof run already had a hold before onset, so the apparent fast post-onset detection is not a successful availability-preserving configuration. The experiment establishes sensitivity to calibration, not robustness to arbitrary industrial noise.

### Clock guard and replay isolation

The archived policy has no conservative clock margin; the optional 5 ms guard follows the formal test for the simulated source/twin clock bound. Under delay, mean alarm latency changes from 1.51039 to 1.50539 s. The classification of attacks and observed benign alarms is unchanged at D=2. This control supports preserving the main displayed means while explaining their precise implementation.

In all 90 intact-source-signature replay controls, C1/C2/C3 rejected every injected replay (`I4=0`), with 30/30 appropriate alarms for each configuration. This supplements the original attack, where timestamp rewriting invalidates the signature and would otherwise confound attribution to sequence rejection. The original configuration implements a monotone sequence check on a FIFO path; it is not a general out-of-order replay-window implementation.

## Remaining limitations and minimal manuscript corrections

1. The model uses ideal Boolean cryptographic validity. The separate COSE script performs real classical signatures, but no full protected MQTT/CoAP stack is simulated.
2. Recorded fail-safe actions do not feed back into the vibration trajectory. RMSE after a recorded hold describes the counterfactual observation trajectory, not the vibration of a physically stopped machine. No degraded-operation policy or restart dynamics were experimentally evaluated.
3. I3 includes rejected and out-of-window updates, so it cannot be read as field-link loss. I10 uses estimated age and cannot independently verify truthful recovery under timestamp manipulation.
4. The no-attack table's combined row copied C0 I1=.28 s to all configurations; C1–C3 instead round to .29 s. All displayed attack means reproduce.
5. Zero alerts in a single 10-hour run per configuration do not establish a zero false-alarm rate. The 30 shorter no-attack controls provide separate per-run evidence and must not be pooled as independent overlapping windows.
6. Threshold calibration assumes the model's linear coupling and noise. Model mismatch, dependent sensor errors, correlated losses, compromised current sensing, adaptive attacks, clock drift attacks and real-device costs are not validated by these runs.
7. A clock guard is now reproducible as a separate optional variant. The original default must not be described as an exact implementation of the conservative formal inequality.
8. The original [public GitHub repository](https://github.com/IlyesAhmim/iot-digital-twin-reproducibility) was accessible on 5 November 2026 and exposes the original scripts/reference outputs. The new audit scripts and results have only been added to this local project. Publishing those additions, creating an archival release DOI, and specifying a reuse license remain author-controlled tasks. No new public release was fabricated.

## Independent reviewer check, 6 November

An independent recalculation verified all saved Student-t mean intervals and paired contrasts to absolute tolerance `1e-10`, the 480 baseline and 1,470 sensitivity row counts, and the baseline CSV's byte identity with the original archive. A targeted code inspection found that C3 could use current sample 0 despite its loss flag: backtracking stopped at index 0, but the subsequent residual condition did not check that sample's availability. Read-only instrumentation observed this at approximately 0.54–0.56 s in normal-operation seeds 11, 15 and 19. The condition now explicitly requires `cur_ok[ci]`.

After that correction, all 120 C3 baseline runs and all 810 C3 sensitivity runs were re-executed and compared with their saved results. Every recorded metric and derived detection field remained unchanged within `1e-12`; C0–C2 do not enter the corrected branch. The entire original `run_all.py` workflow then passed again, including all 480 baseline rows, summaries, 10-hour zero-alert checks, CoAP calculations and COSE sizes. No reference or result CSV was changed to obtain a pass. Logs are in `reports/reviewer4_reproduction_execution.log`; detailed checks are in `reports/reviewer4_independent_checks.json` and `reports/reviewer4_current_loss_fix_checks.json`. `scripts/check_current_sample_loss.py` reproduces the comparison against the saved C3 rows.

The finite-window metrics retain their original definitions: I2 is evaluated at application (arrival plus 1 ms), I3 counts application within the evaluation window, and I10 searches the sampled measured-age trace for the start of a five-second fresh interval. In the 600 s runs its grid is 0.01 s. I10 is neither a physical restart time nor an exact continuous-time certificate; the optional clock guard changes ingestion/alarm decisions, while I10 still uses measured age compared with D.

## Commands to reproduce

From the manuscript root, in an environment containing the direct Python dependencies:

```bash
python iot-digital-twin-reproducibility-main/run_all.py
python iot-digital-twin-reproducibility-main/scripts/audit_analysis.py
```

The first command verifies the archived reference data; the second writes all top-level result CSVs. On this audit host the interpreter was `/home/postdoc/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`, with `PYTHONPATH=/tmp/comst-audit-python`. That temporary dependency path is an execution detail, not a required component of the reproducibility package. The original lock file is retained and a separate audit lock records this run's versions.
