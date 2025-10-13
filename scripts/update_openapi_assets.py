#!/usr/bin/env python3
"""
Update OpenAPI/Swagger UI static assets from official CDN sources.

Usage:
    # Update to latest versions
    python scripts/update_openapi_assets.py
    # or
    # Update to specific versions
    python scripts/update_openapi_assets.py --version 5.10.0
    python scripts/update_openapi_assets.py --swagger-version 5.10.0 --redoc-version 2.1.0
    # or
    # Skip favicon download
    python scripts/update_openapi_assets.py --skip-favicon
    # or
    # View help
    python scripts/update_openapi_assets.py --help
"""

import argparse
import sys
from pathlib import Path

import requests

# Configuration
STATIC_DIR = Path("static/openapi")
TIMEOUT = 30  # seconds

# Asset URLs from official CDNs
ASSETS = {
    "swagger-ui-bundle.js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui-bundle.js",
    "swagger-ui.css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@{version}/swagger-ui.css",
    "redoc.standalone.js": "https://cdn.jsdelivr.net/npm/redoc@{version}/bundles/redoc.standalone.js",
    "favicon.png": "https://fastapi.tiangolo.com/img/favicon.png",
}


def download_file(url: str, destination: Path) -> bool:
    """
    Download a file from URL to destination path.

    Args:
        url: Source URL
        destination: Destination file path

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"📥 Downloading {destination.name}...")
        print(f"   Source: {url}")

        response = requests.get(url, timeout=TIMEOUT, stream=True)
        response.raise_for_status()

        # Get file size if available
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Show progress for large files
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"   Progress: {progress:.1f}%", end="\r")

        file_size = destination.stat().st_size
        print(f"   ✅ Downloaded {destination.name} ({file_size:,} bytes)")
        return True

    except requests.RequestException as e:
        print(f"   ❌ Failed to download {destination.name}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error saving {destination.name}: {e}")
        return False


def get_latest_version(package: str) -> str | None:
    """
    Get the latest version of a npm package.

    Args:
        package: Package name (e.g., 'swagger-ui-dist')

    Returns:
        Version string or None if failed
    """
    try:
        url = f"https://registry.npmjs.org/{package}/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("version")
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Update OpenAPI/Swagger UI static assets")
    parser.add_argument(
        "--swagger-version",
        default="latest",
        help="Swagger UI version (default: latest)",
    )
    parser.add_argument(
        "--redoc-version",
        default="latest",
        help="ReDoc version (default: latest)",
    )
    parser.add_argument(
        "--skip-favicon",
        action="store_true",
        help="Skip downloading favicon",
    )

    args = parser.parse_args()

    print("🔄 OpenAPI Assets Updater")
    print("=" * 60)

    # Get version info if using 'latest'
    swagger_version = args.swagger_version
    if swagger_version == "latest":
        print("🔍 Fetching latest Swagger UI version...")
        swagger_version = get_latest_version("swagger-ui-dist")
        if swagger_version:
            print(f"   Latest Swagger UI: v{swagger_version}")
        else:
            print("   ⚠️  Could not fetch version, using 'latest' tag")
            swagger_version = "latest"

    redoc_version = args.redoc_version
    if redoc_version == "latest":
        print("🔍 Fetching latest ReDoc version...")
        redoc_version = get_latest_version("redoc")
        if redoc_version:
            print(f"   Latest ReDoc: v{redoc_version}")
        else:
            print("   ⚠️  Could not fetch version, using 'latest' tag")
            redoc_version = "latest"

    print()

    # Create static directory if it doesn't exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Target directory: {STATIC_DIR.absolute()}")
    print()

    # Download files
    success_count = 0
    total_count = 0

    for filename, url_template in ASSETS.items():
        if args.skip_favicon and filename == "favicon.png":
            print(f"⏭️  Skipping {filename}")
            continue

        total_count += 1
        destination = STATIC_DIR / filename

        # Determine version based on file type
        if "swagger" in filename:
            url = url_template.format(version=swagger_version)
        elif "redoc" in filename:
            url = url_template.format(version=redoc_version)
        else:
            url = url_template  # No version needed (favicon)

        if download_file(url, destination):
            success_count += 1

        print()

    # Summary
    print("=" * 60)
    if success_count == total_count:
        print(f"✅ Success! All {total_count} files downloaded successfully.")
        return 0
    else:
        print(f"⚠️  Downloaded {success_count}/{total_count} files.")
        print(f"   {total_count - success_count} files failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
