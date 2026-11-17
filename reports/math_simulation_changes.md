# Mathematical and simulation change record

This audit preserves the original model defaults, scientific tables and nine archived reference files. All work below was executed; the reproducibility logs and data are supplied.

| Location | Problem / likely objection | Minimal change | Verification / benefit |
| --- | --- | --- | --- |
| `scripts/coap_timeliness.py`, `verify_results.py` | Four-decimal rounding hid an exact .002110 discrepancy exceeding the literal manuscript bound .0021 | Print six decimals; use .0022 bound | Full original workflow passes with explicit .002110; probabilities unchanged |
| `scripts/dt_sync_sim.py` | Default estimated-age gate does not include source clock error | Optional `freshness_margin`, default zero | Added .005 s guard control, 240 runs; default outputs remain identical |
| `scripts/dt_sync_sim.py` | Rewritten source timestamp invalidates signature, confounding evidence for sequence rejection | Optional intact-source replay control, default unchanged | 90 runs reject all replays and detect all 90 cases |
| `scripts/dt_sync_sim.py` documentation | Replay-window wording exceeds implemented monotone check | Correct docstring | Matches FIFO implementation |
| `scripts/audit_analysis.py` | Uncertainty omitted from displayed means; no reproducible sensitivity evidence | Saved full audit script | 480 baseline statistics, paired seed contrasts, 1470 sensitivity runs, 168 independent CoAP enumeration checks, separate Markov loss MC, encoding-size and clock sanity checks |
| Top-level `results/` | Missing auditable raw/summarized additional results | Save raw and aggregate CSVs plus environment metadata | All result rows backed by execution |
| `requirements-audit-lock.txt` | Audit runtime differs from historical lock file | Preserve original lock; record actual audit versions separately | Full archive numerical equality despite version differences |
| `SHA256SUMS-audit.txt` | Original script hashes no longer describe optional-control/logging changes | Preserve historical hash file; add current one | All nine original reference hashes confirmed unchanged |
| README, CITATION, data dictionary, validation record | Old manuscript title and appendix labels; missing new-output semantics | Update local metadata and append audit methods/history | Original historical records retained; public original repository distinguished from unpublished local additions |
| `reports/math_audit.md`, `reports/simulation_validation.md` | Proof assumptions and implementation limits needed explicit evidence | Add derivations, verified primary-source links, actual result tables and limitations | Supports precise manuscript qualifications without redesign |

Recommended manuscript updates already communicated to the coordinating editor:

- Make the clock errors explicit at generation and decision, retain the freshness inequality and definition, and clarify state dependency/ordering assumptions.
- Identify uniform timeout as a modeling assumption and distinguish single-message deadline probability from stream AoI.
- Use the corrected Monte Carlo bound `2.2×10^-3`.
- Disclose idealized signature flags, monotone sequence rejection and action recording without physical feedback.
- Correct the combined no-attack I1 entry to C0 .28 s / C1–C3 .29 s; explain finite-window/rejection components of I3.
- Include compact run-level uncertainty and the substantive D/noise findings. Extra raw results remain supplementary.
- Explain that the default estimated-age policy and the additional 5 ms conservative guard are different variants.
- Keep PQ sizes as serialization calculations, not cryptographic or embedded-platform timing experiments.

The formal, original CoAP and attack simulation conclusions remain valid within their now-explicit scope. No additional experiment was used to manufacture a stronger security or deployment guarantee.
