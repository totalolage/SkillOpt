#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$HOME/.config/opencode"
CONFIG_FILE="$CONFIG_DIR/opencode.json"
SKILL_DIR="$CONFIG_DIR/skills/skillopt-sleep"

mkdir -p "$SKILL_DIR" "$CONFIG_DIR"
cp "$SCRIPT_DIR/skills/skillopt-sleep/SKILL.md" "$SKILL_DIR/SKILL.md"

python3 - "$CONFIG_FILE" "$REPO_ROOT" <<'PY'
import json
import os
import shutil
import sys

config_file, repo_root = sys.argv[1:]
server = {
    "type": "local",
    "command": ["python3", os.path.join(repo_root, "plugins", "copilot", "mcp_server.py")],
    "enabled": True,
    "env": {"SKILLOPT_SLEEP_REPO": repo_root},
}
command = {
    "description": "Run SkillOpt-Sleep for this OpenCode project.",
    "prompt": "Use the skillopt-sleep skill. Prefer MCP tools. Pass source=opencode and project as the current working directory.",
}

data = {"$schema": "https://opencode.ai/config.json"}
if os.path.exists(config_file):
    try:
        with open(config_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print(f"[sleep] {config_file} is not plain JSON; leaving it unchanged.")
        print("[sleep] Add this MCP block manually, using env (not environment):")
        print(json.dumps({"mcp": {"skillopt-sleep": server}}, indent=2))
        raise SystemExit(0)
    shutil.copy2(config_file, config_file + ".bak")

data.setdefault("$schema", "https://opencode.ai/config.json")
data.setdefault("mcp", {})["skillopt-sleep"] = server
data.setdefault("command", {})["sleep"] = command
with open(config_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f"[sleep] configured MCP in: {config_file}")
PY

echo "[sleep] installed OpenCode skill: $SKILL_DIR/SKILL.md"
echo "[sleep] restart OpenCode before using it."
