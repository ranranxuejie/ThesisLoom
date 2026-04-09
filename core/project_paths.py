from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

try:
    from send2trash import send2trash
except Exception:
    send2trash = None

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = WORKSPACE_ROOT / "projects"
ACTIVE_PROJECT_FILE = PROJECTS_DIR / ".active_project.json"
DEFAULT_PROJECT_NAME = "default"
SHARED_INPUTS_DIR = WORKSPACE_ROOT / "inputs"

# Workspace-level templates to clone when creating project files.
WORKSPACE_TEMPLATE_FILES = [
    "inputs/inputs.json",
    "inputs/existing_material.md",
    "inputs/existing_sections.md",
    "inputs/related_works.md",
    "inputs/revision_requests.md",
    "inputs/write_requests.md",
    "inputs/research_gaps.md",
]

# Fallback templates if source files are missing.
FALLBACK_TEMPLATES: Dict[str, str] = {
    "inputs/inputs.json": "{\n  \"topic\": \"\",\n  \"language\": \"English\",\n  \"model\": \"gemini-3.1-pro\",\n  \"max_review_rounds\": 3,\n  \"paper_search_limit\": 30,\n  \"openalex_api_key\": \"\",\n  \"ark_api_key\": \"\",\n  \"base_url\": \"http://localhost:8000/v1\",\n  \"model_api_key\": \"\",\n  \"auto_resume\": false\n}\n",
    "inputs/existing_material.md": "# Existing Materials\n\n请在这里粘贴已有论文正文、实验记录或技术说明。\n",
    "inputs/existing_sections.md": "# Existing Sections\n\n请在这里粘贴已有章节（如摘要、引言、方法草稿）。\n",
    "inputs/related_works.md": "# Related Works\n\n请在这里补充检索后的相关工作综述。\n",
    "inputs/revision_requests.md": "# Manual Revision Instructions\n\n### GLOBAL\n- 在此填写全文改稿要求\n\n### SUB 2.1\n- 在此填写对具体小节的改稿要求\n",
    "inputs/write_requests.md": "# Write Requests\n\n请在这里补充你的写作要求、格式约束、审稿偏好。\n",
    "inputs/research_gaps.md": "# Research Gaps\n\n(Workflow will update this file.)\n",
}

REQUIRED_DIRS = [
    "inputs",
    "completed_history",
    "completed_history/snapshots",
    "completed_history/history",
]

REQUIRED_FILES = [
    "inputs/inputs.json",
    "inputs/existing_material.md",
    "inputs/existing_sections.md",
    "inputs/related_works.md",
    "inputs/revision_requests.md",
    "inputs/write_requests.md",
    "inputs/research_gaps.md",
]


def _safe_project_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+", "_", str(name or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or DEFAULT_PROJECT_NAME


def list_projects() -> List[str]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    names: List[str] = []
    for child in PROJECTS_DIR.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            names.append(child.name)
    names.sort()
    active_name = get_active_project_name()
    if active_name and active_name not in names:
        names.insert(0, active_name)
    if DEFAULT_PROJECT_NAME not in names:
        names.insert(0, DEFAULT_PROJECT_NAME)
    return names


def move_project_to_recycle_bin(name: str) -> Dict[str, object]:
    safe_name = _safe_project_name(name)
    if safe_name == DEFAULT_PROJECT_NAME:
        return {"ok": False, "message": "默认项目不可移至回收站"}

    project_root = (PROJECTS_DIR / safe_name).resolve()
    if (not project_root.exists()) or (not project_root.is_dir()):
        return {"ok": False, "message": f"项目不存在: {safe_name}"}

    if send2trash is None:
        return {
            "ok": False,
            "message": "缺少依赖 send2trash，无法移至回收站。请先安装该依赖。",
        }

    try:
        send2trash(str(project_root))
    except Exception as e:
        return {"ok": False, "message": f"移至回收站失败: {e}"}

    current_active = get_active_project_name()
    if current_active == safe_name:
        set_active_project(DEFAULT_PROJECT_NAME)
        current_active = get_active_project_name()

    return {
        "ok": True,
        "project_name": safe_name,
        "active_project": current_active,
    }


def _read_active_project_meta() -> Dict[str, str]:
    if not ACTIVE_PROJECT_FILE.exists():
        return {"name": DEFAULT_PROJECT_NAME, "root_path": ""}
    try:
        data = json.loads(ACTIVE_PROJECT_FILE.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("active project payload must be object")
        return {
            "name": _safe_project_name(str(data.get("name", DEFAULT_PROJECT_NAME))),
            "root_path": str(data.get("root_path", "") or data.get("root", "")).strip(),
        }
    except Exception:
        return {"name": DEFAULT_PROJECT_NAME, "root_path": ""}


def _resolve_project_root(name: str, root_path: Optional[str] = None) -> Path:
    raw_root = str(root_path or "").strip()
    if raw_root:
        root = Path(raw_root).expanduser()
        if not root.is_absolute():
            root = (WORKSPACE_ROOT / root).resolve()
        else:
            root = root.resolve()
        return root
    return (PROJECTS_DIR / _safe_project_name(name)).resolve()


def get_active_project_name() -> str:
    name = _read_active_project_meta().get("name", DEFAULT_PROJECT_NAME)
    return _safe_project_name(name)


def set_active_project(name: str, root_path: Optional[str] = None) -> str:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_project_name(name)
    resolved_root = _resolve_project_root(safe_name, root_path)
    payload: Dict[str, str] = {"name": safe_name}
    if str(root_path or "").strip():
        payload["root_path"] = str(resolved_root)

    ACTIVE_PROJECT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ensure_project_structure(resolved_root)
    return safe_name


def get_active_project_root() -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    meta = _read_active_project_meta()
    safe_name = _safe_project_name(meta.get("name", DEFAULT_PROJECT_NAME))
    root = _resolve_project_root(safe_name, meta.get("root_path", ""))
    ensure_project_structure(root)
    return root


def project_path(*parts: str) -> str:
    root = get_active_project_root()
    if not parts:
        return str(root)
    rel = Path(*parts)
    return str((root / rel).resolve())


def _copy_if_missing(src_rel: str, root: Path) -> None:
    src = (WORKSPACE_ROOT / src_rel).resolve()
    dst = (root / src_rel).resolve()
    if dst.exists():
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists() and src.is_file():
        shutil.copy2(str(src), str(dst))
        return

    fallback = FALLBACK_TEMPLATES.get(src_rel, "")
    dst.write_text(fallback, encoding="utf-8")


def _copy_dir_tree_if_missing(src_rel: str, root: Path) -> None:
    src_dir = (WORKSPACE_ROOT / src_rel).resolve()
    dst_dir = (root / src_rel).resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists() or (not src_dir.is_dir()):
        return

    for p in src_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(src_dir)
        target = dst_dir / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(p), str(target))


def ensure_project_structure(project_root: Path) -> None:
    root = Path(project_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    for rel_dir in REQUIRED_DIRS:
        (root / rel_dir).mkdir(parents=True, exist_ok=True)

    for rel_file in WORKSPACE_TEMPLATE_FILES:
        _copy_if_missing(rel_file, root)

    # Compatibility migration: carry over old user_requirements into write_requests.
    legacy_req = root / "inputs" / "user_requirements.md"
    new_req = root / "inputs" / "write_requests.md"
    if (not new_req.exists()) and legacy_req.exists():
        new_req.write_text(legacy_req.read_text(encoding="utf-8"), encoding="utf-8")

    # Compatibility migration: if old outputs/research_gaps exists, move to inputs.
    legacy_rg = root / "outputs" / "research_gaps.md"
    new_rg = root / "inputs" / "research_gaps.md"
    if (not new_rg.exists()) and legacy_rg.exists():
        new_rg.parent.mkdir(parents=True, exist_ok=True)
        new_rg.write_text(legacy_rg.read_text(encoding="utf-8"), encoding="utf-8")

    for rel_file in REQUIRED_FILES:
        target = root / rel_file
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(FALLBACK_TEMPLATES.get(rel_file, ""), encoding="utf-8")


def absolute_path_in_project(rel_path: str) -> str:
    rel = str(rel_path or "").strip().replace("\\", "/")
    return project_path(*[p for p in rel.split("/") if p])


def relative_to_project(abs_path: str) -> str:
    root = get_active_project_root()
    try:
        return str(Path(abs_path).resolve().relative_to(root).as_posix())
    except Exception:
        return str(abs_path)


def shared_input_path(*parts: str) -> str:
    if not parts:
        return str(SHARED_INPUTS_DIR.resolve())
    return str((SHARED_INPUTS_DIR / Path(*parts)).resolve())
