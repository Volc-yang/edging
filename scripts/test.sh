#!/usr/bin/env bash
# Edge World unified verification entry point.
#
# Usage:
#   ./scripts/test.sh              Python tests + edging structural validation
#   ./scripts/test.sh --parity     also run the Godot <-> UE5 parity gate
#   ./scripts/test.sh --all        everything, including the UE5 commandlet
#   ./scripts/test.sh -q           quiet: only print the summary
#
# Exit code is non-zero if any selected gate fails.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RUN_PARITY=0
RUN_UE5=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --parity) RUN_PARITY=1 ;;
    --all)    RUN_PARITY=1; RUN_UE5=1 ;;
    -q|--quiet) QUIET=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

PYTHON="python3"
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
fi

FAILED=0
pass() { printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAILED=1; }
info() { [ "$QUIET" -eq 1 ] || printf '  ....  %s\n' "$1"; }

echo "Edge World verification  (python: $PYTHON)"

# ---------------------------------------------------------------- gate 1
echo "[1/4] Python test suite"
if OUT="$("$PYTHON" -m unittest discover tests 2>&1)"; then
  pass "$(printf '%s' "$OUT" | grep -E '^Ran ' || echo 'unit tests ran')"
else
  fail "python tests"
  printf '%s\n' "$OUT" | tail -30
fi

# ---------------------------------------------------------------- gate 2
echo "[2/4] edging 64D/384 structural validation"
if command -v ruby >/dev/null 2>&1; then
  if OUT="$(cd "$REPO_ROOT/edging" && ruby bin/validate_spacetime_abstractions.rb --complete 2>&1)"; then
    pass "$(printf '%s' "$OUT" | tail -1)"
  else
    fail "edging structural validation"
    printf '%s\n' "$OUT" | tail -20
  fi
else
  info "ruby not installed - skipped"
fi

# ---------------------------------------------------------------- gate 3
echo "[3/4] Godot <-> UE5 parity gate"
if [ "$RUN_PARITY" -eq 1 ]; then
  if OUT="$("$PYTHON" tools/validate_godot_ue5_parity.py 2>&1)"; then
    if printf '%s' "$OUT" | grep -q '"status": "match"'; then
      pass "status: match"
    else
      fail "parity status is not match"
      printf '%s\n' "$OUT" | tail -30
    fi
  else
    fail "parity tool errored"
    printf '%s\n' "$OUT" | tail -30
  fi
else
  info "skipped (pass --parity or --all to enable)"
fi

# ---------------------------------------------------------------- gate 4
echo "[4/4] UE5 headless contract check"
UE5_PROJECT="${UE5_PROJECT:-/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE}"
UE5_CMD="${UE5_CMD:-/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd}"
if [ "$RUN_UE5" -eq 1 ]; then
  if [ -x "$UE5_CMD" ] && [ -d "$UE5_PROJECT" ]; then
    if OUT="$(EDGEWORLD_CHAPTER_ONE_JSON="$REPO_ROOT/models/chapter_one_snapshot.json" \
              "$UE5_CMD" "$UE5_PROJECT/EdgeWorldUE.uproject" \
              -run=EdgeWorldSnapshot -unattended -nop4 -nullrhi 2>&1)"; then
      if printf '%s' "$OUT" | grep -q 'EDGEWORLD_UE_CHAPTER_ONE_VALID'; then
        pass "$(printf '%s' "$OUT" | grep -o 'EDGEWORLD_UE_CHAPTER_ONE_VALID.*' | head -1)"
      else
        fail "commandlet ran but did not report a valid snapshot"
      fi
    else
      fail "UE5 commandlet exited non-zero"
      printf '%s\n' "$OUT" | tail -20
    fi
  else
    info "UE5 engine or project not present on this machine - skipped"
  fi
else
  info "skipped (pass --all to enable; requires UE 5.8)"
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL SELECTED GATES PASSED"
else
  echo "SOME GATES FAILED"
fi
exit "$FAILED"
