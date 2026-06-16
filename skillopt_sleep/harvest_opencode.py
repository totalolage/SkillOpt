"""SkillOpt-Sleep OpenCode session harvesting.

Reads OpenCode's local SQLite database read-only and normalizes sessions into
``SessionDigest`` records. It deliberately avoids copying reasoning, tool
inputs/outputs, file contents, or patch contents.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

from skillopt_sleep.harvest import _detect_feedback, _is_meta_prompt, _project_matches
from skillopt_sleep.harvest_codex import _dedup, _sanitize_text, _sanitize_tool_name
from skillopt_sleep.types import SessionDigest


def _connect_readonly(path: str) -> sqlite3.Connection:
    uri = "file:" + quote(os.path.abspath(os.path.expanduser(path))) + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _loads(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _ms_to_iso(value: Any) -> str:
    try:
        n = float(value)
    except Exception:
        return ""
    if n <= 0:
        return ""
    if n > 10_000_000_000:
        n /= 1000.0
    return datetime.fromtimestamp(n, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_to_ms(value: Optional[str]) -> int:
    if not value:
        return 0
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def _text_part(data: Dict[str, Any]) -> str:
    if data.get("type") != "text" or data.get("synthetic") or data.get("ignored"):
        return ""
    text = data.get("text")
    return text if isinstance(text, str) else ""


def _tool_name(data: Dict[str, Any]) -> str:
    if data.get("type") != "tool":
        return ""
    name = data.get("tool")
    return _sanitize_tool_name(name) if isinstance(name, str) and name else ""


def _file_values(value: Any) -> Iterable[str]:
    if isinstance(value, str) and value:
        yield value
    elif isinstance(value, dict):
        for key in ("path", "file", "filename", "name"):
            item = value.get(key)
            if isinstance(item, str) and item:
                yield item
    elif isinstance(value, list):
        for item in value:
            yield from _file_values(item)


def _files_from_part(data: Dict[str, Any]) -> List[str]:
    kind = data.get("type")
    paths: List[str] = []
    if kind == "patch":
        paths.extend(_file_values(data.get("files")))
    elif kind == "file":
        source = data.get("source")
        if isinstance(source, dict):
            paths.extend(_file_values(source.get("path")))
        paths.extend(_file_values(data.get("filename")))
    return [p.replace("\x00", "")[:500] for p in paths if p]


def digest_opencode_session(conn: sqlite3.Connection, session_id: str) -> Optional[SessionDigest]:
    row = conn.execute(
        """
        SELECT s.id, s.directory, s.time_created, s.time_updated, p.worktree
        FROM session s
        LEFT JOIN project p ON p.id = s.project_id
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    sid, directory, created, updated, worktree = row
    project = directory or worktree or ""

    messages = conn.execute(
        "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created, id",
        (session_id,),
    ).fetchall()
    parts_by_message: Dict[str, List[Dict[str, Any]]] = {}
    for msg_id, raw in conn.execute(
        "SELECT message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
        (session_id,),
    ):
        parts_by_message.setdefault(str(msg_id), []).append(_loads(raw))

    user_prompts: List[str] = []
    assistant_finals: List[str] = []
    tools: List[str] = []
    files: List[str] = []
    feedback: List[str] = []
    n_user = 0
    n_asst = 0

    for msg_id, raw_msg in messages:
        role = str(_loads(raw_msg).get("role", ""))
        for part in parts_by_message.get(str(msg_id), []):
            tool = _tool_name(part)
            if tool:
                tools.append(tool)
            files.extend(_files_from_part(part))

            text = _sanitize_text(_text_part(part))
            if not text or _is_meta_prompt(text):
                continue
            if role == "user":
                n_user += 1
                user_prompts.append(text)
                feedback.extend(_detect_feedback(text))
            elif role == "assistant":
                n_asst += 1
                assistant_finals.append(text)

    if n_user == 0 and n_asst == 0:
        return None

    return SessionDigest(
        session_id=str(sid),
        project=project,
        started_at=_ms_to_iso(created),
        ended_at=_ms_to_iso(updated or created),
        user_prompts=user_prompts,
        assistant_finals=assistant_finals[-5:],
        tools_used=_dedup(tools),
        files_touched=_dedup(files)[:20],
        feedback_signals=feedback,
        n_user_turns=n_user,
        n_assistant_turns=n_asst,
        raw_path=f"opencode://{sid}",
    )


def harvest_opencode(
    db_path: str,
    *,
    scope: str = "all",
    invoked_project: str = "",
    since_iso: Optional[str] = None,
    limit: int = 0,
) -> List[SessionDigest]:
    path = os.path.expanduser(db_path or "")
    if not path or not os.path.exists(path):
        return []
    since_ms = _iso_to_ms(since_iso)
    sql = "SELECT id FROM session WHERE COALESCE(time_updated, time_created, 0) >= ? ORDER BY time_updated DESC"
    params: list[Any] = [since_ms]

    out: List[SessionDigest] = []
    try:
        with _connect_readonly(path) as conn:
            for (session_id,) in conn.execute(sql, params):
                digest = digest_opencode_session(conn, str(session_id))
                if digest is None:
                    continue
                if scope == "invoked" and invoked_project and not _project_matches(
                    digest.project, "invoked", invoked_project
                ):
                    continue
                out.append(digest)
                if limit and len(out) >= limit:
                    break
    except sqlite3.Error:
        return []
    return out
