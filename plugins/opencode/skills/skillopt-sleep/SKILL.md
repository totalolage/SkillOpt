---
name: skillopt-sleep
description: Use when the user asks OpenCode to sleep, self-improve, learn from sessions, consolidate memory, run SkillOpt-Sleep, dry-run, adopt, harvest, status, schedule, or review staged learned skills.
---

# SkillOpt-Sleep

Run SkillOpt-Sleep for the current OpenCode project.

Prefer MCP tools when available:

- `sleep_status`: read-only status
- `sleep_harvest`: inspect mined tasks
- `sleep_dry_run`: preview, stages nothing
- `sleep_run`: run and stage a proposal
- `sleep_adopt`: apply the latest staged proposal with backup

Always pass `source: "opencode"` and `project` as the current project path.
Default to `backend: "mock"` unless the user explicitly asks for real OpenCode
model calls, then use `backend: "opencode"`.

Shell fallback:

```bash
SKILLOPT_SLEEP_REPO=/path/to/SkillOpt \
bash /path/to/SkillOpt/plugins/run-sleep.sh \
  dry-run --project "$(pwd)" --source opencode --backend mock
```

Safety rules:

- Harvest is read-only and should never edit OpenCode's database.
- Proposals are staged under `.skillopt-sleep/staging/`; do not adopt without showing the validation result.
- OpenCode learned rules are staged for `.opencode/skills/skillopt-sleep-learned/SKILL.md`.
- Do not copy secrets, raw tool outputs, reasoning, file contents, or patches into messages.
- After adopting OpenCode skill changes, tell the user to restart OpenCode.
