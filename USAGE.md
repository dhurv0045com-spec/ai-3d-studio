# Aurex AI 3D Studio — User Guide

> Everything you need to know to create, control, share, and export 3D models.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Creating a Model (Text → 3D)](#creating-a-model-text--3d)
- [Creating from an Image](#creating-from-an-image)
- [Prompt Enhancement](#prompt-enhancement)
- [Multi-Variant Generation](#multi-variant-generation)
- [3D Viewer Controls](#3d-viewer-controls)
- [Hand Gesture Control](#hand-gesture-control)
- [Live Pipeline Visualizer](#live-pipeline-visualizer)
- [Saving & History](#saving--history)
- [Folders](#folders)
- [Sharing Models](#sharing-models)
- [Exporting & Downloading](#exporting--downloading)
- [Community Gallery](#community-gallery)
- [Prompt Tips & Best Practices](#prompt-tips--best-practices)
- [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Getting Started

| Access | URL |
|---|---|
| **Local** | Start the server → open `http://127.0.0.1:5000` |
| **Hosted** | Open the deployed URL (e.g., `https://aurexs3d.up.railway.app`) |

You'll land on the **animated login page**. Choose:
- **Sign in with Google** — full personalized experience with isolated history and folders.
- **Continue as Guest** — instant access, shared anonymous storage.

After login you're redirected to `/app`, the main studio interface.

---

## Creating a Model (Text → 3D)

1. **Type your prompt** in the text box — describe the object you want built.
2. **Pick a color** using the color picker.
3. **Select a style** (realistic, cartoon, low-poly, etc.).
4. **Set complexity** from 1 to 5 — higher values produce more detailed geometry with more named parts. **4–5 gives the best results.**
5. Click **GENERATE MODEL**.

### What happens under the hood

The system runs a **5-stage failover pipeline** to guarantee you always get a model:

| Stage | What It Does |
|---|---|
| **Cache Check** | If an identical prompt+color has been generated before, returns instantly. |
| **Gemini + Blender** | An LLM (DeepSeek R1 or Gemini Flash) writes a complete Blender Python script. Blender 4.2 executes it headlessly to produce a `.glb`. |
| **Shap-E** | If Blender fails, the neural Shap-E model generates geometry from text. |
| **Preset Library** | Falls back to hand-tuned preset scripts for 54 known object categories. |
| **Pure-Python Fallback** | Last resort — a zero-dependency GLB builder with 55 recognizable shapes. **Never returns empty.** |

The primary LLM is **DeepSeek R1** (a reasoning model via OpenRouter). Server logs show `[R1]` when it's used. If R1 is unavailable, the system cascades to **Gemini 2.0 Flash** (with 20-key auto-rotation) and finally **Groq** (LLaMA 3.3 70B).

### While it generates

- **Progress bar + pipeline stages** — watch each stage complete in real time with an ETA during Blender execution.
- **Live Blender Script** — expand the **"View Script"** section to see the AI-written Python code as it arrives.
- **Live Logs** — useful for debugging if something goes wrong.

When finished, the viewer loads the model and a **Model Loaded** action strip appears with **Refine**, **Variants**, **Save**, and **Share** buttons.

---

## Creating from an Image

1. Click **Generate from Image** (or the image upload icon).
2. Upload a JPG, PNG, or WebP reference photo (max 5 MB).
3. Gemini Vision analyzes the image and extracts a text description.
4. The description is automatically enhanced and fed into the generation pipeline.
5. You'll see both the extracted prompt and the enhanced version before generation begins.

---

## Prompt Enhancement

Use the **Enhance** button to expand a short prompt before generating. The enhancer adds:

| Enhancement | Example |
|---|---|
| **Structural hints** | Vehicle → wheels, chassis, body panels |
| **Material hints** | Metallic surface, glass canopy, rubber treads |
| **Complexity calibration** | Part count guidance matching your complexity slider |
| **Part naming directive** | Minimum number of named Blender objects for part-level gesture control |

You can also preview enhancement without generating by calling the enhance endpoint directly.

---

## Multi-Variant Generation

Enable **Variants** mode before generating to get three parallel interpretations:

| Variant | Description |
|---|---|
| **1 — Original** | Your prompt as-is |
| **2 — Top-down emphasis** | Viewed from above with emphasized top geometry |
| **3 — Stylized** | Exaggerated proportions and stylized details |

Each variant generates independently in parallel. When all three are ready:
- **Mini-viewer cards** auto-rotate to preview each result.
- Press **1**, **2**, **3** or use **arrow keys** to select.
- Press **Enter** to confirm your selection.

---

## 3D Viewer Controls

### Mouse

| Action | Control |
|---|---|
| **Orbit** | Left-click + drag |
| **Pan** | Right-click + drag, or Shift + left-click + drag |
| **Zoom** | Scroll wheel |

### Touch

| Action | Control |
|---|---|
| **Orbit** | One-finger drag |
| **Pan** | Two-finger drag |
| **Zoom** | Pinch |

---

## Hand Gesture Control

The gesture engine is powered by **MediaPipe Hands** via `gesture-engine.js`. Click the **HAND** button to activate — there is no blocking calibration screen; it starts instantly. Allow camera access when the browser asks.

### Gesture Reference

| Gesture | Action | Notes |
|---|---|---|
| 🖐️ **Open Palm + Move** | **Orbit** — smooth 3D rotation | Roll and yaw of your wrist contribute to rotation |
| ✊ **Closed Fist + Move** | **Pan** — smooth translation on all axes | Depth-aware: palm size modulates Z panning |
| 🤏 **Pinch (thumb + index)** | **Fine Zoom** | Palm width and Z-depth changes both contribute |
| 🙌 **Two Hands Framing** | **Scale Zoom** — change distance between palms | Requires two-hand mode enabled |
| ☝️ **Pointing Up** | **Reset Camera** — returns to default orbit | One-shot with 1.2s cooldown |
| ✌️ **Peace Sign** | **Cycle Parts** — focus on individual model parts | Requires part control enabled |

### Advanced Gesture Features

- **One Euro Filter** — Casiez et al. 2012 noise filter for silky-smooth landmark tracking.
- **Momentum & Inertia** — Camera motion continues smoothly after you stop moving, with configurable decay.
- **Adaptive Speed** — Sensitivity auto-scales based on camera distance to the model.
- **Dead Zone** — Small movements are ignored to prevent jitter.
- **Lost Hand Grace Period** — 350ms grace window prevents flickering when hand tracking briefly drops.

### Control Panel

Use the **Hand Control** panel (bottom-left) to adjust:
- **Sensitivity** — gesture responsiveness
- **Camera preview** — show/hide the camera feed with skeleton overlay
- **Two-hand mode** — enable/disable two-handed zoom
- **Part gestures** — enable/disable part-cycling with peace sign
- **Inertia** — enable/disable momentum after gesture release

Click **HAND** again to deactivate (camera is released).

---

## Live Pipeline Visualizer

During generation, the UI displays a **stage-by-stage pipeline visualization**:

```
[Enhance] → [LLM Script] → [Blender] → [Upload] → [Done]
    ✓           ✓          ⏳ 12s        ○          ○
```

Each stage shows:
- **Status** — completed (✓), in progress (⏳), or pending (○)
- **Elapsed time** in milliseconds
- **ETA** during the Blender execution stage

---

## Saving & History

- Click **SAVE** after generation to store the model in your personal history.
- Models are saved to:
  - **Supabase** (cloud — if configured) for persistent, cross-device access.
  - **Local per-user JSON** as a fallback.
- **History** panel shows all saved models — click any to reload it in the viewer.
- Each history entry records: prompt, color, service used, quality score, cloud URL, file size, and timestamp.

---

## Folders

Organize your models into folders:

| Action | How |
|---|---|
| **Create** | Click "New Folder" and enter a name |
| **Rename** | Right-click or use the rename option |
| **Delete** | Click the delete button (cannot delete "default") |
| **Move** | Save a model to a specific folder during save |

Default folders: `default`, `vehicles`, `creatures`, `buildings`, `misc`.

Folders are synced to Supabase per-user when authenticated.

---

## Sharing Models

1. After generation completes, click **Share**.
2. A public share link is copied to your clipboard: `https://your-app.domain/share/<model_id>`.
3. Anyone with the link can open a **public viewer page** with the embedded 3D model — no login required.

Share pages retrieve model data from Supabase and display it in a standalone Three.js viewer.

---

## Exporting & Downloading

| Format | How |
|---|---|
| **GLB** | Click **Download** — serves the raw `.glb` file as an attachment. |
| **OBJ** | Navigate to `/export/obj` — Blender converts the current GLB to Wavefront OBJ. Takes 5–15 seconds. |
| **FBX** | Navigate to `/export/fbx` — Blender converts to Autodesk FBX format. Takes 5–15 seconds. |

OBJ and FBX conversions run Blender headlessly with a temporary conversion script. The exported file is cleaned up after download.

---

## Community Gallery

The **Community Gallery** shows the latest 50 models generated across all users:

- Accessible at `/api/community` (JSON) or via the Gallery tab in the UI.
- Displays: prompt, color, service used, quality score, and creation time.
- Models include cloud URLs for instant preview.

---

## Prompt Tips & Best Practices

### Do This ✅

| Tip | Example |
|---|---|
| **Name the real object** | `"spaceship"`, `"laptop"`, `"medieval castle"` |
| **List 5–10 physical parts** | `"spaceship with cockpit canopy, twin engines, delta wings, landing gear, thrusters, panel seams"` |
| **Use Complexity 4–5** | Produces professional-grade geometry with many named parts |
| **Describe part relationships** | `"robot arm with shoulder joint, elbow actuator, wrist gimbal, gripper fingers"` |
| **Specify surface details** | `"brushed metal surface with rivets and panel lines"` |

### Avoid This ❌

| Mistake | Why |
|---|---|
| Vague prompts like `"something cool"` | LLM can't write specific geometry code |
| Abstract concepts like `"love"` or `"music"` | Need physical objects for 3D modeling |
| Extremely long prompts (100+ words) | The enhancer already adds detail — keep yours focused |

### Style + Color Synergy

- **Realistic** + muted colors → photorealistic materials
- **Cartoon** + bright colors → stylized, saturated models
- **Low-poly** + any color → faceted geometry with clean edges

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `1` / `2` / `3` | Select variant 1, 2, or 3 (during variant generation) |
| `←` / `→` | Navigate between variants |
| `Enter` | Confirm variant selection |

---

<div align="center">
  <sub><em>Aurex AI 3D Studio V8.0 — From words to worlds.</em></sub>
</div>
