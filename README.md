# AI 3D Studio — Setup & Usage Guide

## Project Structure

```
ai-3d-project/
├── index.html          ← Three.js viewer (open in browser)
├── generate_model.py   ← AI backend (reads prompts, runs Blender, exports .glb)
├── server.py           ← Simple HTTP server (bridges browser ↔ backend)
├── state.json          ← Shared state file (prompt + status)
└── rocket.glb          ← Generated 3D model (created automatically)
```

---

## Quick Start

### Step 1 — Install Requirements

- **Blender 3.x or 4.x**: https://www.blender.org/download/
- **Python 3.8+**: https://www.python.org/

Make sure `blender` is on your PATH, or set the environment variable:
```bash
# Windows
set BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.0\blender.exe

# macOS / Linux
export BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender
```

---

### Step 2 — Start the HTTP Server

Open **Terminal 1**:
```bash
cd ai-3d-project
python server.py
```
You should see:
```
  URL : http://localhost:8000
```

---

### Step 3 — Start the Generation Backend

Open **Terminal 2**:
```bash
cd ai-3d-project
python generate_model.py
```
It will poll state.json every second for new prompts.

---

### Step 4 — Open the Browser

Visit: **http://localhost:8000**

Type a prompt like:
- `create a red rocket with big wings`
- `make a blue spaceship`
- `build a golden tower`
- `generate a green robot`

Click **GENERATE** and watch the model appear!

---

## How It Works

```
Browser (index.html)
   │
   │  POST /save-state  { "prompt": "...", "status": "pending" }
   ▼
server.py  ──writes──▶  state.json
                              │
                         generate_model.py (polling)
                              │  reads prompt
                              │  detects shape + color
                              │  writes blender_script.py
                              │  runs: blender --background --python script.py
                              │  Blender exports rocket.glb
                              │  writes state.json { "status": "done" }
                              ▼
Browser polls state.json every 1s
   │  sees "done"
   │  loads rocket.glb via Three.js GLTFLoader
   ▼
3D model appears in the viewer ✓
```

---

## Supported Shapes

| Keyword in prompt         | Shape generated        |
|--------------------------|------------------------|
| rocket, missile          | Rocket with 4 fins     |
| car, vehicle, truck      | Low-poly car           |
| tower, castle, building  | Stacked tower          |
| spaceship, ufo, saucer   | Flying saucer          |
| robot, android, mech     | Humanoid robot         |
| house, home, cottage     | House with roof        |
| plane, aircraft, jet     | Airplane               |
| pyramid, temple          | Egyptian pyramid       |
| diamond, gem, crystal    | Gem shape              |
| tree, pine               | Layered pine tree      |

## Supported Colors

`red`, `green`, `blue`, `yellow`, `gold`, `white`, `black`, `orange`,
`purple`, `pink`, `cyan`, `silver`

## Size Modifiers

- `big`, `large`, `huge`, `giant` → larger fins/wings
- `small`, `tiny`, `mini` → smaller fins/wings

---

## Demo Mode (No Server)

If you just open `index.html` directly (without running server.py),
the viewer works in **Demo Mode**: it generates a preview shape
using Three.js geometry instead of Blender. No GLB file is needed.
Great for testing the UI!

---

## Troubleshooting

**"blender not found"**
→ Set BLENDER_PATH to the full path of your Blender executable.

**Model doesn't update**
→ Make sure server.py is running and generate_model.py is running.
→ Check Terminal 2 for Blender errors.

**Port 8000 in use**
→ Edit `server.py` and change `PORT = 8000` to another port (e.g. 8080).
