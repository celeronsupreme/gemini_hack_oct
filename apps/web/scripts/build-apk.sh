#!/usr/bin/env bash
# Build the Android debug APK (Capacitor wrapper around dist/). Run from Git Bash:
#   bash apps/web/scripts/build-apk.sh http://<this-pc-lan-ip>:8000
# The API address is baked into the bundle, so rebuild when the PC's IP changes.
# Needs JAVA_HOME (JDK 21) and android/local.properties with sdk.dir; defaults to the portable install in
# %LOCALAPPDATA%/AndroidBuild used on the UI-seat machine.
set -euo pipefail
API_BASE="${1:?usage: build-apk.sh http://<lan-ip>:8000}"
WEB="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${LOCALAPPDATA:-}/AndroidBuild"
export JAVA_HOME="${JAVA_HOME:-$(cygpath -w "$TOOLS"/jdk-21*)}"
[ -f "$WEB/android/local.properties" ] || echo "sdk.dir=$(cygpath -m "$TOOLS/sdk")" > "$WEB/android/local.properties"
PNPM=pnpm; command -v pnpm.cmd >/dev/null && PNPM=pnpm.cmd

cd "$WEB"
CAP_BUILD=1 VITE_API_BASE="$API_BASE" VITE_USE_MOCK=0 $PNPM build
npx cap sync android
(cd android && ./gradlew assembleDebug --no-daemon -q)
echo "APK: $WEB/android/app/build/outputs/apk/debug/app-debug.apk (API $API_BASE)"
