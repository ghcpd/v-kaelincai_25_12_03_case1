#!/usr/bin/env python3
"""
Setup script for Logistics Routing v2 project.

Creates virtual environment, installs dependencies, and validates setup.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run shell command; exit on error."""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    print(f"  Command: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n❌ FAILED: {description}")
        sys.exit(1)
    
    print(f"✓ {description}")


def main():
    project_root = Path(__file__).parent
    venv_dir = project_root / ".venv"
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║         Logistics Routing v2 - Project Setup                        ║
╚══════════════════════════════════════════════════════════════════════╝

Project Root: {project_root}
Virtual Environment: {venv_dir}
    """)
    
    # Step 1: Create virtual environment
    if not venv_dir.exists():
        run_command(
            f"python -m venv {venv_dir}",
            "Creating Python virtual environment"
        )
    else:
        print(f"✓ Virtual environment already exists at {venv_dir}")
    
    # Step 2: Activate and upgrade pip
    if sys.platform == "win32":
        pip_cmd = str(venv_dir / "Scripts" / "pip")
    else:
        pip_cmd = str(venv_dir / "bin" / "pip")
    
    run_command(
        f"{pip_cmd} install --upgrade pip setuptools wheel",
        "Upgrading pip, setuptools, and wheel"
    )
    
    # Step 3: Install dependencies
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        run_command(
            f"{pip_cmd} install -r {requirements_file}",
            "Installing project dependencies"
        )
    else:
        print(f"⚠️  No requirements.txt found; skipping dependency installation")
    
    # Step 4: Validate installation
    print(f"\n{'='*70}")
    print("  Validating Setup")
    print(f"{'='*70}\n")
    
    if sys.platform == "win32":
        python_cmd = str(venv_dir / "Scripts" / "python")
    else:
        python_cmd = str(venv_dir / "bin" / "python")
    
    run_command(
        f"{python_cmd} --version",
        "Python version check"
    )
    
    run_command(
        f"{python_cmd} -c \"import pytest; print('pytest available')\"",
        "Pytest availability check"
    )
    
    # Step 5: Create necessary directories
    for directory in ["tests", "src", "data", "results"]:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        print(f"✓ Directory ready: {dir_path}")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                     Setup Complete! ✓                               ║
╚══════════════════════════════════════════════════════════════════════╝

Next steps:

1. Activate virtual environment:
   - Windows:  {venv_dir}\\Scripts\\activate
   - Unix:     source {venv_dir}/bin/activate

2. Run integration tests:
   python run_tests.sh

3. Build the project:
   python setup.py

For more information, see README.md
    """)


if __name__ == "__main__":
    main()
