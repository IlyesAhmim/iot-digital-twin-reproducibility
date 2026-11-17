"""Check packaged file hashes and parse Python sources; do not execute simulations."""
from pathlib import Path
import ast, hashlib
root = Path(__file__).resolve().parent
checked = 0
for line in (root / "SHA256SUMS.txt").read_text().splitlines():
    expected, name = line.split("  ", 1)
    path = root / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"HASH MISMATCH: {name}")
    checked += 1
for path in root.rglob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
print(f"PASS: {checked} hashes; Python syntax parsed. No simulation executed.")
