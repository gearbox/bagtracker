#!/usr/bin/env python3
"""
Verify Uvicorn configuration is correct
Usage: python scripts/verify_uvicorn_config.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_config():
    """Verify the Uvicorn configuration"""
    try:
        from uvicorn_config import config

        print("=" * 60)
        print("Uvicorn Configuration Verification")
        print("=" * 60)

        # Check required fields
        required = ["app", "host", "port", "workers"]
        if missing := [field for field in required if field not in config]:
            print(f"❌ Missing required fields: {missing}")
            return False

        # Display configuration
        print("\n✅ Configuration loaded successfully\n")
        print(f"{'Field':<25} {'Value':<35}")
        print("-" * 60)

        for key, value in sorted(config.items()):
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 32:
                value_str = f"{value_str[:29]}..."
            print(f"{key:<25} {value_str:<35}")

        # Validate values
        print("\n" + "=" * 60)
        print("Validation Checks")
        print("=" * 60)

        checks = []

        # Check workers
        if config["workers"] < 1:
            checks.append(("❌", "Workers", f"Must be >= 1, got {config['workers']}"))
        elif config["workers"] > 32:
            checks.append(("⚠️ ", "Workers", f"High worker count: {config['workers']} (may use too much memory)"))
        else:
            checks.append(("✅", "Workers", f"Valid: {config['workers']}"))

        # Check port
        if not (1 <= config["port"] <= 65535):
            checks.append(("❌", "Port", f"Invalid port: {config['port']}"))
        else:
            checks.append(("✅", "Port", f"Valid: {config['port']}"))

        # Check host
        if config["host"] in ["0.0.0.0", "127.0.0.1", "localhost"]:
            checks.append(("✅", "Host", f"Valid: {config['host']}"))
        else:
            checks.append(("⚠️ ", "Host", f"Unusual host: {config['host']}"))

        # Check app path
        if "backend.asgi:app" in config["app"]:
            checks.append(("✅", "App", "Valid application path"))
        else:
            checks.append(("⚠️ ", "App", f"Unusual app path: {config['app']}"))

        # Check timeout
        timeout = config.get("timeout_keep_alive", 0)
        if timeout < 60:
            checks.append(("⚠️ ", "Timeout", f"Low timeout: {timeout}s (may drop long requests)"))
        else:
            checks.append(("✅", "Timeout", f"Valid: {timeout}s"))

        # Print checks
        for status, name, message in checks:
            print(f"{status} {name:<15} {message}")

        # Memory estimation
        print("\n" + "=" * 60)
        print("Resource Estimation")
        print("=" * 60)
        memory_per_worker = 45  # MB (approximate)
        total_memory = config["workers"] * memory_per_worker
        print(f"Estimated memory usage: ~{total_memory}MB ({config['workers']} workers × ~{memory_per_worker}MB)")

        if total_memory > 2048:
            print("⚠️  High memory usage - ensure your system has enough RAM")

        # Summary
        print("\n" + "=" * 60)
        errors = [c for c in checks if c[0] == "❌"]
        warnings = [c for c in checks if c[0] == "⚠️ "]

        if errors:
            print(f"❌ Configuration has {len(errors)} error(s)")
            return False
        elif warnings:
            print(f"✅ Configuration valid with {len(warnings)} warning(s)")
            return True
        else:
            print("✅ Configuration is valid - ready for production!")
            return True

    except ImportError as e:
        print(f"❌ Failed to import configuration: {e}")
        print("Make sure uvicorn_config.py is in the project root")
        return False
    except Exception as e:
        print(f"❌ Error verifying configuration: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)
