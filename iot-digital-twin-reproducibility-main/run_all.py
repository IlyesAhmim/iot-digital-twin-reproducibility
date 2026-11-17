#!/usr/bin/env python3
"""Reproduce the three analyses without overwriting the published reference data."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results' / 'reproduced')
    args = parser.parse_args()
    output = args.output.resolve()
    reference = ROOT / 'results' / 'reference'
    if output == reference or reference in output.parents:
        parser.error('Choose an output directory outside results/reference.')
    output.mkdir(parents=True, exist_ok=True)
    logs = output / 'logs'
    logs.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['MPLBACKEND'] = 'Agg'
    env.setdefault('MPLCONFIGDIR', str(output / '.matplotlib'))
    environment = {
        'python': platform.python_version(),
        'platform': platform.platform(),
        'packages': {name: importlib.metadata.version(name) for name in
                     ('numpy', 'scipy', 'matplotlib', 'cbor2', 'cryptography')},
    }
    (output / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    for script in ('coap_timeliness.py', 'dt_sync_sim.py', 'cose_overhead.py'):
        print(f'Running {script} ...', flush=True)
        with (logs / f'{Path(script).stem}.log').open('w') as log:
            subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                           cwd=output, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        print((logs / f'{Path(script).stem}.log').read_text(), flush=True)
    subprocess.run([sys.executable, str(ROOT / 'verify_results.py'),
                    '--output', str(output)], check=True)
    print(f'Reproduction completed: {output}')


if __name__ == '__main__':
    main()
