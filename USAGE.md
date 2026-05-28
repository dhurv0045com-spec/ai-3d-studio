# Aurex AI 3D Studio — How to Use

## Open the Studio

- **Local**: start the server, then open `http://127.0.0.1:5000`
- **Hosted**: open the deployed URL (for example, `/app`)

## Create a Model (Text → 3D)

- **Describe what to build** in the prompt box (keep the noun clear):
  - Good: `spaceship, sleek fighter with cockpit canopy and twin engines`
  - Good: `laptop with keyboard, touchpad, bezel, hinge`
- **Pick a color**, **style**, and **complexity** (4–5 gives the best results).
- Click **GENERATE MODEL**.
- While it runs, watch:
  - **Progress bar + pipeline** (with ETA during Blender stage)
  - **Live Blender script** — expand **View Script** under the pipeline
  - **Live logs** (useful if a generation fails)

When finished, the viewer loads the new model and a **Model Loaded** action strip offers Refine, Variants, Save, and Share.

## Hand Gesture Engine v2 (Jarvis-Class)

Click **HAND** to enable. Allow camera permissions. On first use, show an **open palm** for ~2 seconds to calibrate (saved in your browser).

### Gesture vocabulary (10 gestures)

| Gesture | Hand pose | Action |
|---------|-----------|--------|
| **ORBIT** | Open palm (4+ fingers), move hand | Rotate/orbit the model with inertia |
| **ZOOM** | Pinch thumb + index | Precision zoom (physics-smooth) |
| **PAN** | Fist (0–1 fingers extended) | Pan camera target (shift focus point) |
| **PART_CYCLE** | Peace sign (index + middle) | Cycle focused model part |
| **INSPECT** | Point (index only) | Raycast highlight + mesh name tooltip |
| **WIREFRAME** | Rock on (index + pinky) | Toggle wireframe |
| **SAVE** | Thumbs up | Open save dialog |
| **FIT** | Full spread (all 5 fingers wide) | Fit camera to full model |
| **RESET** | Open palm + fast wave | Reset camera |
| **ROLL** | Open palm + wrist roll | Subtle roll-orbit |

### Two-hand mode

- **Both open**: orbit + twist between hands
- **Both pinch**: cinematic dolly zoom (+ subtle FOV)
- **Both fist**: 3D pan (X/Y/Z from hand depth)
- **Orbit + point**: one hand orbits, other inspects with crosshair tooltip

### UI while HAND is on

- **Gesture HUD** (bottom-left of viewport): emoji, gesture name, confidence bar
- **Control panel**: cheat sheet, sensitivity, inertia, preview, two-hand, part gestures
- **Camera preview** (bottom-right): skeleton overlay color-coded by gesture; click to expand
- **Recalibrate** anytime from the panel

Turn off with **HAND** again (camera released).

## Enhance Prompt

Use **Enhance** when your prompt is short. Generation also auto-enriches with:

1. **Structural hints** (vehicle, creature, furniture, etc.)
2. **Material hints** (from style + color)
3. **Complexity calibration** (part count guidance)
4. **Part naming directive** (minimum named Blender objects for part-focus)

## Generate from Image

Use **Generate from Image** to upload a reference image. The app extracts a text description and then generates a model from it.

## Variants

Enable **variants** before generating. When ready:

- Cards auto-rotate in mini-viewers
- Press **1**, **2**, **3** or arrow keys to select
- **Enter** confirms selection

## Save, History, and Folders

- **SAVE**: store the current model to your history (and Supabase if configured)
- **Folders**: organize models per folder
- **History**: reload any saved model into the viewer

## Share Links

- After generation finishes, use **Share** to copy a share link.
- Anyone with the link can open a public viewer page at `/share/<model_id>`.

## Export / Download

- Use the export/download actions to get the GLB (and other supported formats if enabled in your build).

## Best Results: Prompt Tips

- Put the **real object name** in the prompt (e.g. “spaceship”, “laptop”, “camera”).
- Add 5–10 concrete physical parts:
  - `wings, engines, cockpit canopy, landing gear, thrusters, panel seams`
- Use **Complexity 4–5** for professional results.
- For part-level hand control, describe part relationships:
  - `robot arm with shoulder joint, elbow actuator, wrist gimbal, gripper fingers`
