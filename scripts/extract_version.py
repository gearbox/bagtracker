#!/usr/bin/env python3
"""
Extract version from pyproject.toml and create _version.py

Usage:
    python scripts/extract_version.py
"""

import tomllib
from pathlib import Path


def extract_version(pyproject_toml_path: str | None = None, version_placement_dir: str | None = None) -> None:
    pyproject_path = Path(pyproject_toml_path or "./pyproject.toml")
    version_dir_path = Path(version_placement_dir or "./backend")
    version_dir_path.mkdir(parents=True, exist_ok=True)
    version_file_path = "_version.py"
    version_full_path = version_dir_path / version_file_path

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    version = data["project"]["version"]

    version_full_path.write_text(f'"""Auto-generated version file"""\n\n__version__ = "{version}"\n')

    print(f"Extracted version: {version}")


if __name__ == "__main__":
    extract_version()
