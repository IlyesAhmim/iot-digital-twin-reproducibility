# Repository publication guide

This guide describes how to publish the code and generated data accompanying the
submitted manuscript. It covers
repository preparation, version identification, and the data availability statement.

## 1. Create the repository

Create a public GitHub repository named `iot-digital-twin-reproducibility`, or use
another descriptive name. To follow the commands below, create an empty repository
without an automatically generated README, `.gitignore`, or license file. This
package already provides the README and `.gitignore`. The authors should select
an appropriate reuse license and add its text to the repository.

## 2. Upload the code and reference data

Open a terminal in the root of this package. Replace `YOUR_ACCOUNT` with the
GitHub account or organization name and adjust the repository name if necessary.

```bash
git init -b main
git add .
git commit -m "Add manuscript reproducibility code and reference results"
git remote add origin https://github.com/YOUR_ACCOUNT/iot-digital-twin-reproducibility.git
git push -u origin main
```

Authenticate with GitHub when prompted. The reference outputs in
`results/reference/` are included in version control. Locally regenerated outputs
in `results/reproduced/` are excluded by `.gitignore`.

After uploading, confirm that the repository and its files are publicly accessible.
The example addresses in this guide are placeholders and must be replaced with
the actual repository URL before using the data availability statement.

## 3. Identify the submitted version

Create an annotated tag to identify the code and data associated with the manuscript:

```bash
git tag -a v1.0.0 -m "Code and data accompanying the submitted manuscript"
git push origin v1.0.0
```

Record the tag and corresponding commit identifier with the submission materials.
Subsequent changes can be assigned a new version so that readers can distinguish
the submitted results from later developments.

## 4. Complete the data availability statement

Replace `[repository URL]` with the public repository address in the following text:

> The source code and generated data supporting the closed-form analysis
> (Section 7.2), the simulation study (Section 8.6), and the computation of message
> overheads are publicly available at [repository URL].

For a LaTeX manuscript using `hyperref`, use:

```latex
The source code and generated data supporting the closed-form analysis
(Section 7.2), the simulation study (Section 8.6), and the computation of
message overheads are publicly available at
\url{https://github.com/YOUR_ACCOUNT/iot-digital-twin-reproducibility}.
```

Use this statement once the repository is public and the uploaded files have been
checked. The term "generated data" identifies the analytical and simulation outputs
provided here; it does not imply measurements from a physical deployment.

## 5. Complete the citation metadata

Add the actual repository URL to `CITATION.cff` using the `repository-code` field.
Once a release has been published, add its version and release date. Add the article
DOI when it has been assigned. Keep the software version and article citation
consistent with the material made available to readers.

## Reproduction and verification

Installation and execution instructions are provided in [README.md](README.md).
The command `python run_all.py` executes all three analyses and compares the
generated outputs with the reference results. The completed verification is
documented in [the validation record](docs/VALIDATION.md); indicator definitions
and units are provided in [the data dictionary](docs/DATA_DICTIONARY.md).
