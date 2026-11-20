import argparse
import sys
import subprocess
import time
from pathlib import Path

import os
import shutil

def find_tectonic_bin() -> str:
    if os.environ.get("TECTONIC_BIN") and os.path.isfile(os.environ["TECTONIC_BIN"]):
        return os.environ["TECTONIC_BIN"]
    which_bin = shutil.which("tectonic")
    if which_bin:
        return which_bin
    home = Path.home()
    cand1 = home / ".gemini" / "antigravity" / "tools" / "tectonic" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    if cand1.exists():
        return str(cand1)
    cand2 = home / ".local" / "bin" / "tectonic"
    if cand2.exists():
        return str(cand2)
    return "tectonic"

TECTONIC_BIN = find_tectonic_bin()

def get_projects_root() -> Path:
    if os.environ.get("LATEX_STUDIO_PROJECTS_DIR"):
        p = Path(os.environ["LATEX_STUDIO_PROJECTS_DIR"])
        p.mkdir(parents=True, exist_ok=True)
        return p
    cwd = Path.cwd()
    if (cwd / "projects").exists():
        return cwd / "projects"
    cand = cwd / "projects"
    cand.mkdir(parents=True, exist_ok=True)
    return cand

PROJECTS_ROOT = get_projects_root()

def compile_project(project_name: str):
    p_dir = PROJECTS_ROOT / project_name
    if not p_dir.exists():
        print(f"Error: Project '{project_name}' not found at {p_dir}")
        sys.exit(1)

    tex_file = p_dir / "main.tex"
    if not tex_file.exists():
        print(f"Error: main.tex not found in {p_dir}")
        sys.exit(1)

    print(f"Compiling {tex_file.name} using Tectonic XeTeX...")
    t0 = time.time()
    cmd = [TECTONIC_BIN, str(tex_file), "--outdir", str(p_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = round(time.time() - t0, 2)

    pdf_file = p_dir / "main.pdf"
    if proc.returncode == 0 and pdf_file.exists():
        print(f"✓ Compilation successful in {dt}s!")
        print(f"Output: {pdf_file} ({pdf_file.stat().st_size} bytes)")
    else:
        print(f"✗ Compilation failed in {dt}s:")
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile a LaTeX project with Tectonic XeTeX")
    parser.add_argument("--project", "-p", required=True, help="Project name or slug")
    args = parser.parse_args()
    compile_project(args.project)
