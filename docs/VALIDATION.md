# Validation record

Validation date: **30 October 2026**.

The complete `python run_all.py` workflow was executed successfully using Python
3.12.14 on Linux x86_64. The exact installed package versions are recorded in
`requirements-lock.txt`; the direct dependencies were NumPy 2.3.5, SciPy 1.18.1,
Matplotlib 3.11.2, cbor2 6.1.5 and cryptography 50.0.2.

| Check | Result |
| --- | --- |
| Computational preservation | All three scientific scripts retain the original executable code; only explanatory documentation has been updated |
| Reference preservation | All nine reference files are byte-identical to the original supplementary outputs |
| CoAP closed-form output | All 51 CSV rows match the reference at absolute/relative tolerance `1e-9` |
| Monte Carlo check | Printed maximum absolute discrepancy `0.0021` for 400,000 trials per tested point |
| Simulation runs | All 480 CSV rows match the reference at absolute/relative tolerance `1e-9` |
| Simulation summary | All parameters, indicators in all 16 cells and false-alarm counts match at the same tolerance |
| Generated table | `sim_table.tex` matches the reference exactly |
| False alarms | Zero alerts for C2 and C3, each over 10 simulated hours without attack or degradation |
| COSE message lengths | Plain CBOR 23 bytes; Ed25519/ES256 Sign1 100 bytes; HMAC-256/64 Mac0 43 bytes |
| COSE overhead | Sign1 77 bytes; Mac0 20 bytes; all seven byte-count fields match exactly |
| Figures | Both PDF figures regenerated and rendered to images for visual inspection; labels and panels are readable |

Reference checks establish reproduction of the supplied supplementary results.
They are not an independent scientific validation of the model assumptions or a
hardware experiment. The relevant manuscript equation, Table 12, Figure 5 and
Appendix B were inspected to establish the documentation mapping.

Host cryptographic timings are deliberately excluded from equality checks. Their
values depend on the execution machine and are not constrained-device measurements.
PDF and PNG byte equality is not required; font selection, graphics libraries and
PDF metadata may differ. The automatic verifier checks that these files exist;
visual inspection was performed separately for this preparation.

To repeat the numerical checks after a full run:

```bash
python verify_results.py
```

The runner writes fresh logs, environment metadata and a machine-readable
verification report into `results/reproduced/` on each successful execution.
That directory is intentionally excluded from Git; the reference outputs and
this record are included.
