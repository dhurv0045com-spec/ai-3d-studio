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
- Blender scripts are generated with **DeepSeek R1** first (reasoning model via OpenRouter); if R1 is unavailable, the app falls back to the standard LLM. Server logs show `[R1]` / `[MODEL_B]` lines during generation.
- While it runs, watch:
  - **Progress bar + pipeline** (with ETA during Blender stage)
  - **Live Blender script** — expand **View Script** under the pipeline
  - **Live logs** (useful if a generation fails)

When finished, the viewer loads the new model and a **Model Loaded** action strip offers Refine, Variants, Save, and Share.

## Hand Gesture Control

Hand control is provided by `static/gesture-engine.js` (loaded by the studio page). Click **HAND** to turn on instantly — there is no blocking calibration screen on startup. Allow camera when the browser asks.

- **Open hand + move** → rotate / orbit the model
- **Pinch** (thumb + index) → zoom in/out
- **Fist** → pan the view
- **Peace sign** → cycle through model parts (if part gestures enabled)
- **Two hands** (optional in panel): spread/pinch distance = zoom

Use the small **Hand Control** panel (bottom-left) for sensitivity, camera preview, two-hand mode, and part gestures.

Turn off with **HAND** again (camera is released).

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
