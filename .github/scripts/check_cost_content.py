"""Fail if cost correlations or plant cost index tables are committed to the repository.

ExerPy ships neither: users supply their own purchase equipment cost functions or use OpenPyTEA.
Scans the tracked files, or every file below a directory given as argument.
"""

import re
import subprocess
import sys
from pathlib import Path

INDEX_NAME = "ce" + "pci"  # the commercial index is not named anywhere else in the code

BLOCKED_PATH = re.compile(r"(^|/)(cost_estimation|cost_correlations|cost_library)(/|$)")
BLOCKED_TEXT = re.compile(
    rf"{INDEX_NAME}|TurtonCostEstimator|\b(?:_COMP_COST|_MOTOR_COST|_PHX_COST|_DEFAULT_CI_RATIOS|PEC_W)\b",
    re.IGNORECASE,
)
# A power law with literal coefficients, e.g. "PEC = 15526 * (A / 42) ** 0.8".
POWER_LAW = re.compile(r"\bPEC\w*\s*=\s*[\d_.]+\s*\*.*\*\*\s*\(?\s*\d*\.\d+", re.IGNORECASE)
# Index values of a year, e.g. "2013: 567.3"; two or more in one file make a table.
YEAR_VALUE = re.compile(r"""["']?\b(?:19[5-9]\d|20\d\d)\b["']?\s*:\s*(\d{3,4}(?:\.\d+)?)\b""")
INDEX_RANGE = (300.0, 3000.0)
# Reads the index of OpenPyTEA at runtime by its attribute name and holds no values itself.
EXTERNAL_INDEX_READERS = {"src/exerpy/costing.py"}


def files_to_scan(root):
    if len(sys.argv) > 1:
        return [p for p in Path(sys.argv[1]).rglob("*") if p.is_file() and ".git" not in p.parts]
    names = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    return [root / name for name in names.decode().split("\0") if name]


def scan(path, label):
    findings = []
    if BLOCKED_PATH.search(label):
        findings.append(f"{label}: path of a cost correlation module")
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return findings
    index_lines = []
    for number, line in enumerate(data.decode("utf-8", errors="ignore").splitlines(), start=1):
        if BLOCKED_TEXT.search(line) and label not in EXTERNAL_INDEX_READERS:
            findings.append(f"{label}:{number}: cost correlation or cost index name")
        if POWER_LAW.search(line):
            findings.append(f"{label}:{number}: cost correlation with literal coefficients")
        values = [float(v) for v in YEAR_VALUE.findall(line)]
        index_lines += [number] * sum(INDEX_RANGE[0] <= v <= INDEX_RANGE[1] for v in values)
    if len(index_lines) >= 2:
        findings.append(f"{label}:{index_lines[0]}: table of cost index values by year")
    return findings


def main():
    root = Path(__file__).resolve().parents[2]
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else root
    findings = []
    for path in files_to_scan(root):
        if path.resolve() == Path(__file__).resolve():
            continue
        findings += scan(path, path.relative_to(base).as_posix())
    if findings:
        print("Cost correlations or cost index tables must not be part of ExerPy:")
        print("\n".join(f"  {finding}" for finding in findings))
        return 1
    print("No cost correlations or cost index tables found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
