# SkillOpt-Sleep for OpenCode

OpenCode support has three pieces:

- a `skillopt-sleep` skill, installed into `~/.config/opencode/skills/`
- MCP tools (`sleep_status`, `sleep_dry_run`, `sleep_run`, `sleep_adopt`, `sleep_harvest`)
- native OpenCode session harvesting from `~/.local/share/opencode/opencode.db`

Install:

```bash
bash plugins/opencode/install.sh
```

Then quit and restart OpenCode. Config is loaded at startup.

Manual OpenCode config shape:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "skillopt-sleep": {
      "type": "local",
      "command": ["python3", "/abs/path/SkillOpt/plugins/copilot/mcp_server.py"],
      "enabled": true,
      "env": {
        "SKILLOPT_SLEEP_REPO": "/abs/path/SkillOpt"
      }
    }
  }
}
```

Useful shell fallback:

```bash
SKILLOPT_SLEEP_REPO=/abs/path/SkillOpt \
bash /abs/path/SkillOpt/plugins/run-sleep.sh \
  dry-run --project "$(pwd)" --source opencode --backend mock
```

Use `--backend opencode` only when you want live OpenCode model calls. `mock`
is deterministic and free.

OpenCode runs stage learned rules into the current project's
`.opencode/skills/skillopt-sleep-learned/SKILL.md`. They do not write
`CLAUDE.md` unless you pass `--memory-path` explicitly.
