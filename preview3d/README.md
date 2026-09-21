# EdgeWorld Preview 3D

The package now contains two macOS executables:

- `EdgeWorldPreview3D`: the existing cast/voxel preview.
- `EdgeWorldChapterOne`: the Chapter One world frontend shared with Godot.

Open `Package.swift` in Xcode and select the `EdgeWorldChapterOne` scheme, or run:

```bash
swift run EdgeWorldChapterOne
```

This is a standalone macOS SwiftUI + SceneKit preview app for `edge-world` batch cast data.

## What it does

- Loads the sample `4x4x4x4` batch cast JSON.
- Renders the `256` samples as a 3D voxel volume with `4` time steps per cell.
- Treats the first three coordinates as space and the 4th coordinate as time, not as a global spatial axis.
- Uses the `changed` hexagram as the next-time hexagram inside each cell.
- Lets you rotate, zoom, click voxels, and switch color modes.
- Interprets dimensions as `1^1` point, `1^2` plane, `1^3` cube, and `changed` as next-time state.

## Run

To build the app bundle and launch it with `open`:

```bash
./open_preview3d.command
```

To load a different batch file, use the `Open JSON` button in the side panel after launch.
Preview-compatible 3D volume files can be generated with:

```bash
./.venv/bin/python tools/render_cast_volume_3d.py
```

## Interaction

- Drag to orbit the camera.
- Scroll to zoom.
- Click a voxel to inspect its cast details in the side panel.
- Use the time picker to isolate one time step or show all layers.
