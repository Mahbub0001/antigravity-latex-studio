---
name: latex-studio
description: AI-assisted LaTeX workspace with real-time Tectonic XeTeX compilation, split-screen live A4 PDF preview, project templates (IEEE, ACM, Thesis, Report), and clean Overleaf-ready ZIP bundle export. Use whenever user works on LaTeX, scientific papers, Overleaf sync, or PDF generation.
---

# LaTeX Studio Skill

A full-fledged, local, AI-assisted LaTeX engineering environment inspired by OpenAI Prism and Overleaf.

## Key Capabilities

1. **Split-Screen Studio**: Left pane LaTeX code editor (`main.tex`, `references.bib`, `figures/`), right pane crisp A4 PDF preview rendered with 1% precision smooth zooming and real-time live auto-compile.
2. **Dedicated Projects Dashboard**: Overleaf-grade dashboard to manage, rename, duplicate, delete, and download all local LaTeX projects.
3. **Instant XeTeX Compilation**: Powered by standalone Tectonic 0.17 engine (compilation in ~0.3-0.5s with offline caching).
4. **Side Panel Integration**: Seamlessly displays directly inside Antigravity's auxiliary side panel.

## Mandatory Side Panel Display Instructions

To ensure the interactive studio displays automatically in the Antigravity side panel:
1. Build the HTML artifact into the conversation artifact directory:
   ```bash
   python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/build_ui.py --project <project_slug> --output <artifact_dir>\latex_studio.html
   ```
2. **DO NOT** mark any markdown summary document (`.md`) with `UserFacing: true`. All markdown files must use `UserFacing: false` so that `latex_studio.html` remains the active artifact in the side panel!
3. Provide the clickable sidecar link in your response:
   `[LaTeX Studio](sidecar://latex-studio/studio/)`
