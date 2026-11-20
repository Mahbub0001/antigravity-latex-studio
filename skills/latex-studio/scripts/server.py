import os
import sys
import time
import base64
import io
import shutil
import zipfile
import subprocess
import threading
import winreg
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import pypdfium2 as pdfium
import uvicorn

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
    cand = cwd / "projects"
    cand.mkdir(parents=True, exist_ok=True)
    return cand

PROJECTS_ROOT = get_projects_root()

def get_downloads_folders() -> List[Path]:
    """Finds the user's actual Downloads folder dynamically without hardcoded paths."""
    folders = []
    if os.name == "nt":
        try:
            import winreg
            sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                val, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                p = Path(os.path.expandvars(val))
                if p.exists() and p not in folders:
                    folders.append(p)
        except Exception:
            pass
    dl = Path.home() / "Downloads"
    if dl.exists() and dl not in folders:
        folders.append(dl)
    if not folders:
        dl.mkdir(parents=True, exist_ok=True)
        folders.append(dl)
    return folders

DOWNLOADS_DIRS = get_downloads_folders()
PRIMARY_DOWNLOADS_DIR = DOWNLOADS_DIRS[0]

# Watchdog state
last_heartbeat_time = time.time()
disconnect_time: Optional[float] = None
is_shutting_down = False
INITIAL_GRACE_PERIOD = 600  # 10 minutes initial grace period to allow opening UI
INACTIVITY_TIMEOUT = 300    # 5 minutes of no heartbeats before shutdown
DISCONNECT_BUFFER = 60      # 60 seconds buffer after client disconnect before shutdown

def inactivity_watchdog():
    """Shuts down server automatically if client stops sending heartbeats (e.g. Studio closed)."""
    global is_shutting_down, last_heartbeat_time, disconnect_time
    start_time = time.time()
    while not is_shutting_down:
        time.sleep(2)
        # Check if still in initial grace period
        if (time.time() - start_time) < INITIAL_GRACE_PERIOD:
            continue
        
        now = time.time()
        # If client explicitly disconnected (e.g. closed tab), wait buffer for potential reload
        if disconnect_time is not None:
            if (now - disconnect_time) > DISCONNECT_BUFFER:
                print(f"[Watchdog] Studio tab closed. Disconnect buffer ({DISCONNECT_BUFFER}s) expired. Shutting down server gracefully.")
                is_shutting_down = True
                os._exit(0)
        else:
            elapsed = now - last_heartbeat_time
            if elapsed > INACTIVITY_TIMEOUT:
                print(f"[Watchdog] Inactivity detected ({round(elapsed)}s since last heartbeat). Shutting down server gracefully.")
                is_shutting_down = True
                os._exit(0)

def start_inactivity_watchdog():
    """Starts inactivity watchdog only when standalone server is run."""
    t = threading.Thread(target=inactivity_watchdog, daemon=True)
    t.start()

app = FastAPI(title="Antigravity LaTeX Studio Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

TEMPLATES = {
    "ieee": r"""\documentclass[10pt,journal,compsoc]{IEEEtran}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{booktabs}

\title{Your Research Paper Title Goes Here}
\author{First Author \and Second Author}

\begin{document}
\maketitle

\begin{abstract}
Write a concise summary of your research methodology, findings, and contributions here.
\end{abstract}

\section{Introduction}
Introduction text with mathematical formulation:
\begin{equation}
E = mc^2
\end{equation}

\section{Methodology}
Detail your experimental setup and algorithms.

\bibliographystyle{plain}
\bibliography{references}

\end{document}
""",
    "report": r"""\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{a4paper, margin=1in}

\title{Academic Project Report}
\author{Your Name}
\date{\today}

\begin{document}
\maketitle

\begin{abstract}
Abstract for the academic project report goes here.
\end{abstract}

\section{Introduction}
Introduce the problem statement and background.

\section{Theoretical Background}
Formulation and analysis:
\begin{equation}
f(x) = \int_{-\infty}^{\infty} e^{-t^2} \, \mathrm{d}t = \sqrt{\pi}
\end{equation}

\section{Conclusion}
Summary of outcomes and future directions.

\bibliographystyle{plain}
\bibliography{references}

\end{document}
""",
    "blank": r"""\documentclass[11pt]{article}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}

\title{Untitled Document}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

Start writing your document here...

\end{document}
"""
}

class CompileRequest(BaseModel):
    project_id: str
    code: str
    filename: str = "main.tex"

class CreateProjectRequest(BaseModel):
    name: str
    template: str = "ieee"

class RenameProjectRequest(BaseModel):
    new_name: str

class OpenExplorerRequest(BaseModel):
    file_type: str = "zip"
    project_id: str

def render_pdf_pages_b64(pdf_path: Path) -> List[str]:
    if not pdf_path.exists():
        return []
    pdf = None
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        pages_b64 = []
        for page in pdf:
            img = page.render(scale=2).to_pil()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
        return pages_b64
    except Exception as e:
        print(f"Error rendering PDF: {e}")
        return []
    finally:
        if pdf is not None:
            try:
                pdf.close()
            except Exception:
                pass

def generate_overleaf_zip_bytes(p_dir: Path) -> bytes:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(p_dir):
            for file in files:
                if file.endswith(('.aux', '.log', '.out', '.xdv', '.fls', '.fdb_latexmk', '.bbl', '.blg')):
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(p_dir)
                zf.write(file_path, arcname=rel_path.as_posix())
    zip_buf.seek(0)
    return zip_buf.getvalue()

@app.get("/", response_class=HTMLResponse)
def index():
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    html_file = Path(__file__).parent / "latex_studio.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>LaTeX Studio</h1><p>UI file not found. Run build_ui.py</p>"

@app.get("/api/health")
def health():
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    return {
        "status": "ok",
        "engine": "Tectonic 0.17",
        "projects_dir": str(PROJECTS_ROOT),
        "downloads_dir": str(PRIMARY_DOWNLOADS_DIR)
    }

@app.post("/api/heartbeat")
def heartbeat():
    global last_heartbeat_time, disconnect_time
    last_heartbeat_time = time.time()
    disconnect_time = None  # Reset disconnect countdown
    return {"status": "alive", "timestamp": last_heartbeat_time}

@app.post("/api/client-disconnect")
def client_disconnect():
    global disconnect_time
    if disconnect_time is None:
        disconnect_time = time.time()
        print(f"[Client] Disconnect reported by UI. Buffer countdown started ({DISCONNECT_BUFFER}s).")
    return {"status": "disconnect_acknowledged", "buffer_seconds": DISCONNECT_BUFFER}

@app.post("/api/shutdown")
def shutdown():
    global is_shutting_down
    is_shutting_down = True
    print("[Shutdown] Explicit shutdown requested by client.")
    def do_exit():
        time.sleep(0.3)
        os._exit(0)
    threading.Thread(target=do_exit).start()
    return {"status": "shutting_down"}

@app.get("/api/projects")
def list_projects():
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    projects = []
    import datetime
    import json
    import re
    for p in PROJECTS_ROOT.iterdir():
        if p.is_dir():
            tex_file = p / "main.tex"
            pdf_file = p / "main.pdf"
            meta_file = p / "metadata.json"
            
            # Custom title
            title = p.name.replace("_", " ").title()
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as mf:
                        mdata = json.load(mf)
                        if "title" in mdata and mdata["title"]:
                            title = mdata["title"]
                except Exception:
                    pass
            
            # Document class detection
            doc_class = "article"
            tex_preview = ""
            if tex_file.exists():
                try:
                    with open(tex_file, "r", encoding="utf-8", errors="ignore") as f:
                        tex_content = f.read(1500)
                        tex_preview = tex_content[:200]
                        m = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", tex_content)
                        if m:
                            doc_class = m.group(1).strip()
                except Exception:
                    pass
            
            # Page count
            page_count = 0
            if pdf_file.exists():
                try:
                    doc = pdfium.PdfDocument(str(pdf_file))
                    page_count = len(doc)
                    doc.close()
                except Exception:
                    page_count = 1
            
            mtime = p.stat().st_mtime
            updated_at_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y %I:%M %p")
            
            projects.append({
                "id": p.name,
                "name": title,
                "slug": p.name,
                "has_pdf": pdf_file.exists(),
                "page_count": page_count,
                "doc_class": doc_class,
                "updated_at": mtime,
                "updated_at_str": updated_at_str,
                "preview": tex_preview
            })
    projects.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"projects": projects, "downloads_dir": str(PRIMARY_DOWNLOADS_DIR)}

@app.post("/api/projects/{project_id}/rename")
def rename_project(project_id: str, req: RenameProjectRequest):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    import json
    
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_title = req.new_name.strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="New project name cannot be empty")
    
    new_slug = new_title.lower().replace(" ", "_").replace("-", "_")
    new_slug = "".join(c for c in new_slug if c.isalnum() or c == "_")
    if not new_slug:
        new_slug = project_id

    final_id = project_id
    final_dir = p_dir
    if new_slug != project_id:
        cand_dir = PROJECTS_ROOT / new_slug
        if not cand_dir.exists():
            try:
                p_dir.rename(cand_dir)
                final_id = new_slug
                final_dir = cand_dir
            except Exception as e:
                print(f"[Rename] Folder rename skipped ({e}), metadata updated.")

    meta_file = final_dir / "metadata.json"
    meta_data = {}
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as mf:
                meta_data = json.load(mf)
        except Exception:
            pass
    meta_data["title"] = new_title
    meta_data["updated_at"] = time.time()
    try:
        with open(meta_file, "w", encoding="utf-8") as mf:
            json.dump(meta_data, mf, indent=2)
    except Exception as e:
        print(f"[Rename] Could not write metadata.json: {e}")

    return {"success": True, "id": final_id, "name": new_title}

def handle_remove_readonly(func, path, exc):
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

@app.post("/api/projects/{project_id}/delete")
def delete_project(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    import gc
    import stat
    
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 1. Force python garbage collection to release any internal file handles
    gc.collect()
    
    # 2. Try removing with retry and onerror handler for read-only files
    deleted = False
    last_err = None
    for attempt in range(4):
        try:
            for root, dirs, files in os.walk(p_dir):
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    except Exception:
                        pass
            shutil.rmtree(str(p_dir), onerror=handle_remove_readonly)
            deleted = True
            break
        except Exception as e:
            last_err = e
            gc.collect()
            time.sleep(0.15)
            
    # 3. If Windows file lock still persists, move to .trash folder
    if not deleted and p_dir.exists():
        try:
            trash_dir = PROJECTS_ROOT / ".trash"
            trash_dir.mkdir(exist_ok=True)
            trash_target = trash_dir / f"{project_id}_{int(time.time())}"
            shutil.move(str(p_dir), str(trash_target))
            deleted = True
            def cleanup_trash():
                time.sleep(2)
                try:
                    shutil.rmtree(str(trash_target), ignore_errors=True)
                except Exception:
                    pass
            threading.Thread(target=cleanup_trash, daemon=True).start()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete project: {last_err or e}")
        
    return {"success": True, "deleted": project_id}

@app.post("/api/projects/{project_id}/duplicate")
def duplicate_project(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    import json
    
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    copy_slug = f"{project_id}_copy"
    target = PROJECTS_ROOT / copy_slug
    idx = 1
    while target.exists():
        copy_slug = f"{project_id}_copy_{idx}"
        target = PROJECTS_ROOT / copy_slug
        idx += 1
    
    try:
        shutil.copytree(str(p_dir), str(target))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate project: {e}")
    
    title = f"{project_id.replace('_', ' ').title()} (Copy)"
    meta_file = target / "metadata.json"
    try:
        with open(meta_file, "w", encoding="utf-8") as mf:
            json.dump({"title": title, "updated_at": time.time()}, mf, indent=2)
    except Exception:
        pass
        
    return {"success": True, "id": copy_slug, "name": title}

@app.post("/api/projects/new")
def create_project(req: CreateProjectRequest):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    
    slug = req.name.lower().strip().replace(" ", "_").replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    if not slug:
        slug = f"project_{int(time.time())}"
    
    p_dir = PROJECTS_ROOT / slug
    if p_dir.exists():
        slug = f"{slug}_{int(time.time()) % 1000}"
        p_dir = PROJECTS_ROOT / slug
    
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "figures").mkdir(exist_ok=True)
    
    template_code = TEMPLATES.get(req.template, TEMPLATES["blank"])
    tex_path = p_dir / "main.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(template_code)
    
    bib_path = p_dir / "references.bib"
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(r"""@article{sample2026,
  title={Advanced Machine Learning Methods},
  author={Author, Example and Coauthor, Another},
  journal={Journal of AI Research},
  volume={1},
  pages={1--10},
  year={2026}
}
""")

    cmd = [TECTONIC_BIN, "-C", str(tex_path), "--outdir", str(p_dir)]
    subprocess.run(cmd, capture_output=True, text=True)
    return {"id": slug, "name": req.name, "created": True}

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    tex_path = p_dir / "main.tex"
    code = ""
    if tex_path.exists():
        with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    
    bib_path = p_dir / "references.bib"
    bib_code = ""
    if bib_path.exists():
        with open(bib_path, "r", encoding="utf-8", errors="ignore") as f:
            bib_code = f.read()

    pdf_path = p_dir / "main.pdf"
    pdf_base64 = ""
    page_count = 0
    if pdf_path.exists():
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            doc = pdfium.PdfDocument(pdf_bytes)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1
    
    figures = []
    fig_dir = p_dir / "figures"
    if fig_dir.exists():
        figures = [f.name for f in fig_dir.iterdir() if f.is_file()]

    return {
        "id": project_id,
        "name": project_id.replace("_", " ").title(),
        "code": code,
        "bib_code": bib_code,
        "pdf_base64": pdf_base64,
        "figures": figures,
        "page_count": page_count,
        "downloads_dir": str(PRIMARY_DOWNLOADS_DIR)
    }

@app.post("/api/compile")
def compile_project(req: CompileRequest):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    
    p_dir = PROJECTS_ROOT / req.project_id
    if not p_dir.exists():
        p_dir.mkdir(parents=True, exist_ok=True)
        (p_dir / "figures").mkdir(exist_ok=True)
    
    target_path = p_dir / req.filename
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(req.code)
    
    main_tex = p_dir / "main.tex"
    t0 = time.time()
    cmd = [TECTONIC_BIN, "-C", str(main_tex), "--outdir", str(p_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    compile_time = round(time.time() - t0, 2)
    
    pdf_path = p_dir / "main.pdf"
    if proc.returncode == 0 and pdf_path.exists():
        pdf_base64 = ""
        page_count = 1
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            doc = pdfium.PdfDocument(pdf_bytes)
            page_count = len(doc)
            doc.close()
        except Exception:
            pass
        return {
            "success": True,
            "compile_time": compile_time,
            "page_count": page_count,
            "pdf_base64": pdf_base64,
            "stdout": proc.stdout
        }
    else:
        error_text = (proc.stderr or "") + "\n" + (proc.stdout or "")
        error_lines = [l for l in error_text.splitlines() if "error:" in l.lower() or "fatal" in l.lower() or "!" in l]
        if not error_lines:
            error_lines = error_text.splitlines()[-10:]
        return {
            "success": False,
            "compile_time": compile_time,
            "error": "\n".join(error_lines),
            "stdout": proc.stdout
        }

# Browser-native download endpoints
@app.get("/api/projects/{project_id}/download/pdf")
def download_pdf_stream(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    p_dir = PROJECTS_ROOT / project_id
    pdf_path = p_dir / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not compiled yet")
    return FileResponse(
        path=str(pdf_path),
        filename=f"{project_id}.pdf",
        media_type="application/pdf"
    )

@app.get("/api/projects/{project_id}/download/zip")
def download_zip_stream(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    zip_bytes = generate_overleaf_zip_bytes(p_dir)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_id}_overleaf.zip"'}
    )

@app.post("/api/projects/{project_id}/export-downloads")
def export_to_downloads(project_id: str):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    
    p_dir = PROJECTS_ROOT / project_id
    if not p_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    pdf_src = p_dir / "main.pdf"
    zip_bytes = generate_overleaf_zip_bytes(p_dir)

    saved_locations = []
    # Save to all detected download folders (D:\DOWNLOADS, etc.)
    for target_dir in DOWNLOADS_DIRS:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if pdf_src.exists():
                pdf_dest = target_dir / f"{project_id}.pdf"
                shutil.copy2(pdf_src, pdf_dest)
            
            zip_dest = target_dir / f"{project_id}_overleaf.zip"
            with open(zip_dest, "wb") as f:
                f.write(zip_bytes)
            saved_locations.append(str(target_dir))
        except Exception as e:
            print(f"Failed to copy to {target_dir}: {e}")

    primary_pdf = PRIMARY_DOWNLOADS_DIR / f"{project_id}.pdf"
    primary_zip = PRIMARY_DOWNLOADS_DIR / f"{project_id}_overleaf.zip"

    return {
        "success": True,
        "message": f"Saved directly to {PRIMARY_DOWNLOADS_DIR}",
        "downloads_dir": str(PRIMARY_DOWNLOADS_DIR),
        "pdf_file": str(primary_pdf),
        "zip_file": str(primary_zip),
        "pdf_filename": f"{project_id}.pdf",
        "zip_filename": f"{project_id}_overleaf.zip"
    }

@app.post("/api/open-explorer")
def open_explorer(req: OpenExplorerRequest):
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    
    if req.file_type == "pdf":
        target = PRIMARY_DOWNLOADS_DIR / f"{req.project_id}.pdf"
    else:
        target = PRIMARY_DOWNLOADS_DIR / f"{req.project_id}_overleaf.zip"
    
    if target.exists():
        subprocess.Popen(f'explorer.exe /select,"{target}"')
        return {"success": True, "opened": str(target)}
    else:
        subprocess.Popen(f'explorer.exe "{PRIMARY_DOWNLOADS_DIR}"')
        return {"success": True, "opened": str(PRIMARY_DOWNLOADS_DIR)}

if __name__ == "__main__":
    start_inactivity_watchdog()
    sidecar_port = os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT")
    port = int(sidecar_port) if sidecar_port else 7357
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
