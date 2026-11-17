#!/usr/bin/env python3
"""Compare a full reproduction against the manuscript reference results."""
import argparse
import csv
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / 'results' / 'reference'


def compare(actual, expected, location):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), f'{location}: keys differ'
        for key in expected:
            compare(actual[key], expected[key], f'{location}/{key}')
    elif isinstance(expected, list):
        assert len(actual) == len(expected), f'{location}: lengths differ'
        for index, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, f'{location}/{index}')
    else:
        try:
            a, e = float(actual), float(expected)
        except (ValueError, TypeError):
            assert actual == expected, f'{location}: {actual!r} != {expected!r}'
            return
        equal = (math.isnan(a) and math.isnan(e)) or math.isclose(a, e, rel_tol=1e-9, abs_tol=1e-9)
        assert equal, f'{location}: {actual!r} != {expected!r}'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results' / 'reproduced')
    output = parser.parse_args().output.resolve()
    checks = []
    for name, count in (('coap_timeliness.csv', 51), ('sim_results.csv', 480)):
        actual = read_csv(output / name)
        assert len(actual) == count, f'{name}: expected {count} rows'
        compare(actual, read_csv(REFERENCE / name), name)
        checks.append(f'{name}: all {count} rows match (rtol=atol=1e-9).')
    compare(json.loads((output / 'sim_summary.json').read_text()),
            json.loads((REFERENCE / 'sim_summary.json').read_text()), 'sim_summary.json')
    checks.append('sim_summary.json: all parameters, 16 cells and false-alarm counts match.')
    assert (output / 'sim_table.tex').read_text() == (REFERENCE / 'sim_table.tex').read_text(), 'Table rows differ'
    checks.append('sim_table.tex: identical manuscript table rows.')
    actual = json.loads((output / 'cose_overhead.json').read_text())
    expected = json.loads((REFERENCE / 'cose_overhead.json').read_text())
    for key, value in expected.items():
        if key.endswith('_bytes'):
            assert actual[key] == value, f'{key}: message size differs'
    checks.append('COSE: all seven message-size/overhead values match exactly; host timings excluded.')
    log = (output / 'logs' / 'coap_timeliness.log').read_text()
    match = re.search(r'max \|closed form - Monte Carlo\| = ([0-9.]+)', log)
    assert match and float(match[1]) <= 0.0022, 'Monte Carlo discrepancy exceeds manuscript bound'
    checks.append(f'CoAP Monte Carlo: reported maximum discrepancy {match[1]} <= 0.0022.')
    for stem in ('Figure_coap_timeliness', 'Figure_sim_traces'):
        for suffix in ('.pdf', '.png'):
            path = output / 'figures' / (stem + suffix)
            assert path.is_file() and path.stat().st_size > 0, f'Missing figure: {path}'
    checks.append('Both figures exist in PDF and PNG (visual equivalence is not asserted here).')
    report = {'status': 'passed', 'checks': checks}
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('\n'.join('PASS: ' + check for check in checks))


if __name__ == '__main__':
    main()
