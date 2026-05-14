#!/usr/bin/env python3
"""Create a QGIS plugin ZIP package for ROI Raster Histogram.

Run from repository root:

    python scripts/package_plugin.py

The generated ZIP is written to dist/ and should not be committed.
"""

from __future__ import annotations

import configparser
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
PLUGIN_FOLDER_NAME = "ROI_raster_histogram_QGIS"

INCLUDE_FILES = [
    "__init__.py",
    "metadata.txt",
    "roi_raster_histogram.py",
    "README.md",
    "LICENSE",
]


def read_version() -> str:
    metadata_path = REPO_ROOT / "metadata.txt"
    parser = configparser.ConfigParser()
    parser.read(metadata_path, encoding="utf-8")
    return parser.get("general", "version", fallback="0.0.0")


def validate_required_files() -> None:
    missing = [name for name in INCLUDE_FILES if not (REPO_ROOT / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Missing required plugin file(s): {joined}")


def create_package() -> Path:
    validate_required_files()
    version = read_version()
    DIST_DIR.mkdir(exist_ok=True)

    zip_path = DIST_DIR / f"ROI_Raster_Histogram_{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_name in INCLUDE_FILES:
            source = REPO_ROOT / file_name
            target = Path(PLUGIN_FOLDER_NAME) / file_name
            zf.write(source, target.as_posix())

    return zip_path


def main() -> None:
    if DIST_DIR.exists():
        # Keep this conservative: only remove generated ZIP files.
        for zip_file in DIST_DIR.glob("*.zip"):
            zip_file.unlink()
    package_path = create_package()
    size_kb = package_path.stat().st_size / 1024
    print(f"Created: {package_path}")
    print(f"Size: {size_kb:.1f} KB")
    print("Install in QGIS via Plugins > Manage and Install Plugins > Install from ZIP.")


if __name__ == "__main__":
    main()
