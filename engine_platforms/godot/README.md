# Godot frontend

Open `project.godot` with Godot 4.7 or run:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path engine_platforms/godot
```

The frontend reads `models/chapter_one_snapshot.json`. Its two run buttons invoke
the shared Python rule runtime, either with local Ollama or with the deterministic
fallback, and then reload the approved snapshot.
