# LaTeX Studio Guidelines

Whenever the user asks to write, edit, format, compile, or view LaTeX documents, academic papers, reports, or Overleaf projects:

1. **SIDE PANEL DISPLAY (MANDATORY)**:
   - In Antigravity, to show the interactive LaTeX Studio tool directly in the side panel beside the chat:
     You **MUST** generate `latex_studio.html` in the current conversation's artifact directory:
     `<appDataDir>\brain\<conversation-id>\latex_studio.html`
     Run: `python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/build_ui.py --project <project_id> --output <artifact_dir>\latex_studio.html`
     *(This script automatically registers `latex_studio.html.metadata.json` with `userFacing: true`)*.
   - **WORKSPACE FULL BROWSER COPY**:
     `build_ui.py` automatically writes `latex_studio.html` into the user's active workspace folder (`<workspace>/latex_studio.html`) and system Downloads folder as well so the user can open it in full browser view.
   - **CRITICAL RULE**: DO NOT create any markdown summary or overview file with `UserFacing: true`! If you write an overview or plan, ALWAYS set `UserFacing: false` (or output directly in chat). If you set `UserFacing: true` on an `.md` file, Antigravity will replace the LaTeX Studio in the side panel with that markdown file!
   - In your chat response, ALWAYS include the clickable sidecar link:
     `[LaTeX Studio](sidecar://latex-studio/studio/)`
     and the artifact link `[latex_studio.html](file:///<artifact_dir>/latex_studio.html)` so the user can open it with one click.

2. **Workspace Location**:
   - Projects are stored under `<workspace_root>/projects/<project_name>/`.
   - Each project contains: `main.tex`, `references.bib`, and a `figures/` folder.
   - Any uploaded figures or images should be saved in `figures/` and referenced via `\includegraphics[...]{figures/<filename>}`.

3. **Server Lifecycle Management**:
   - The studio backend runs on `http://127.0.0.1:7357`.
   - If the server is offline, start it with `python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/ensure_server.py`.

4. **Instant XeTeX Compilation**:
   - Uses the standalone Tectonic XeTeX engine:
     `python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/compile.py --project <project_name>`
   - Compiles in ~0.3-0.5s into authentic vector PDFs.

5. **Exports & Downloads**:
   - PDFs and clean Overleaf-ready ZIP archives are exported directly to the user's system Downloads folder:
     `python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:7357/api/projects/<project_name>/export-downloads', method='POST'))"`
