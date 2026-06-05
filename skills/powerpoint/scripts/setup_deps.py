#!/usr/bin/env python3
"""Install Python and Node packages for PowerPoint operations."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

CORE_PACKAGES = [
    ("python-pptx", "pptx"),
    ("Pillow", "PIL"),
    ("pyyaml", "yaml"),
]

OPTIONAL_PACKAGES = [
    ("markitdown[pptx]", "markitdown"),
]

SKILL_DIR = Path(__file__).resolve().parents[1]


def missing_packages(packages):
    missing = []
    for package_name, import_name in packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    return missing


def install(packages):
    if not packages:
        return 0

    print(f"Installing: {', '.join(packages)}")
    commands = [
        [sys.executable, "-m", "pip", "install", "--quiet"] + packages,
        [sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages"] + packages,
    ]

    last_error = ""
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print("Done.")
            return 0
        last_error = result.stderr.strip() or result.stdout.strip()

    print(f"Error: {last_error}")
    return 1


def node_dependencies_installed():
    check_script = SKILL_DIR / "scripts" / "check_pptxgenjs_env.js"
    if not check_script.exists():
        return False
    node_cmd = shutil.which("node")
    if node_cmd is None:
        return False
    result = subprocess.run(
        [node_cmd, str(check_script)],
        cwd=SKILL_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def install_node_dependencies():
    package_json = SKILL_DIR / "package.json"
    if not package_json.exists():
        print(f"Error: package.json not found at {package_json}")
        return 1
    node_cmd = shutil.which("node")
    npm_cmd = shutil.which("npm")
    if node_cmd is None:
        print("Error: Node.js is required for PptxGenJS deck generation, but node was not found on PATH.")
        return 1
    if npm_cmd is None:
        print("Error: npm is required for PptxGenJS deck generation, but npm was not found on PATH.")
        return 1
    if node_dependencies_installed():
        print("Node dependencies already installed.")
        return 0

    command = [npm_cmd, "install", "--silent"]
    print("Installing Node dependencies for PptxGenJS deck generation...")
    result = subprocess.run(command, cwd=SKILL_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip())
        return result.returncode
    print("Node dependencies installed.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Install PowerPoint skill dependencies")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Install optional dependencies such as MarkItDown and local Node packages",
    )
    parser.add_argument(
        "--node",
        action="store_true",
        help="Install local Node dependencies for PptxGenJS deck generation",
    )
    args = parser.parse_args()

    packages = list(CORE_PACKAGES)
    if args.full:
        packages.extend(OPTIONAL_PACKAGES)

    missing = missing_packages(packages)
    python_result = install(missing) if missing else 0
    if not missing:
        print("All requested Python dependencies already installed.")
    if python_result != 0:
        return python_result

    if args.full or args.node:
        return install_node_dependencies()

    return 0


if __name__ == "__main__":
    sys.exit(main())
