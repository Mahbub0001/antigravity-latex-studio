# LaTeX Studio for Google Antigravity

LaTeX Studio is a local LaTeX workspace plugin built specifically for Google Antigravity. It provides real-time XeTeX compilation, an inlined PDF preview with selectable text, debounced live editing, and a project dashboard.

## Key Capabilities

- **Real-Time XeTeX Compilation**: Uses the Tectonic engine for fast local rendering without requiring a full TeX installation.
- **Selectable Vector PDF**: Uses PDF.js to render PDF pages with an active text layer, allowing text selection, copying, and search.
- **Live Sync**: Debounced automatic compilation while typing in the editor.
- **Project Dashboard**: Manage multiple LaTeX projects directly from the web interface.
- **Dual Display**: Operates inside Antigravity's side panel or as a standalone file in your workspace.
- **Direct Exports**: Saves compiled PDFs and ZIP archives directly to the system Downloads folder.

## Setup in Antigravity

Paste this instruction into any Antigravity session:

```markdown
Install the LaTeX Studio plugin for Antigravity from GitHub:
Repository: https://github.com/Mahbub0001/antigravity-latex-studio

Instructions:
1. Clone to ~/.gemini/config/plugins/latex-studio
2. Install dependencies: pip install fastapi uvicorn pydantic pypdfium2 requests
3. Ensure Tectonic is available on the system.
4. Start the server daemon: python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/ensure_server.py
5. Build the interface: python ~/.gemini/config/plugins/latex-studio/skills/latex-studio/scripts/build_ui.py
6. Open [LaTeX Studio](sidecar://latex-studio/studio/) in the side panel.
```

## Shortcuts

- `Ctrl + Enter`: Recompile document
- `Live Toggle`: Turn real-time compiling on or off
- `Zoom Buttons`: Adjust preview scale
