#!/usr/bin/env python3

import subprocess
import re


def main() -> None:
    matches = [
        re.match(r"^v(\d+)\.(\d+)\.(\d+)$", t)
        for t in subprocess.check_output(["git", "tag"]).decode().splitlines()
    ]
    semvers = [tuple(int(g) for g in m.groups()) for m in matches if m]
    if not semvers:
        return
    major, minor, patch = max(semvers)
    print(f"v{major}.{minor}.{patch}")


if __name__ == "__main__":
    main()
