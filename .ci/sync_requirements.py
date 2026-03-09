#!/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

import sys
import tomllib
from pathlib import Path


def main(fix: bool) -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    dependencies = data["project"]["dependencies"]

    requirements = Path("requirements.txt").read_text().strip().split("\n")
    if requirements != dependencies:
        if fix:
            print("Updating 'requirements.txt'.")
            Path("requirements.txt").write_text("\n".join(dependencies) + "\n")
        else:
            print("'requirements.txt' is outdated!")
            exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        fix: bool = False
    elif len(sys.argv) == 2 and sys.argv[1] == "--fix":
        fix = True
    else:
        print(f"Usage: {sys.argv[0]} [--fix]")
        exit(1)
    main(fix)
