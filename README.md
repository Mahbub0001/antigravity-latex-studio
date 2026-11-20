# LaTeX Studio for Google Antigravity

A local LaTeX workspace and Overleaf companion plugin designed for Antigravity. Features instant Tectonic XeTeX compilation, an inlined PDF.js vector preview with full text selection, real-time live typing synchronization, and an Overleaf-style projects dashboard.

## Features

- **Split-Screen Studio**: Left-pane code editor (`main.tex`, `references.bib`, `figures/`) and right-pane live vector PDF preview.
- **Selectable Vector Text**: Native PDF.js text layer enabling character-accurate mouse text selection, copy-pasting, and document search.
- **Instant Tectonic XeTeX**: Local, reproducible PDF compilation in ~0.5s.
- **Reactive Live Sync**: Debounced auto-compilation while editing without manual recompile triggers.
- **Projects Dashboard**: Full project management (create, rename, duplicate, delete).
- **Workspace Standalone HTML**: Automatically drops `latex_studio.html` directly into the current workspace for full-window browser viewing.
- **Dynamic System Downloads**: Automatically saves PDFs and clean Overleaf-ready ZIP bundles into the user's default system Downloads folder.

## Installation in Antigravity

In any Antigravity conversation, run the following setup prompt:

```markdown
Install the LaTeX Studio plugin for Antigravity:
1. Clone repository:
   git clone https://github.com/Mahbub0001/antigravity-latex-studio ~/.gemini/config/plugins/latex-studio
2. Install Python dependencies:
   pip install fastapi uvicorn pydantic pypdfium2 requests
3. Start the background service:
   python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/ensure_server.py
4. Build the workspace interface:
   python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/build_ui.py
5. Open [LaTeX Studio](sidecar://latex-studio/studio/) in the side panel.
```

## License

MIT License. Created by Mahbub Ul Alam Bhuiyan.
