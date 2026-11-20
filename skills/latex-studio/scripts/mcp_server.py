import os
import sys
import time
import threading
import urllib.request
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Add scripts directory to path to import server logic
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import server

# Create FastMCP instance
mcp = FastMCP("latex-studio")

def start_background_api():
    """Starts FastAPI/Uvicorn backend on 127.0.0.1:7357 if not already running."""
    try:
        req = urllib.request.Request("http://127.0.0.1:7357/api/health", headers={"User-Agent": "MCPHealth"})
        with urllib.request.urlopen(req, timeout=0.5) as r:
            if r.status == 200:
                return
    except Exception:
        pass

    import uvicorn
    try:
        config = uvicorn.Config(server.app, host="127.0.0.1", port=7357, log_level="warning")
        uv_server = uvicorn.Server(config)
        uv_server.run()
    except Exception as e:
        # Port already bound or other non-fatal error
        pass

# Start API server in background daemon thread
api_thread = threading.Thread(target=start_background_api, daemon=True)
api_thread.start()

@mcp.tool()
def list_latex_projects() -> str:
    """Lists all available LaTeX projects in the workspace."""
    res = server.list_projects()
    projects = res.get("projects", [])
    lines = [f"- {p['id']}: {p['name']} (PDF compiled: {p['has_pdf']})" for p in projects]
    return f"Downloads Folder: {res.get('downloads_dir')}\nProjects:\n" + ("\n".join(lines) if lines else "None")

@mcp.tool()
def create_latex_project(name: str, template: str = "ieee") -> str:
    """Creates a new LaTeX project from template ('ieee', 'report', or 'blank')."""
    req = server.CreateProjectRequest(name=name, template=template)
    res = server.create_project(req)
    return f"Project created successfully: {res['id']} using '{template}' template."

@mcp.tool()
def compile_latex_project(project_id: str, code: str, filename: str = "main.tex") -> str:
    """Compiles LaTeX code for a project using Tectonic XeTeX engine and returns status and page count."""
    req = server.CompileRequest(project_id=project_id, code=code, filename=filename)
    res = server.compile_project(req)
    if res.get("success"):
        return f"Compiled successfully in {res.get('compile_time')}s. Page count: {res.get('page_count')}."
    else:
        return f"Compilation failed in {res.get('compile_time')}s:\n{res.get('error')}"

@mcp.tool()
def export_latex_project(project_id: str) -> str:
    """Exports compiled PDF and Overleaf-ready ZIP bundle directly to the user's Downloads folder (D:\\DOWNLOADS)."""
    try:
        res = server.export_to_downloads(project_id)
        return f"Exported successfully!\nPDF: {res['pdf_file']}\nZIP: {res['zip_file']}"
    except Exception as e:
        return f"Export failed: {str(e)}"

@mcp.tool()
def rename_latex_project(project_id: str, new_name: str) -> str:
    """Renames an existing LaTeX project."""
    req = server.RenameProjectRequest(new_name=new_name)
    res = server.rename_project(project_id, req)
    return f"Project renamed to '{res['name']}' (ID: {res['id']})."

@mcp.tool()
def delete_latex_project(project_id: str) -> str:
    """Permanently deletes a LaTeX project and all its files."""
    res = server.delete_project(project_id)
    return f"Project '{res['deleted']}' deleted successfully."

if __name__ == "__main__":
    mcp.run()
