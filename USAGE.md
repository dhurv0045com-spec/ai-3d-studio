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
  - **Progress bar + pipeline**
  - **Live logs** (useful if a generation fails)

When finished, the viewer loads the new model and you can:
- **Rotate**: click-drag (or touch-drag)
- **Zoom**: mouse wheel / trackpad / pinch
- Use viewer buttons:
  - **RESET**: reset camera
  - **AUTO**: auto rotate
  - **WIRE**: wireframe mode
  - **HAND**: optional hand-gesture control (see below)

## Hand Gesture Control (Optional)

- Click **HAND** to enable.
- Allow camera permissions.
- **1 hand (Jarvis-style controls)**:
  - **Open hand** = cinematic rotate/orbit
  - **Pinch (thumb + index)** = precision zoom
  - **Fist** = pan/shift camera target (like pro 3D viewport)
  - **Peace sign** = cycle through model parts (part focus mode)
- **2 hands** (if enabled in hand panel):
  - Move both hands (midpoint) = smooth pan
  - Increase/decrease hand distance = cinematic zoom
  - Twist hand pair angle = subtle orbit adjustment
- **Part gestures toggle** in hand panel:
  - ON: peace sign cycles and focuses parts
  - OFF: disables part focus and returns full-model view

Turn it off anytime by clicking **HAND** again (camera is released).

## Enhance Prompt

Use **Enhance** when your prompt is short. It expands your prompt into a more “3D-ready” description before generation.

The studio now also enriches generation input with:
- selected style
- complexity level
- extra part-detail instructions (when prompt is too generic)

This improves part separation, silhouette quality, and overall model realism.

## Generate from Image

Use **Generate from Image** to upload a reference image. The app extracts a text description and then generates a model from it.

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
- For best part-level control, describe part relationships:
  - `robot arm with shoulder joint, elbow actuator, wrist gimbal, gripper fingers`

