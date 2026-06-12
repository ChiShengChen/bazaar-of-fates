#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Re-sync the divination MATH from the interview monorepo into this standalone
# 算命 repo. Single source of truth = the monorepo; this pulls only the pure
# 排盤/起卦 engine cores, their author prompts, and the pure chart renderers,
# renames the interview-style taskNN_* packages to real names, and rewrites the
# only two cross-engine import patterns.
#
# It NEVER touches the 算命 product shell that is native to this repo:
#   fortune/birth/  fortune/api/  fortune/interpret/  fortune/shared/  web/app/*
# Those are hand-written here and own the birth-input + reading product.
#
# Usage:  scripts/sync_from_main.sh [path-to-monorepo]
#   default monorepo: ~/Desktop/威鯨面試_LLMEng
# ---------------------------------------------------------------------------
set -euo pipefail

MAIN="${1:-$HOME/Desktop/威鯨面試_LLMEng}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ENG="$HERE/fortune/engines"
PROMPTS="$HERE/prompts"
CHARTS="$HERE/web/app/_charts"

[ -d "$MAIN" ] || { echo "✗ monorepo not found: $MAIN" >&2; exit 1; }
echo "→ syncing from $MAIN"
mkdir -p "$CHARTS"

# name : taskNN_dir : space-separated core engine files (under pipeline/)
ROWS=(
  "astrology:task25_astro:astro.py"
  "iching:task26_meihua:iching.py"
  "bazi:task27_bazi:bazi.py"
  "ziwei:task28_ziwei:ziwei_core.py ziwei.py"
  "suimei:task29_suimei:suimei.py"
  "qizheng:task30_qizheng:qizheng.py"
  "tieban:task31_tieban:tieban.py"
  "qimen:task32_qimen:qimen.py"
  "liuren:task33_liuren:liuren.py"
  "taiyi:task34_taiyi:taiyi.py"
  "jyotish:task35_jyotish:jyotish.py"
)

rewrite_imports() {
  # the only two cross-engine imports that exist in the pure cores
  #   from task27_bazi.pipeline import bazi as B  ->  from fortune.engines.bazi import bazi as B
  #   from task25_astro.pipeline import astro as A ->  from fortune.engines.astrology import astro as A
  local f="$1"
  perl -0pi -e 's/from task27_bazi\.pipeline import bazi/from fortune.engines.bazi import bazi/g' "$f"
  perl -0pi -e 's/from task25_astro\.pipeline import astro/from fortune.engines.astrology import astro/g' "$f"
  perl -0pi -e 's/from task28_ziwei\.pipeline import ziwei_core/from fortune.engines.ziwei import ziwei_core/g' "$f"
}

for row in "${ROWS[@]}"; do
  name="${row%%:*}"; rest="${row#*:}"; task="${rest%%:*}"; files="${rest#*:}"
  dst="$ENG/$name"
  mkdir -p "$dst"
  : > "$dst/__init__.py"
  for f in $files; do
    src="$MAIN/$task/pipeline/$f"
    [ -f "$src" ] || { echo "  ⚠ missing $src — skipped"; continue; }
    cp "$src" "$dst/$f"
    rewrite_imports "$dst/$f"
    echo "  ✓ engine  $name/$f"
  done
  # author prompt(s) → prompts/<name>/  (monorepo prompts/<taskNN>/)
  pdir="$MAIN/prompts/$task"
  if [ -d "$pdir" ]; then
    mkdir -p "$PROMPTS/$name"
    cp "$pdir"/*.md "$PROMPTS/$name/" 2>/dev/null && echo "  ✓ prompt  $name/"
  fi
done

# NOTE: the SVG chart renderers in web/app/_charts/ (StarChart/RashiChart/QizhengChart)
# are now NATIVE to this repo — they carry 算命-only overlays (house spokes, transit
# 行運 outer ring, synastry 合盤 bi-wheel) the monorepo's trading charts don't have, so
# sync deliberately does NOT overwrite them.

echo "✓ sync complete. Engines: $(ls "$ENG")"
echo "  (product shell — birth/, api/, interpret/, shared/, web pages — is native, untouched.)"
