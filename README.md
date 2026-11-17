# Synchronization assurance for IoT-enabled digital twins

Scientific code and saved simulation results accompanying the manuscript by **Ilyes Ahmim and Abderrezak Rachedi**:

*Synchronization Assurance for IoT-Enabled Digital Twins: A Review of Cross-Layer Threats, Protocols, Standards, and Indicators*.

This package includes the existing CoAP analytical model, C0–C3 manufacturing-cell simulation, COSE size computations, statistical summaries, and saved sensitivity analyses. All scientific scripts and result files are copied unchanged from the revised author project. Packaging did **not** rerun simulations or independently revalidate the scientific findings.

## Layout

```text
iot-digital-twin-reproducibility-main/
  run_all.py
  verify_results.py
  scripts/                  # Original scientific and audit scripts
  results/reference/        # Original reference outputs
  requirements*.txt         # Historical and audit environments
results/                    # Saved 480 baseline and 1,470 sensitivity rows + summaries
reports/                    # Existing numerical checks and limitations
docs/                       # Data dictionary, validation history, model specification
CITATION.cff
requirements-audit-lock.txt
```

The nested scientific-code directory is intentional: the audit scripts use its parent `results/` and `reports/` directories. Keep this layout. Reference outputs and saved audit results are included; regenerated duplicate outputs and caches are excluded.

## Inspect existing results without rerunning experiments

Read `results/simulation_runs.csv`, `results/sensitivity_runs.csv`, `results/statistical_summary.csv` and `results/paired_comparisons.csv`. Methods and limitations are documented in `reports/simulation_validation.md` and `reports/math_audit.md`. `SHA256SUMS.txt` verifies the contents of this package with `sha256sum -c SHA256SUMS.txt` on systems providing that command.

## Reproduce later, when desired

The historical audit environment is recorded for Python 3.12. From **this package root**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-audit-lock.txt
python iot-digital-twin-reproducibility-main/run_all.py
python iot-digital-twin-reproducibility-main/scripts/audit_analysis.py
```

These commands execute simulations; they were not run during packaging. `run_all.py` writes `iot-digital-twin-reproducibility-main/results/reproduced/` and compares it with the reference data. `audit_analysis.py` then writes the top-level `results/`, replacing the generated audit CSV/JSON outputs. Review or preserve local changes before rerunning.

The optional targeted regression check also reruns C3 simulations:

```bash
python iot-digital-twin-reproducibility-main/scripts/check_current_sample_loss.py
```

It compares the affected C3 outputs with saved results and writes `reports/reviewer4_current_loss_fix_checks.json`. No LaTeX installation, institutional database access or external experimental dataset is needed for the numerical workflows. Dependency installation needs access to the applicable package distributions; their availability was not retested during packaging.

## Mapping to the current manuscript

| Component | Location in manuscript |
|---|---|
| CoAP timeliness | Section VII-B, Eq.(2), Fig.6 |
| Manufacturing simulation | Section VIII-F, configurations C0–C3, Table XIII, Fig.8 |
| Model parameters | Appendix A and supplementary simulation specification |
| COSE overhead | Sections V-B and VIII-F, indicator I11 |
| Uncertainty/sensitivity | Saved supplementary CSV files and numerical reports |

The model is illustrative, uses stylized attacks and idealized cryptographic checks, and does not establish hardware performance or closed-loop safety. Read the detailed limitations before reusing the results. Historical section numbering or bibliography links in copied audit reports refer to their original manuscript versions; the source manuscript/bibliography are in the separate Overleaf package. The supplementary PDF's literature-inventory command belongs to the full manuscript project and is not part of this scientific-code package.

## Citation and publication

`CITATION.cff` preserves the supplied authors and existing repository URL. No DOI, release tag, license or new publication status has been invented. The source project does not specify a reuse license; the authors retain that decision. This folder is ready to be version-controlled, but no GitHub publication or push has been performed. See `PUSH_TO_GITHUB.md` for the two possible workflows.
