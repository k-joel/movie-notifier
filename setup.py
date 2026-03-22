#!/usr/bin/env python3
"""
Setup script for Movie Notifier
"""

import os
import sys
import subprocess


def main():
    # Print header
    print()
    print("=" * 60)
    print(" MOVIE NOTIFIER SETUP")
    print("=" * 60)

    print()
    print("This script will help you set up the Movie Notifier application.")

    # Check Python version
    print()
    print("[1] Checking Python version...")
    if sys.version_info < (3, 7):
        print(f"  ERROR: Python 3.7+ required. Current: {sys.version}")
        return False
    else:
        print(
            f"  OK: Python {sys.version_info.major}.{sys.version_info.minor} detected")

    # Install dependencies
    print()
    print("[2] Installing dependencies...")
    requirements_file = "requirements.txt"
    if os.path.exists(requirements_file):
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file])
            print("  OK: Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"  WARNING: Failed to install dependencies: {e}")
            print("  You can try manually: pip install -r requirements.txt")
            # Continue setup even if dependencies fail (like install.bat)
    else:
        print(f"  ERROR: Requirements file not found: {requirements_file}")
        return False

    # Create directories
    print()
    print("[3] Creating directories...")
    directories = ["config", "data", "logs", "scripts"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"  OK: Created directory: {directory}")
        else:
            print(f"  OK: Directory already exists: {directory}")

    # Check if config file exists
    print()
    print("[4] Checking configuration...")
    config_file = "config/config.yaml"
    config_example = "config/config.yaml.example"
    if os.path.exists(config_file):
        print(f"  OK: Configuration file already exists: {config_file}")
    else:
        print(f"  WARNING: Configuration file not found: {config_file}")
        if os.path.exists(config_example):
            print(f"  You can copy {config_example} to {config_file}")
            print("  and update it with your API keys and email settings.")
        else:
            print(
                "  Please create config/config.yaml with your API keys and email settings.")

    # Check scripts
    print()
    print("[5] Checking scripts...")
    scripts_dir = "scripts"
    required_scripts = ["tmdb_client.py", "config_manager.py",
                        "email_notifier.py", "movie_notifier.py"]

    if os.path.exists(scripts_dir):
        missing = []
        for script in required_scripts:
            if not os.path.exists(os.path.join(scripts_dir, script)):
                missing.append(script)

        if missing:
            print(f"  ERROR: Missing scripts: {', '.join(missing)}")
            return False
        else:
            print(f"  OK: All required scripts found in {scripts_dir}")
    else:
        print(f"  ERROR: Scripts directory not found: {scripts_dir}")
        return False

    # Success message
    print()
    print("=" * 60)
    print(" SETUP COMPLETE")
    print("=" * 60)

    # Next steps
    print()
    print("NEXT STEPS:")
    print()
    print("1. Get a TMDB API Key:")
    print("   - Visit: https://www.themoviedb.org/settings/api")
    print("   - Create an account if needed")
    print("   - Request an API key")
    print()
    print("2. Configure Email Settings:")
    print("   - For Gmail, create an App Password:")
    print("     https://myaccount.google.com/apppasswords")
    print("   - Use this password in the config file")
    print()
    print("3. Edit Configuration File:")
    print("   - Open: config/config.yaml")
    print("   - Update TMDB API key")
    print("   - Update email settings")
    print("   - Add/remove actors/directors as needed")
    print()
    print("4. Test the Setup:")
    print("   - Run: python scripts/movie_notifier.py --test")
    print()
    print("5. Run Once to Test:")
    print("   - Run: python scripts/movie_notifier.py --once")
    print()
    print("6. Set Up Scheduled Runs:")
    print("   - Use the cron job feature in AionUI")
    print("   - Or run: python scripts/movie_notifier.py --schedule")
    print()
    print("Available Commands:")
    print("  python scripts/movie_notifier.py --help")
    print("  python scripts/movie_notifier.py --test")
    print("  python scripts/movie_notifier.py --once")
    print("  python scripts/movie_notifier.py --schedule")

    return True


if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print()
            print("ERROR: Setup failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"Unexpected error: {e}")
        sys.exit(1)
