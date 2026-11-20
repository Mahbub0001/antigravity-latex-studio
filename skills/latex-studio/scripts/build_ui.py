import json
import base64
import io
import os
import sys
import argparse
import datetime
import re
from pathlib import Path
import pypdfium2 as pdfium

SCRIPTS_DIR = Path(__file__).parent

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

def get_downloads_dir() -> Path:
    if os.name == "nt":
        try:
            import winreg
            sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                val, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                p = Path(os.path.expandvars(val))
                if p.exists():
                    return p
        except Exception:
            pass
    dl = Path.home() / "Downloads"
    dl.mkdir(parents=True, exist_ok=True)
    return dl

def build(project_id: str = None, output_path: Path = None):
    # Detect all available projects
    projects = []
    for p in PROJECTS_ROOT.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            tex_file = p / "main.tex"
            pdf_file = p / "main.pdf"
            meta_file = p / "metadata.json"
            
            title = p.name.replace("_", " ").title()
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as mf:
                        mdata = json.load(mf)
                        if "title" in mdata and mdata["title"]:
                            title = mdata["title"]
                except Exception:
                    pass
            
            doc_class = "article"
            if tex_file.exists():
                try:
                    with open(tex_file, "r", encoding="utf-8", errors="ignore") as f:
                        tex_c = f.read(1500)
                        m = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", tex_c)
                        if m:
                            doc_class = m.group(1).strip()
                except Exception:
                    pass

            page_count = 0
            if pdf_file.exists():
                try:
                    with open(pdf_file, "rb") as pf:
                        doc = pdfium.PdfDocument(pf.read())
                        page_count = len(doc)
                        doc.close()
                except Exception:
                    page_count = 1

            mtime = p.stat().st_mtime
            updated_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y %I:%M %p")

            projects.append({
                "id": p.name,
                "name": title,
                "slug": p.name,
                "has_pdf": pdf_file.exists(),
                "page_count": page_count,
                "doc_class": doc_class,
                "updated_at": mtime,
                "updated_at_str": updated_str
            })
            
    projects.sort(key=lambda x: x["updated_at"], reverse=True)

    # Determine default project
    if not project_id:
        if any(p["id"] == "bangla_trimodal_sentiment" for p in projects):
            project_id = "bangla_trimodal_sentiment"
        elif any(p["id"] == "bengali_sentiment_7class" for p in projects):
            project_id = "bengali_sentiment_7class"
        elif any(p["id"] == "neural_schrodinger_bridges" for p in projects):
            project_id = "neural_schrodinger_bridges"
        elif projects:
            project_id = projects[0]["id"]
        else:
            project_id = "default_project"

    p_dir = PROJECTS_ROOT / project_id
    tex_path = p_dir / "main.tex"
    tex_code = ""
    if tex_path.exists():
        with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
            tex_code = f.read()

    bib_path = p_dir / "references.bib"
    bib_code = ""
    if bib_path.exists():
        with open(bib_path, "r", encoding="utf-8", errors="ignore") as f:
            bib_code = f.read()

    pdf_path = p_dir / "main.pdf"
    pdf_base64 = ""
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

    # Read PDF.js static assets for 100% self-contained inlining
    static_dir = Path(__file__).resolve().parent / "static"
    pdf_js_content = ""
    pdf_js_path = static_dir / "pdf.min.js"
    if pdf_js_path.exists():
        with open(pdf_js_path, "r", encoding="utf-8", errors="ignore") as f:
            pdf_js_content = f.read()

    pdf_worker_content = ""
    pdf_worker_path = static_dir / "pdf.worker.min.js"
    if pdf_worker_path.exists():
        with open(pdf_worker_path, "r", encoding="utf-8", errors="ignore") as f:
            pdf_worker_content = f.read()

    pdf_css_content = ""
    pdf_css_path = static_dir / "pdf_viewer.min.css"
    if pdf_css_path.exists():
        with open(pdf_css_path, "r", encoding="utf-8", errors="ignore") as f:
            pdf_css_content = f.read()

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LaTeX Studio | Overleaf & XeTeX Interactive Studio</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  
  <!-- PDF.js Inlined Viewer CSS & Core Library for Guaranteed Offline & Webview Support -->
  <style>
/* PDF.js Viewer CSS Inlined */
__PDF_VIEWER_CSS__
  </style>

  <script>
/* PDF.js Core Inlined */
__PDF_JS_CORE__
  </script>

  <script>
/* Inlined Worker Init with Blob URL */
window.pdfWorkerScriptSource = __INLINED_WORKER_SOURCE__;
(function() {
  try {
    if (window.pdfjsLib && window.pdfWorkerScriptSource) {
      const blob = new Blob([window.pdfWorkerScriptSource], { type: 'application/javascript' });
      window.pdfWorkerBlobUrl = URL.createObjectURL(blob);
      pdfjsLib.GlobalWorkerOptions.workerSrc = window.pdfWorkerBlobUrl;
    }
  } catch (err) {
    console.warn("Failed to create blob worker:", err);
  }
})();
  </script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    
    * {
      box-sizing: border-box;
    }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .code-font {
      font-family: 'Fira Code', Consolas, "Courier New", monospace;
    }
    .viewer-bg {
      background-color: #202124;
    }
    .a4-sheet-shadow {
      box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5), 0 4px 12px -2px rgba(0, 0, 0, 0.3);
    }
    ::-webkit-scrollbar {
      width: 7px;
      height: 7px;
    }
    ::-webkit-scrollbar-track {
      background: #14141d;
    }
    ::-webkit-scrollbar-thumb {
      background: #313244;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #45475a;
    }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
      -webkit-appearance: none; 
      margin: 0; 
    }
    input[type=number] {
      -moz-appearance: textfield;
    }

    /* PDF.js Native TextLayer Styling for 100% Selectable Text */
    .textLayer {
      position: absolute;
      text-align: initial;
      left: 0;
      top: 0;
      right: 0;
      bottom: 0;
      overflow: hidden;
      opacity: 1;
      line-height: 1.0;
      text-size-adjust: none;
      forced-color-adjust: none;
      transform-origin: 0 0;
      z-index: 2;
      user-select: text !important;
      -webkit-user-select: text !important;
    }

    .textLayer span,
    .textLayer br {
      color: transparent !important;
      position: absolute;
      white-space: pre;
      cursor: text !important;
      transform-origin: 0% 0%;
    }

    .textLayer ::selection {
      background: rgba(59, 130, 246, 0.45) !important;
      color: transparent !important;
    }

    .textLayer ::-moz-selection {
      background: rgba(59, 130, 246, 0.45) !important;
      color: transparent !important;
    }
  </style>
</head>
<body class="bg-[#11111b] text-[#cdd6f4] h-screen flex flex-col overflow-hidden m-0 p-0 select-none">

  <!-- Top Toast Notification for Downloads -->
  <div id="toastNotification" class="fixed top-14 right-6 z-50 transform transition-all duration-300 translate-y-[-140px] opacity-0 pointer-events-none">
    <div class="bg-[#181825] border border-emerald-500/80 shadow-2xl rounded-xl p-3.5 flex items-center space-x-3.5 text-xs text-white">
      <div class="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 text-base font-bold">
        &#10003;
      </div>
      <div class="space-y-0.5">
        <div id="toastTitle" class="font-semibold text-emerald-400 text-xs">Saved to Downloads Folder!</div>
        <div id="toastMsg" class="text-gray-300 font-mono text-[11px] truncate max-w-[280px]">D:\\\\DOWNLOADS</div>
      </div>
      <button onclick="openInExplorer()" class="ml-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition pointer-events-auto shadow-sm flex items-center gap-1.5 shrink-0 cursor-pointer active:scale-95">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/></svg>
        <span>Open in Folder</span>
      </button>
    </div>
  </div>

  <!-- VIEW 1: Overleaf-style Projects Dashboard View -->
  <div id="projectsDashboardView" class="hidden flex-1 flex-col h-full bg-[#11111b] overflow-hidden">
    <!-- Top Bar for Dashboard -->
    <header class="h-13 border-b border-[#28283d] bg-[#181825] px-6 flex items-center justify-between shrink-0 shadow-sm z-10">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
          L
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <span class="text-sm font-bold text-white tracking-tight">LaTeX Studio</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-mono font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">Overleaf Companion</span>
          </div>
          <div class="text-[11px] text-gray-400">High-Precision Tectonic XeTeX Engine</div>
        </div>
      </div>

      <!-- Search Bar -->
      <div class="flex-1 max-w-md mx-6">
        <div class="relative">
          <svg class="w-4 h-4 text-gray-500 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input type="text" id="projectSearchInput" oninput="onSearchProjects(this.value)" placeholder="Search projects by name or slug..." class="w-full bg-[#11111b] border border-[#313244] text-xs text-white rounded-lg pl-9 pr-4 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none placeholder-gray-500 transition font-sans" />
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center space-x-2.5">
        <button onclick="refreshProjectsDashboard()" title="Refresh projects" class="p-2 rounded-lg bg-[#24273a] hover:bg-[#313244] text-gray-300 hover:text-white border border-[#363a4f] transition cursor-pointer active:scale-95">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        </button>

        <button onclick="openNewProjectModal()" class="flex items-center space-x-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-2 rounded-lg transition font-semibold shadow-sm cursor-pointer active:scale-95">
          <span class="text-sm font-bold leading-none">+</span>
          <span>New Project</span>
        </button>

        <button id="dashReturnToEditorBtn" onclick="returnToEditor()" class="hidden flex items-center space-x-1.5 text-xs bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white px-3 py-2 rounded-lg border border-emerald-500/30 transition font-medium cursor-pointer">
          <span>Go to Editor</span>
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
        </button>
      </div>
    </header>

    <!-- Main Dashboard Body -->
    <div class="flex-1 overflow-y-auto px-6 py-7">
      <div class="max-w-6xl mx-auto space-y-6">
        
        <!-- Header Info & Filter Bar -->
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-xl font-bold text-white flex items-center gap-2.5">
              <span>All Projects</span>
              <span id="dashProjectCountBadge" class="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-[#24273a] text-gray-300 border border-[#363a4f]">0</span>
            </h1>
            <p class="text-xs text-gray-400 mt-1">
              Projects stored on disk at <code class="text-blue-400 font-mono">e:\\github-projects\\exp\\projects</code>
            </p>
          </div>
          
          <div class="flex items-center space-x-2 text-xs text-gray-400">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Local Backend Port 7357</span>
          </div>
        </div>

        <!-- Projects Table -->
        <div class="bg-[#181825] border border-[#28283d] rounded-xl overflow-hidden shadow-xl">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-[#28283d] bg-[#14141f] text-gray-400 font-medium uppercase tracking-wider text-[11px]">
                <th class="py-3 px-5">Project Title</th>
                <th class="py-3 px-4">Document Class</th>
                <th class="py-3 px-4">Status / Pages</th>
                <th class="py-3 px-4">Last Modified</th>
                <th class="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="projectsTableBody" class="divide-y divide-[#222233]">
              <!-- Dynamically populated rows -->
            </tbody>
          </table>
          
          <!-- Empty State -->
          <div id="projectsEmptyState" class="hidden py-14 flex flex-col items-center justify-center text-center text-gray-400 space-y-3">
            <div class="w-12 h-12 rounded-full bg-[#24273a] flex items-center justify-center text-gray-500 text-xl font-bold">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
            </div>
            <div>
              <div class="text-sm font-semibold text-gray-300">No projects found</div>
              <div class="text-xs text-gray-500 mt-0.5">Try searching with another keyword or create a new project.</div>
            </div>
            <button onclick="openNewProjectModal()" class="mt-2 bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer">
              + Create New Project
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>

  <!-- VIEW 2: Overleaf-style Split Studio Editor View -->
  <div id="studioView" class="flex-1 flex flex-col h-full overflow-hidden relative">
    <!-- Sleek Top Navigation Bar -->
    <header class="h-12 border-b border-[#28283d] bg-[#181825] px-3.5 flex items-center justify-between shrink-0 shadow-sm z-10">
      <div class="flex items-center space-x-2.5">
        
        <!-- Overleaf-style "< Projects" Button to switch to Dashboard -->
        <button onclick="showProjectsDashboard()" class="flex items-center space-x-1.5 text-xs bg-[#24273a] hover:bg-[#313244] text-white px-2.5 py-1.5 rounded-lg border border-[#3b3f58] transition font-semibold cursor-pointer active:scale-95" title="View all projects in dashboard">
          <svg class="w-3.5 h-3.5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
          <span>Projects</span>
        </button>

        <span class="text-xs text-gray-600">/</span>

        <!-- Current Project Name with Inline Rename Modal trigger -->
        <div class="flex items-center space-x-1.5 bg-[#11111b] px-2.5 py-1 rounded-lg border border-[#313244]">
          <svg class="w-3.5 h-3.5 text-blue-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          <span id="studioProjectTitle" class="text-xs font-semibold text-white max-w-[210px] truncate" title="Current project"></span>
          <button onclick="triggerRenameFromHeader()" class="p-0.5 text-gray-400 hover:text-blue-400 rounded transition cursor-pointer" title="Rename this project">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
          </button>
        </div>

        <!-- New Project Button -->
        <button onclick="openNewProjectModal()" class="flex items-center space-x-1 text-xs bg-[#24273a] hover:bg-[#313244] text-gray-200 px-2.5 py-1 rounded-lg transition font-medium border border-[#363a4f] shadow-xs cursor-pointer active:scale-95" title="Create another project">
          <span class="text-blue-400 font-bold">+</span>
          <span>New</span>
        </button>

        <span class="text-xs text-gray-600">/</span>
        <span id="currentFileNameBadge" class="text-xs font-mono text-gray-300 bg-black/20 px-2 py-0.5 rounded border border-[#28283d]">main.tex</span>
      </div>

      <!-- Actions & Toolbar -->
      <div class="flex items-center space-x-2">
        
        <!-- Status Badge -->
        <div id="statusBadge" class="flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span id="statusText" class="font-medium text-[11px]">Ready</span>
        </div>

        <!-- Realtime Live Auto-Compile Toggle -->
        <button id="autoCompileToggleBtn" onclick="toggleAutoCompile()" class="flex items-center space-x-1.5 text-xs bg-[#24273a] hover:bg-[#313244] text-emerald-400 px-2.5 py-1.5 rounded-lg border border-emerald-500/30 transition font-medium cursor-pointer active:scale-95" title="Toggle automatic compilation on edit">
          <span id="autoCompileDot" class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span id="autoCompileLabel" class="font-medium text-[11px]">Live: ON</span>
        </button>

        <!-- Recompile Button (Overleaf Green) -->
        <button onclick="triggerCompile(false)" id="recompileBtn" class="flex items-center space-x-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-1.5 rounded-lg transition font-semibold shadow-sm cursor-pointer active:scale-95">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          <span>Recompile</span>
          <kbd class="text-[9px] bg-emerald-800/80 px-1.5 py-0.2 rounded font-mono font-normal">Ctrl+Enter</kbd>
        </button>

        <!-- Download PDF Button -->
        <button onclick="exportDownloads('pdf')" class="flex items-center space-x-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg transition font-medium shadow-sm cursor-pointer active:scale-95" title="Download compiled PDF to D:\\\\DOWNLOADS">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <span>Download PDF</span>
        </button>

        <!-- Download Overleaf ZIP Button -->
        <button onclick="exportDownloads('zip')" class="flex items-center space-x-1.5 text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg transition font-medium shadow-sm cursor-pointer active:scale-95" title="Download Overleaf-ready project ZIP to D:\\\\DOWNLOADS">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
          <span>Overleaf ZIP</span>
        </button>

        <!-- Copy Code -->
        <button onclick="copyCode()" id="copyBtn" class="flex items-center space-x-1 text-xs border border-[#313244] text-gray-300 px-2.5 py-1.5 rounded-lg hover:bg-[#24273a] transition font-medium cursor-pointer">
          <span id="copyBtnText">Copy</span>
        </button>
      </div>
    </header>

    <!-- Split Studio Layout -->
    <div class="flex-1 flex overflow-hidden">
      
      <!-- Left Pane: LaTeX Code Editor (46%) -->
      <div class="w-[46%] flex flex-col border-r border-[#28283d] bg-[#181825] text-[#cdd6f4]">
        <!-- Tab Bar -->
        <div class="h-9 bg-[#11111b] border-b border-[#28283d] px-3 flex items-center justify-between text-xs">
          <div class="flex items-center space-x-1.5">
            <button id="tabMainTex" onclick="switchTab('main.tex')" class="px-3 py-1.5 bg-[#181825] text-blue-400 font-mono text-[11px] font-semibold rounded-t-md border-t-2 border-blue-500 flex items-center gap-1.5 transition cursor-pointer">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span>main.tex</span>
            </button>
            <button id="tabBib" onclick="switchTab('references.bib')" class="px-3 py-1.5 text-gray-400 hover:text-gray-200 font-mono text-[11px] rounded-t-md flex items-center gap-1.5 transition cursor-pointer">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
              <span>references.bib</span>
            </button>
          </div>
          <div class="flex items-center space-x-2 text-[11px] text-gray-400 font-mono">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>Tectonic XeTeX</span>
          </div>
        </div>

        <!-- Code Textarea & Line Numbers -->
        <div class="flex-1 flex overflow-hidden relative font-mono text-xs leading-relaxed">
          <div id="lineNumbers" class="w-11 bg-[#11111b] text-gray-600 text-right pr-2 pt-3 select-none code-font border-r border-[#28283d] overflow-hidden">
            1
          </div>
          <textarea id="latexCode" spellcheck="false" onscroll="syncScroll()" class="flex-1 bg-transparent text-[#cdd6f4] p-3 resize-none outline-none code-font overflow-y-auto whitespace-pre selection:bg-blue-600/30 font-medium"></textarea>
        </div>

        <!-- Collapsible In-App LaTeX Error Drawer -->
        <div id="errorDrawer" class="hidden bg-red-950/80 border-t border-red-500/40 px-3.5 py-2 text-xs font-mono text-red-200 shrink-0">
          <div class="flex items-center justify-between font-semibold text-red-400 mb-1">
            <span class="flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <span>LaTeX Compilation Notice</span>
            </span>
            <button onclick="dismissErrorDrawer()" class="text-gray-400 hover:text-white cursor-pointer font-bold px-1">&times;</button>
          </div>
          <pre id="errorDrawerText" class="text-[11px] leading-snug whitespace-pre-wrap max-h-24 overflow-y-auto selection:bg-red-800 text-red-300"></pre>
        </div>

        <!-- Editor Footer -->
        <div class="h-7 bg-[#11111b] border-t border-[#28283d] px-3.5 flex items-center justify-between text-[11px] text-gray-400 font-mono shrink-0">
          <span id="lineCount">Lines: 0</span>
          <span class="text-emerald-400 flex items-center gap-1 font-sans">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            Live Reactive Sync
          </span>
        </div>
      </div>

      <!-- Right Pane: Real Vector PDF.js Canvas Viewer with Native Text Selection (54%) -->
      <div class="w-[54%] flex flex-col viewer-bg overflow-hidden relative">
        
        <!-- PDF Canvas Toolbar with Precise 1% Zoom Engine -->
        <div class="h-9 bg-[#1a1b1e] border-b border-[#2c2d31] px-4 flex items-center justify-between text-xs text-gray-200 shrink-0">
          <div class="flex items-center space-x-3">
            <span class="font-semibold text-gray-200 tracking-wide">PDF PREVIEW</span>
            <span id="pageCountBadge" class="bg-[#28292d] px-2 py-0.5 rounded text-[11px] text-gray-300 font-mono border border-gray-700">
              Page 1 of 1
            </span>
            <span class="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-medium">
              Selectable Text Layer
            </span>
          </div>

          <div class="flex items-center space-x-3 text-[11px]">
            <span id="compileTime" class="text-emerald-400 font-mono font-medium">&#10003; Ready</span>
            <span class="text-gray-600">|</span>
            
            <!-- Dedicated 1% Precision Zoom Controls -->
            <div class="flex items-center bg-[#28292d] border border-gray-700 rounded-lg p-0.5 shadow-xs">
              <!-- -1% Button -->
              <button onclick="stepZoom(-1)" class="w-6 h-6 flex items-center justify-center hover:bg-gray-700 text-gray-200 hover:text-white rounded font-bold text-xs transition active:scale-90 cursor-pointer" title="Zoom out (-1%)">
                &minus;
              </button>
              
              <!-- Zoom Editable Percentage Input (1% Precision) -->
              <div class="flex items-center px-1">
                <input type="number" id="zoomInput" value="100" min="20" max="300" step="1" onchange="onZoomInputChange(this.value)" oninput="onZoomInputChange(this.value)" class="w-10 bg-transparent text-center font-mono text-xs text-white outline-none font-semibold" />
                <span class="text-gray-400 text-[10px]">%</span>
              </div>

              <!-- +1% Button -->
              <button onclick="stepZoom(1)" class="w-6 h-6 flex items-center justify-center hover:bg-gray-700 text-gray-200 hover:text-white rounded font-bold text-xs transition active:scale-90 cursor-pointer" title="Zoom in (+1%)">
                &#43;
              </button>
            </div>

            <!-- Fit Presets -->
            <button onclick="fitWidth()" class="hover:bg-gray-700 text-gray-300 hover:text-white px-2 py-1 rounded transition text-[11px] cursor-pointer">
              Fit Width
            </button>
            <button onclick="setExactZoom(100)" class="hover:bg-gray-700 text-gray-300 hover:text-white px-2 py-1 rounded transition text-[11px] cursor-pointer">
              100%
            </button>
          </div>
        </div>

        <!-- Realtime Compile Progress Bar (Animated) -->
        <div id="compileProgressBar" class="h-0.5 w-full bg-transparent overflow-hidden shrink-0">
          <div id="compileProgressLine" class="h-full bg-blue-500 w-full hidden animate-pulse"></div>
        </div>

        <!-- Rendered Page Viewport (PDF.js Canvas & Selectable Text Layers) -->
        <div id="pagesViewport" class="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col items-center select-text">
          <!-- Rendered page canvases and text layers injected here -->
        </div>

        <!-- Floating Live Status Pill -->
        <div id="liveCompilingPill" class="absolute bottom-6 right-8 z-40 bg-[#181825]/95 border border-blue-500/50 text-blue-300 px-3.5 py-1.5 rounded-full shadow-2xl text-xs font-mono hidden items-center space-x-2 backdrop-blur-md pointer-events-none">
          <svg class="animate-spin h-3.5 w-3.5 text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span id="liveCompilingMsg">Rendering live preview...</span>
        </div>

      </div>

    </div>
  </div>

  <!-- MODAL 1: Rename Project Modal -->
  <div id="renameModal" class="fixed inset-0 bg-black/75 backdrop-blur-xs z-50 hidden items-center justify-center p-4">
    <div class="bg-[#181825] border border-[#313244] rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-5">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
          <span>Rename Project</span>
        </h3>
        <button onclick="closeRenameModal()" class="text-gray-400 hover:text-white text-lg font-bold p-1 cursor-pointer">&times;</button>
      </div>

      <input type="hidden" id="renameTargetProjectId" value="" />
      <div>
        <label class="block text-xs font-semibold text-gray-300 mb-1.5">Project Title</label>
        <input type="text" id="renameProjectInput" class="w-full bg-[#11111b] border border-[#363a4f] rounded-lg px-3.5 py-2 text-xs text-white focus:border-blue-500 outline-none font-medium" />
        <p class="text-[11px] text-gray-500 mt-1.5">This updates the project title across the studio, dashboard, and downloads.</p>
      </div>

      <div class="flex items-center justify-end space-x-2.5 pt-2">
        <button onclick="closeRenameModal()" class="px-4 py-2 text-xs font-medium text-gray-300 hover:text-white hover:bg-[#24273a] rounded-lg transition cursor-pointer">
          Cancel
        </button>
        <button onclick="submitRenameProject()" id="submitRenameBtn" class="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition shadow-sm cursor-pointer active:scale-95">
          Save Changes
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL 2: Delete Project Confirmation Modal -->
  <div id="deleteModal" class="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 hidden items-center justify-center p-4">
    <div class="bg-[#181825] border border-red-500/30 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-5">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-red-400 flex items-center gap-2">
          <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          <span>Delete Project</span>
        </h3>
        <button onclick="closeDeleteModal()" class="text-gray-400 hover:text-white text-lg font-bold p-1 cursor-pointer">&times;</button>
      </div>

      <input type="hidden" id="deleteTargetProjectId" value="" />
      <div>
        <p class="text-xs text-gray-300">
          Are you sure you want to permanently delete <strong id="deleteProjectNameDisplay" class="text-white"></strong>?
        </p>
        <p class="text-xs text-red-400/90 mt-2 bg-red-500/10 border border-red-500/20 p-2.5 rounded-lg leading-relaxed">
          Warning: All files (.tex, references.bib, compiled PDF, figures) in this project directory will be permanently removed.
        </p>
      </div>

      <div class="flex items-center justify-end space-x-2.5 pt-2">
        <button onclick="closeDeleteModal()" class="px-4 py-2 text-xs font-medium text-gray-300 hover:text-white hover:bg-[#24273a] rounded-lg transition cursor-pointer">
          Cancel
        </button>
        <button onclick="submitDeleteProject()" id="submitDeleteBtn" class="px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-500 text-white rounded-lg transition shadow-sm cursor-pointer active:scale-95">
          Delete Permanently
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL 3: New Project Modal -->
  <div id="newProjectModal" class="fixed inset-0 bg-black/75 backdrop-blur-xs z-50 hidden items-center justify-center p-4">
    <div class="bg-[#181825] border border-[#313244] rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-5">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          <span>Create New Project</span>
        </h3>
        <button onclick="closeNewProjectModal()" class="text-gray-400 hover:text-white text-lg font-bold p-1 cursor-pointer">&times;</button>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-gray-300 mb-1.5">Project Name</label>
          <input type="text" id="newProjName" placeholder="e.g. LLM Inference Benchmark" class="w-full bg-[#11111b] border border-[#363a4f] rounded-lg px-3.5 py-2 text-xs text-white focus:border-blue-500 outline-none font-medium" />
        </div>

        <div>
          <label class="block text-xs font-semibold text-gray-300 mb-1.5">LaTeX Document Template</label>
          <select id="newProjTemplate" class="w-full bg-[#11111b] border border-[#363a4f] rounded-lg px-3 py-2 text-xs text-white focus:border-blue-500 outline-none">
            <option value="ieee">IEEE Transactions (2-column journal/conference)</option>
            <option value="report">Academic Technical Report / Preprint</option>
            <option value="blank">Minimal Blank Document</option>
          </select>
        </div>
      </div>

      <div class="flex items-center justify-end space-x-2.5 pt-2">
        <button onclick="closeNewProjectModal()" class="px-4 py-2 text-xs font-medium text-gray-300 hover:text-white hover:bg-[#24273a] rounded-lg transition cursor-pointer">
          Cancel
        </button>
        <button onclick="submitNewProject()" id="submitNewProjBtn" class="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition shadow-sm cursor-pointer active:scale-95">
          Create & Open
        </button>
      </div>
    </div>
  </div>

  <script>
    const API_BASE = "http://127.0.0.1:7357";
    let currentProjectId = __CURRENT_PROJ_ID__;
    let projectsList = __PROJECTS_LIST__;
    let currentPdfBase64 = __PDF_BASE64__;
    let currentPdfDoc = null;
    let isRenderingPdf = false;
    let pendingRenderPdf = false;

    let activeFile = "main.tex";
    let currentZoom = 100;
    let lastExportedType = 'pdf';
    let currentView = 'studio';

    let autoCompileEnabled = true;
    let autoCompileTimer = null;
    let isCompiling = false;
    let pendingCompile = false;

    let fileContents = {
      "main.tex": __MAIN_TEX__,
      "references.bib": __REF_BIB__
    };

    function initPdfWorker() {
      if (typeof pdfjsLib === 'undefined') return;
      if (window.pdfWorkerBlobUrl) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = window.pdfWorkerBlobUrl;
        return;
      }
      try {
        if (window.pdfWorkerScriptSource) {
          const blob = new Blob([window.pdfWorkerScriptSource], { type: 'application/javascript' });
          window.pdfWorkerBlobUrl = URL.createObjectURL(blob);
          pdfjsLib.GlobalWorkerOptions.workerSrc = window.pdfWorkerBlobUrl;
        } else {
          pdfjsLib.GlobalWorkerOptions.workerSrc = 'http://127.0.0.1:7357/static/pdf.worker.min.js';
        }
      } catch (e) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'http://127.0.0.1:7357/static/pdf.worker.min.js';
      }
    }

    async function init() {
      // 1. Initialise Code & Line Numbers
      document.getElementById('latexCode').value = fileContents[activeFile] || '';
      updateLineNumbers();
      initPdfWorker();
      setExactZoom(100);

      // Render initial PDF with selectable text
      if (currentPdfBase64) {
        await renderPdfFromBase64(currentPdfBase64);
      }

      // 2. Start heartbeat loop to keep backend alive
      startHeartbeatLoop();

      // 3. Inspect URL query params
      const urlParams = new URLSearchParams(window.location.search);
      const urlProject = urlParams.get('project');
      const urlView = urlParams.get('view');

      // 4. Fetch live projects list from API
      await fetchProjectsList();

      // 5. Determine initial view
      if (urlView === 'projects' || urlView === 'dashboard') {
        showProjectsDashboard();
      } else if (urlProject) {
        await switchToStudioView(urlProject);
      } else {
        switchToStudioView(currentProjectId);
      }

      // Keyboard shortcuts
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'Enter' || e.key === 's')) {
          e.preventDefault();
          if (currentView === 'studio') {
            triggerCompile(false);
          }
        }
        if (e.key === 'Escape') {
          closeRenameModal();
          closeDeleteModal();
          closeNewProjectModal();
          dismissErrorDrawer();
        }
      });

      // Realtime typing listener
      document.getElementById('latexCode').addEventListener('input', () => {
        fileContents[activeFile] = document.getElementById('latexCode').value;
        updateLineNumbers();
        scheduleAutoCompile();
      });

      // Ctrl + Wheel to Zoom in/out smoothly by 1%
      document.getElementById('pagesViewport').addEventListener('wheel', (e) => {
        if (e.ctrlKey) {
          e.preventDefault();
          stepZoom(e.deltaY < 0 ? 1 : -1);
        }
      }, { passive: false });

      // Graceful disconnect on window unload
      window.addEventListener('beforeunload', () => {
        try { navigator.sendBeacon(`${API_BASE}/api/client-disconnect`); } catch (e) {}
      });
      window.addEventListener('pagehide', () => {
        try { navigator.sendBeacon(`${API_BASE}/api/client-disconnect`); } catch (e) {}
      });
    }

    // Realtime Auto-Compile Debounce Engine
    function scheduleAutoCompile() {
      if (!autoCompileEnabled) return;
      if (autoCompileTimer) clearTimeout(autoCompileTimer);

      const statusText = document.getElementById('statusText');
      if (!isCompiling) {
        statusText.innerText = "Typing...";
      }

      autoCompileTimer = setTimeout(() => {
        triggerCompile(true);
      }, 1000);
    }

    function toggleAutoCompile() {
      autoCompileEnabled = !autoCompileEnabled;
      const btn = document.getElementById('autoCompileToggleBtn');
      const dot = document.getElementById('autoCompileDot');
      const label = document.getElementById('autoCompileLabel');

      if (autoCompileEnabled) {
        btn.className = "flex items-center space-x-1.5 text-xs bg-[#24273a] hover:bg-[#313244] text-emerald-400 px-2.5 py-1.5 rounded-lg border border-emerald-500/30 transition font-medium cursor-pointer active:scale-95";
        dot.className = "w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse";
        label.innerText = "Live: ON";
        scheduleAutoCompile();
      } else {
        btn.className = "flex items-center space-x-1.5 text-xs bg-[#1f202e] hover:bg-[#28293d] text-gray-400 px-2.5 py-1.5 rounded-lg border border-gray-700 transition font-medium cursor-pointer active:scale-95";
        dot.className = "w-1.5 h-1.5 rounded-full bg-gray-500";
        label.innerText = "Live: OFF";
      }
    }

    // Heartbeat loop
    function startHeartbeatLoop() {
      setInterval(async () => {
        try {
          await fetch(`${API_BASE}/api/heartbeat`, { method: 'POST' });
        } catch (e) {}
      }, 3000);
    }

    // Fetch projects from backend
    async function fetchProjectsList() {
      try {
        const res = await fetch(`${API_BASE}/api/projects`);
        if (res.ok) {
          const data = await res.json();
          if (data.projects) {
            projectsList = data.projects;
          }
        }
      } catch (err) {
        console.warn("Could not fetch projects list from API:", err);
      }
      renderProjectsDashboard(projectsList);
      updateStudioProjectHeader();
    }

    /* VIEW SWITCHING ENGINE */
    function showProjectsDashboard() {
      currentView = 'dashboard';
      document.getElementById('studioView').classList.add('hidden');
      document.getElementById('projectsDashboardView').classList.remove('hidden');
      document.getElementById('projectsDashboardView').classList.add('flex');

      try {
        const url = new URL(window.location);
        url.searchParams.delete('project');
        url.searchParams.set('view', 'projects');
        window.history.replaceState({}, '', url);
      } catch (e) {}

      fetchProjectsList();
      
      const returnBtn = document.getElementById('dashReturnToEditorBtn');
      if (currentProjectId) {
        returnBtn.classList.remove('hidden');
      } else {
        returnBtn.classList.add('hidden');
      }
    }

    function returnToEditor() {
      if (currentProjectId) {
        switchToStudioView(currentProjectId);
      }
    }

    async function switchToStudioView(projId) {
      currentView = 'studio';
      document.getElementById('projectsDashboardView').classList.add('hidden');
      document.getElementById('projectsDashboardView').classList.remove('flex');
      document.getElementById('studioView').classList.remove('hidden');

      if (projId && projId !== currentProjectId) {
        await switchProject(projId);
      } else {
        updateStudioProjectHeader();
        try {
          const url = new URL(window.location);
          url.searchParams.delete('view');
          url.searchParams.set('project', currentProjectId);
          window.history.replaceState({}, '', url);
        } catch (e) {}
      }
    }

    function updateStudioProjectHeader() {
      const p = projectsList.find(x => x.id === currentProjectId);
      const titleElem = document.getElementById('studioProjectTitle');
      if (p) {
        titleElem.innerText = p.name;
        titleElem.title = `${p.name} (${p.id})`;
      } else {
        titleElem.innerText = currentProjectId.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
      }
    }

    /* PROJECTS DASHBOARD RENDERING */
    function renderProjectsDashboard(list) {
      const tbody = document.getElementById('projectsTableBody');
      const emptyState = document.getElementById('projectsEmptyState');
      const countBadge = document.getElementById('dashProjectCountBadge');

      countBadge.innerText = list.length;

      if (!list || list.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
      }

      emptyState.classList.add('hidden');
      tbody.innerHTML = list.map(p => `
        <tr class="hover:bg-[#1e1e2e]/70 transition group">
          <td class="py-3 px-5">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
              </div>
              <div class="min-w-0">
                <button onclick="switchToStudioView('${p.id}')" class="text-left font-semibold text-white text-xs hover:text-blue-400 transition cursor-pointer group-hover:underline block truncate max-w-[320px]">
                  ${p.name}
                </button>
                <div class="text-[10px] text-gray-500 font-mono truncate max-w-[280px]">${p.id}</div>
              </div>
            </div>
          </td>

          <td class="py-3 px-4">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#24273a] text-gray-300 border border-[#363a4f]">
              ${p.doc_class || 'article'}
            </span>
          </td>

          <td class="py-3 px-4">
            ${p.has_pdf 
              ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">&#10003; ${p.page_count} ${p.page_count === 1 ? 'page' : 'pages'}</span>`
              : `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20">Not compiled</span>`
            }
          </td>

          <td class="py-3 px-4 text-gray-400 text-[11px] whitespace-nowrap">
            ${p.updated_at_str || 'Recently'}
          </td>

          <td class="py-3 px-5 text-right whitespace-nowrap">
            <div class="flex items-center justify-end space-x-1.5">
              <button onclick="switchToStudioView('${p.id}')" class="px-2.5 py-1 text-[11px] font-semibold bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white rounded-md transition cursor-pointer active:scale-95 flex items-center gap-1" title="Open in Studio Editor">
                <span>Open</span>
              </button>

              <button onclick="openRenameModal('${p.id}', '${p.name.replace(/'/g, "\\\\'")}')" class="p-1.5 hover:bg-[#28283d] text-gray-400 hover:text-white rounded-md transition cursor-pointer" title="Rename project">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
              </button>

              <button onclick="duplicateProject('${p.id}')" class="p-1.5 hover:bg-[#28283d] text-gray-400 hover:text-blue-400 rounded-md transition cursor-pointer" title="Duplicate project">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>

              <button onclick="exportDownloadsForProj('${p.id}', 'pdf')" class="p-1.5 hover:bg-emerald-500/20 text-gray-400 hover:text-emerald-400 rounded-md transition cursor-pointer" title="Download PDF to D:\\\\DOWNLOADS">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              </button>

              <button onclick="exportDownloadsForProj('${p.id}', 'zip')" class="p-1.5 hover:bg-purple-500/20 text-gray-400 hover:text-purple-400 rounded-md transition cursor-pointer" title="Download Overleaf ZIP to D:\\\\DOWNLOADS">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
              </button>

              <button onclick="openDeleteModal('${p.id}', '${p.name.replace(/'/g, "\\\\'")}')" class="p-1.5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 rounded-md transition cursor-pointer" title="Delete project">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `).join('');
    }

    function onSearchProjects(query) {
      const q = query.toLowerCase().trim();
      if (!q) {
        renderProjectsDashboard(projectsList);
        return;
      }
      const filtered = projectsList.filter(p => 
        p.name.toLowerCase().includes(q) || 
        p.id.toLowerCase().includes(q) ||
        (p.doc_class && p.doc_class.toLowerCase().includes(q))
      );
      renderProjectsDashboard(filtered);
    }

    async function refreshProjectsDashboard() {
      await fetchProjectsList();
    }

    /* RENAME PROJECT ENGINE */
    function triggerRenameFromHeader() {
      const p = projectsList.find(x => x.id === currentProjectId);
      const name = p ? p.name : currentProjectId;
      openRenameModal(currentProjectId, name);
    }

    function openRenameModal(projId, currentName) {
      document.getElementById('renameTargetProjectId').value = projId;
      document.getElementById('renameProjectInput').value = currentName || projId;
      document.getElementById('renameModal').classList.remove('hidden');
      document.getElementById('renameModal').classList.add('flex');
      setTimeout(() => document.getElementById('renameProjectInput').focus(), 50);
    }

    function closeRenameModal() {
      document.getElementById('renameModal').classList.add('hidden');
      document.getElementById('renameModal').classList.remove('flex');
    }

    async function submitRenameProject() {
      const projId = document.getElementById('renameTargetProjectId').value;
      const newName = document.getElementById('renameProjectInput').value.trim();
      if (!newName) return alert("Please enter a valid project name");

      const btn = document.getElementById('submitRenameBtn');
      btn.disabled = true;
      btn.innerText = "Saving...";

      try {
        const res = await fetch(`${API_BASE}/api/projects/${projId}/rename`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_name: newName })
        });
        const data = await res.json();
        if (data.success) {
          if (currentProjectId === projId) {
            currentProjectId = data.id;
          }
          await fetchProjectsList();
          closeRenameModal();
          showToast("Project Renamed Successfully!", newName);
        } else {
          alert("Rename failed: " + (data.detail || "Unknown error"));
        }
      } catch (err) {
        alert("Server error during rename: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerText = "Save Changes";
      }
    }

    /* DELETE PROJECT ENGINE */
    function openDeleteModal(projId, name) {
      document.getElementById('deleteTargetProjectId').value = projId;
      document.getElementById('deleteProjectNameDisplay').innerText = `"${name || projId}"`;
      document.getElementById('deleteModal').classList.remove('hidden');
      document.getElementById('deleteModal').classList.add('flex');
    }

    function closeDeleteModal() {
      document.getElementById('deleteModal').classList.add('hidden');
      document.getElementById('deleteModal').classList.remove('flex');
    }

    async function submitDeleteProject() {
      const projId = document.getElementById('deleteTargetProjectId').value;
      const btn = document.getElementById('submitDeleteBtn');
      btn.disabled = true;
      btn.innerText = "Deleting...";

      try {
        const res = await fetch(`${API_BASE}/api/projects/${projId}/delete`, {
          method: 'POST'
        });
        const data = await res.json();
        if (data.success) {
          closeDeleteModal();
          await fetchProjectsList();
          showToast("Project Deleted", projId);
          if (currentProjectId === projId) {
            if (projectsList.length > 0) {
              currentProjectId = projectsList[0].id;
              await switchToStudioView(currentProjectId);
            } else {
              showProjectsDashboard();
            }
          }
        } else {
          alert("Failed to delete project: " + (data.detail || "Unknown error"));
        }
      } catch (err) {
        alert("Server error during delete: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerText = "Delete Permanently";
      }
    }

    /* DUPLICATE PROJECT ENGINE */
    async function duplicateProject(projId) {
      try {
        const res = await fetch(`${API_BASE}/api/projects/${projId}/duplicate`, {
          method: 'POST'
        });
        const data = await res.json();
        if (data.success) {
          await fetchProjectsList();
          showToast("Project Cloned Successfully!", data.name);
        } else {
          alert("Failed to duplicate project: " + (data.detail || "Unknown error"));
        }
      } catch (err) {
        alert("Server error duplicating project: " + err.message);
      }
    }

    /* PDF.JS RENDERING & SELECTABLE TEXT ENGINE */
    async function renderPdfFromBase64(b64Data) {
      if (!b64Data) {
        document.getElementById('pagesViewport').innerHTML = 
          '<div class="text-gray-400 text-xs py-14">No compiled PDF found. Click Recompile.</div>';
        return;
      }

      if (typeof pdfjsLib === 'undefined') {
        document.getElementById('pagesViewport').innerHTML = 
          '<div class="text-amber-400 text-xs py-14">PDF engine initializing, please wait...</div>';
        setTimeout(() => renderPdfFromBase64(b64Data), 150);
        return;
      }

      try {
        initPdfWorker();
        const binaryString = atob(b64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }

        const loadingTask = pdfjsLib.getDocument({
          data: bytes,
          cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
          cMapPacked: true
        });

        currentPdfDoc = await loadingTask.promise;
        document.getElementById('pageCountBadge').innerText = `Page 1 of ${currentPdfDoc.numPages}`;
        await renderAllPages();
      } catch (err) {
        console.error("PDF.js render error:", err);
        document.getElementById('pagesViewport').innerHTML = 
          `<div class="text-red-400 text-xs py-14">Error loading PDF preview: ${err.message}</div>`;
      }
    }

    async function renderAllPages() {
      if (!currentPdfDoc) return;
      if (isRenderingPdf) {
        pendingRenderPdf = true;
        return;
      }
      isRenderingPdf = true;
      pendingRenderPdf = false;

      const viewport = document.getElementById('pagesViewport');
      const numPages = currentPdfDoc.numPages;
      const targetWidth = Math.round(595 * (currentZoom / 100));

      let existingContainers = viewport.querySelectorAll('.pdf-page-container');
      if (existingContainers.length !== numPages) {
        viewport.innerHTML = '';
        for (let i = 1; i <= numPages; i++) {
          const pageDiv = document.createElement('div');
          pageDiv.className = 'pdf-page-container flex flex-col items-center mb-6';
          pageDiv.id = `page-container-${i}`;
          pageDiv.innerHTML = `
            <div class="page-wrapper relative a4-sheet-shadow rounded-xs bg-white overflow-hidden select-text" style="width: ${targetWidth}px;">
              <canvas class="pdf-canvas block w-full"></canvas>
              <div class="textLayer select-text"></div>
            </div>
            <div class="text-[10px] text-gray-400 mt-2 font-mono select-none">Page ${i} of ${numPages}</div>
          `;
          viewport.appendChild(pageDiv);
        }
        existingContainers = viewport.querySelectorAll('.pdf-page-container');
      }

      try {
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
          const page = await currentPdfDoc.getPage(pageNum);
          const container = existingContainers[pageNum - 1];
          if (!container) continue;

          const wrapper = container.querySelector('.page-wrapper');
          const canvas = container.querySelector('.pdf-canvas');
          const textLayerDiv = container.querySelector('.textLayer');

          const unscaledViewport = page.getViewport({ scale: 1 });
          const scale = (targetWidth / unscaledViewport.width);
          const dpr = window.devicePixelRatio || 1.5;

          const displayWidth = targetWidth;
          const displayHeight = Math.round(unscaledViewport.height * scale);

          wrapper.style.width = displayWidth + 'px';
          wrapper.style.height = displayHeight + 'px';

          canvas.width = Math.round(displayWidth * dpr);
          canvas.height = Math.round(displayHeight * dpr);
          canvas.style.width = displayWidth + 'px';
          canvas.style.height = displayHeight + 'px';

          const ctx = canvas.getContext('2d');
          ctx.setTransform(1, 0, 0, 1, 0, 0);

          const renderContext = {
            canvasContext: ctx,
            viewport: page.getViewport({ scale: scale * dpr })
          };

          await page.render(renderContext).promise;

          // Render Native Selectable Text Layer
          const textViewport = page.getViewport({ scale: scale });
          textLayerDiv.innerHTML = '';
          textLayerDiv.style.width = displayWidth + 'px';
          textLayerDiv.style.height = displayHeight + 'px';
          textLayerDiv.style.setProperty('--scale-factor', textViewport.scale);

          const textContent = await page.getTextContent();

          await pdfjsLib.renderTextLayer({
            textContentSource: textContent,
            container: textLayerDiv,
            viewport: textViewport
          }).promise;
        }
      } catch (renderErr) {
        console.warn("Render page warning:", renderErr);
      } finally {
        isRenderingPdf = false;
        if (pendingRenderPdf) {
          pendingRenderPdf = false;
          renderAllPages();
        }
      }
    }

    /* 1% Precision Zoom Engine */
    function setExactZoom(newPercent) {
      currentZoom = Math.max(20, Math.min(300, Math.round(newPercent)));
      document.getElementById('zoomInput').value = currentZoom;
      renderAllPages();
    }

    function stepZoom(delta) {
      setExactZoom(currentZoom + delta);
    }

    function onZoomInputChange(val) {
      const num = parseInt(val, 10);
      if (!isNaN(num)) {
        setExactZoom(num);
      }
    }

    function fitWidth() {
      const viewport = document.getElementById('pagesViewport');
      const availWidth = viewport.clientWidth - 48;
      if (availWidth > 200) {
        const percent = Math.round((availWidth / 595) * 100);
        setExactZoom(percent);
      }
    }

    function switchTab(fileName) {
      activeFile = fileName;
      document.getElementById('currentFileNameBadge').innerText = fileName;

      if (fileName === 'main.tex') {
        document.getElementById('tabMainTex').className = 'px-3 py-1.5 bg-[#181825] text-blue-400 font-mono text-[11px] font-semibold rounded-t-md border-t-2 border-blue-500 flex items-center gap-1.5 transition cursor-pointer';
        document.getElementById('tabBib').className = 'px-3 py-1.5 text-gray-400 hover:text-gray-200 font-mono text-[11px] rounded-t-md flex items-center gap-1.5 transition cursor-pointer';
      } else {
        document.getElementById('tabBib').className = 'px-3 py-1.5 bg-[#181825] text-blue-400 font-mono text-[11px] font-semibold rounded-t-md border-t-2 border-blue-500 flex items-center gap-1.5 transition cursor-pointer';
        document.getElementById('tabMainTex').className = 'px-3 py-1.5 text-gray-400 hover:text-gray-200 font-mono text-[11px] rounded-t-md flex items-center gap-1.5 transition cursor-pointer';
      }

      document.getElementById('latexCode').value = fileContents[fileName] || '';
      updateLineNumbers();
    }

    function updateLineNumbers() {
      const code = document.getElementById('latexCode').value;
      const lines = code.split('\\n');
      document.getElementById('lineNumbers').innerHTML = lines.map((_, i) => i + 1).join('<br>');
      document.getElementById('lineCount').innerText = `Lines: ${lines.length}`;
    }

    function syncScroll() {
      const textarea = document.getElementById('latexCode');
      document.getElementById('lineNumbers').scrollTop = textarea.scrollTop;
    }

    async function triggerCompile(isAuto = false) {
      if (isCompiling) {
        pendingCompile = true;
        return;
      }
      isCompiling = true;
      pendingCompile = false;

      const btn = document.getElementById('recompileBtn');
      const badge = document.getElementById('statusBadge');
      const statusText = document.getElementById('statusText');
      const timeReadout = document.getElementById('compileTime');
      const progressLine = document.getElementById('compileProgressLine');
      const livePill = document.getElementById('liveCompilingPill');

      btn.disabled = true;
      statusText.innerText = "Compiling...";
      badge.className = "flex items-center space-x-1.5 text-xs text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-500/20";
      progressLine.classList.remove('hidden');
      livePill.classList.remove('hidden');
      livePill.classList.add('flex');

      const currentCode = document.getElementById('latexCode').value;
      fileContents[activeFile] = currentCode;

      try {
        const res = await fetch(`${API_BASE}/api/compile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            project_id: currentProjectId, 
            code: currentCode,
            filename: activeFile
          })
        });

        const data = await res.json();
        if (data.success) {
          currentPdfBase64 = data.pdf_base64;
          await renderPdfFromBase64(currentPdfBase64);
          timeReadout.innerHTML = `&#10003; ${data.compile_time}s compile`;
          statusText.innerText = "Compiled successfully";
          badge.className = "flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20";
          dismissErrorDrawer();
        } else {
          statusText.innerText = "Syntax Notice";
          badge.className = "flex items-center space-x-1.5 text-xs text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20";
          showErrorDrawer(data.error);
        }
      } catch (err) {
        console.error("Local API compile error:", err);
        statusText.innerText = "Backend Offline";
        badge.className = "flex items-center space-x-1.5 text-xs text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20";
      } finally {
        isCompiling = false;
        btn.disabled = false;
        progressLine.classList.add('hidden');
        livePill.classList.add('hidden');
        livePill.classList.remove('flex');

        if (pendingCompile) {
          pendingCompile = false;
          triggerCompile(true);
        }
      }
    }

    function showErrorDrawer(errText) {
      const drawer = document.getElementById('errorDrawer');
      const textElem = document.getElementById('errorDrawerText');
      textElem.innerText = errText || "LaTeX Syntax / Compilation Warning";
      drawer.classList.remove('hidden');
    }

    function dismissErrorDrawer() {
      const drawer = document.getElementById('errorDrawer');
      drawer.classList.add('hidden');
    }

    async function exportDownloads(type) {
      exportDownloadsForProj(currentProjectId, type);
    }

    async function exportDownloadsForProj(projId, type) {
      lastExportedType = type;
      try {
        const res = await fetch(`${API_BASE}/api/projects/${projId}/export-downloads`, {
          method: 'POST'
        });
        const data = await res.json();

        const downloadUrl = `${API_BASE}/api/projects/${projId}/download/${type}`;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = type === 'zip' ? `${projId}_overleaf.zip` : `${projId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        if (data.success) {
          showToast(
            type === 'zip' ? "Overleaf ZIP Saved to Downloads!" : "PDF Saved to Downloads!",
            type === 'zip' ? data.zip_file : data.pdf_file
          );
        }
      } catch (err) {
        const downloadUrl = `${API_BASE}/api/projects/${projId}/download/${type}`;
        window.open(downloadUrl, '_blank');
      }
    }

    function showToast(title, filePath) {
      const toast = document.getElementById('toastNotification');
      document.getElementById('toastTitle').innerText = title;
      document.getElementById('toastMsg').innerText = filePath;

      toast.classList.remove('translate-y-[-140px]', 'opacity-0', 'pointer-events-none');
      toast.classList.add('translate-y-0', 'opacity-100');

      setTimeout(() => {
        toast.classList.add('translate-y-[-140px]', 'opacity-0', 'pointer-events-none');
        toast.classList.remove('translate-y-0', 'opacity-100');
      }, 7000);
    }

    async function openInExplorer() {
      try {
        await fetch(`${API_BASE}/api/open-explorer`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: currentProjectId, file_type: lastExportedType })
        });
      } catch (err) {
        console.error(err);
      }
    }

    async function switchProject(projId) {
      currentProjectId = projId;
      updateStudioProjectHeader();

      try {
        const url = new URL(window.location);
        url.searchParams.delete('view');
        url.searchParams.set('project', projId);
        window.history.replaceState({}, '', url);
      } catch (e) {}

      const statusText = document.getElementById('statusText');
      statusText.innerText = `Loading ${projId}...`;

      try {
        const res = await fetch(`${API_BASE}/api/projects/${projId}`);
        const data = await res.json();
        
        fileContents["main.tex"] = data.code || '';
        fileContents["references.bib"] = data.bib_code || '';
        document.getElementById('latexCode').value = fileContents[activeFile];

        currentPdfBase64 = data.pdf_base64 || '';
        await renderPdfFromBase64(currentPdfBase64);
        updateLineNumbers();

        statusText.innerText = "Ready";
      } catch (err) {
        console.error("Failed to load project:", err);
        statusText.innerText = "Error loading project";
      }
    }

    function openNewProjectModal() {
      document.getElementById('newProjectModal').classList.remove('hidden');
      document.getElementById('newProjectModal').classList.add('flex');
      setTimeout(() => document.getElementById('newProjName').focus(), 50);
    }

    function closeNewProjectModal() {
      document.getElementById('newProjectModal').classList.add('hidden');
      document.getElementById('newProjectModal').classList.remove('flex');
    }

    async function submitNewProject() {
      const name = document.getElementById('newProjName').value.trim();
      const template = document.getElementById('newProjTemplate').value;
      if (!name) return alert("Please enter a project name");

      const btn = document.getElementById('submitNewProjBtn');
      btn.disabled = true;
      btn.innerText = "Creating...";

      try {
        const res = await fetch(`${API_BASE}/api/projects/new`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, template })
        });
        const data = await res.json();
        
        await fetchProjectsList();
        closeNewProjectModal();
        await switchToStudioView(data.id);
        showToast("New Project Created!", data.name);
      } catch (err) {
        alert("Failed to create project: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerText = "Create & Open";
      }
    }

    function copyCode() {
      const code = document.getElementById('latexCode').value;
      navigator.clipboard.writeText(code).then(() => {
        const btnText = document.getElementById('copyBtnText');
        btnText.innerText = 'Copied!';
        setTimeout(() => { btnText.innerText = 'Copy'; }, 2000);
      });
    }

    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""

    rendered_html = html_template.replace("__CURRENT_PROJ_ID__", json.dumps(project_id))
    rendered_html = rendered_html.replace("__PROJECTS_LIST__", json.dumps(projects))
    rendered_html = rendered_html.replace("__PDF_BASE64__", json.dumps(pdf_base64))
    rendered_html = rendered_html.replace("__MAIN_TEX__", json.dumps(tex_code))
    rendered_html = rendered_html.replace("__REF_BIB__", json.dumps(bib_code))
    rendered_html = rendered_html.replace("__PDF_VIEWER_CSS__", pdf_css_content)
    rendered_html = rendered_html.replace("__PDF_JS_CORE__", pdf_js_content)
    rendered_html = rendered_html.replace("__INLINED_WORKER_SOURCE__", json.dumps(pdf_worker_content))

    target_paths = []
    if output_path:
        target_paths.append(output_path)
    
    # 1. Scripts dir internal copy
    target_paths.append(SCRIPTS_DIR / "latex_studio.html")

    # 2. Workspace root / Current Working Directory (so user can open full browser view from their project folder!)
    cwd_html = Path.cwd() / "latex_studio.html"
    if cwd_html not in target_paths:
        target_paths.append(cwd_html)

    # 3. Active project directory (if specific project)
    if project_id and (PROJECTS_ROOT / project_id).exists():
        proj_html = PROJECTS_ROOT / project_id / "latex_studio.html"
        if proj_html not in target_paths:
            target_paths.append(proj_html)

    # 4. User's real Downloads directory
    dl_dir = get_downloads_dir()
    dl_html = dl_dir / "latex_studio.html"
    if dl_html not in target_paths:
        target_paths.append(dl_html)

    for tp in target_paths:
        tp.parent.mkdir(parents=True, exist_ok=True)
        with open(tp, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        print(f"Built HTML successfully to {tp} ({len(rendered_html)} bytes)")

        # If writing to an Antigravity brain conversation directory, automatically create .metadata.json!
        if "brain" in str(tp):
            meta_path = tp.parent / f"{tp.name}.metadata.json"
            meta_content = {
                "summary": "Interactive LaTeX Studio Workspace (Real-time XeTeX Preview, Selectable Text Layer & Projects Dashboard)",
                "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "userFacing": True
            }
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta_content, mf, indent=2)
            print(f"Registered Antigravity artifact metadata at {meta_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p", default=None)
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    out_p = Path(args.output) if args.output else None
    build(project_id=args.project, output_path=out_p)
