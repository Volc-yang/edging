#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
APP_DIR="$ROOT/.artifacts/EdgeWorldPreview3D.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
EXECUTABLE="$MACOS/EdgeWorldPreview3D"
DEFAULT_JSON="$ROOT/../models/four_phase_4d_cast_1781927642799684000.json"

swift build --package-path "$ROOT"

mkdir -p "$MACOS"
mkdir -p "$RESOURCES"
cp "$ROOT/.build/debug/EdgeWorldPreview3D" "$EXECUTABLE"
cp "$DEFAULT_JSON" "$RESOURCES/default_cast.json"
chmod +x "$EXECUTABLE"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>EdgeWorldPreview3D</string>
  <key>CFBundleIdentifier</key>
  <string>com.edgeworld.preview3d</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>EdgeWorldPreview3D</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>14.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

printf 'APPL????' > "$CONTENTS/PkgInfo"
open "$APP_DIR"
