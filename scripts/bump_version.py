#!/usr/bin/env python3

import json
import re
import sys
import tomllib
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def semver_tuple(version: str, source: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(version)
    if not m:
        sys.exit(f"error: invalid semver '{version}' in {source}")
    return [int(g) for g in m.groups()]


def extract_version(path: Path) -> str:
    if path.name == "package.json":
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            sys.exit(f"error reading {path}: {e}")
        version = data.get("version")
        if version is None:
            sys.exit(f"error: no version field in {path}")
        return version
    elif path.name == "pyproject.toml":
        try:
            data = tomllib.loads(path.read_text())
        except Exception as e:
            sys.exit(f"error reading {path}: {e}")
        version = data.get("project", {}).get("version")
        if version is None:
            sys.exit(f"error: no [project].version in {path}")
        return version
    else:
        sys.exit(f"error: unrecognised file type: {path}")


def write_version(path: Path, new: str) -> None:
    if path.name == "package.json":
        data = json.loads(path.read_text())
        data["version"] = new
        path.write_text(json.dumps(data, indent=2) + "\n")
    elif path.name == "pyproject.toml":
        lines = path.read_text().splitlines(keepends=True)
        in_project = False
        out = []
        bumped = False
        for line in lines:
            if re.match(r"^\[project\]", line):
                in_project = True
            elif re.match(r"^\[", line):
                in_project = False
            if in_project and re.match(r"^version\s*=", line):
                line = re.sub(r'"[^"]*"', f'"{new}"', line, count=1)
                in_project = False  # redundant
                bumped = True
            out.append(line)
            if bumped:
                break
        if not bumped:
            sys.exit(f"Version number not found in {path}")
        path.write_text("".join(out))


def main():
    if len(sys.argv) < 2:
        sys.exit("error: no files provided")

    entries: list[tuple[Path, tuple[int, int, int]]] = []

    for arg in sys.argv[1:]:
        path = Path(arg)
        version = extract_version(path)
        print(f"{path}: {version}", file=sys.stderr)
        entries.append((path, semver_tuple(version, str(path))))

    major, minor, patch = max(t for _, t in entries)
    new_version = f"{major}.{minor}.{patch + 1}"

    for path, _ in entries:
        write_version(path, new_version)
        print(f"{path}: -> {new_version}", file=sys.stderr)

    print(new_version)


if __name__ == "__main__":
    main()
