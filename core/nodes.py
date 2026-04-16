import copy
import json
import os
import re
import time
from typing import Optional, Dict, Any, List
import requests
# 假设你的其他模块是这样组织的，请根据实际情况调整导入路径
from core.state import (
    PaperWriterState,
    serialize_guidance_catalog,
    serialize_review_catalog,
    resolve_inputs_path,
    build_output_paths,
    save_state_checkpoint,
)
# 假设 call_doubao 函数放在 utils 或 llm 模块中
from core.llm import call_llm
from core.prompts import PROMPT_TEMPLATE
from core.project_paths import project_path


def _append_workflow_event(level: str, message: str, **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "level": str(level),
        "message": str(message),
    }
    payload.update(extra)

    runtime_payload: Dict[str, Any] = {}
    runtime_path = project_path("completed_history", "workflow_runtime.json")
    try:
        if os.path.exists(runtime_path):
            with open(runtime_path, "r", encoding="utf-8") as f:
                raw_runtime = json.load(f)
            if isinstance(raw_runtime, dict):
                runtime_payload = raw_runtime
    except Exception:
        runtime_payload = {}

    runtime_status = str(runtime_payload.get("status", "")).strip()
    if runtime_status and (not str(payload.get("runtime_status", "")).strip()):
        payload["runtime_status"] = runtime_status

    runtime_phase = str(runtime_payload.get("phase", "")).strip()
    if runtime_phase and (not str(payload.get("phase", "")).strip()):
        payload["phase"] = runtime_phase

    runtime_node = str(runtime_payload.get("node", "")).strip()
    if runtime_node and (not str(payload.get("node", "")).strip()):
        payload["node"] = runtime_node

    runtime_mode = str(runtime_payload.get("interaction_mode", "")).strip()
    if runtime_mode and (not str(payload.get("interaction_mode", "")).strip()):
        payload["interaction_mode"] = runtime_mode

    runtime_pending_action = str(runtime_payload.get("pending_action", "")).strip()
    if runtime_pending_action and (not str(payload.get("pending_action", "")).strip()):
        payload["pending_action"] = runtime_pending_action

    events_path = project_path("completed_history", "workflow_events.jsonl")
    folder = os.path.dirname(events_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    try:
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _call_llm_safe(max_retries: int = 3, retry_delay_seconds: float = 2.0, **kwargs) -> Any:
    """
    统一 LLM 安全调用：当出现异常或空响应时进行重试，避免节点直接跳过。
    """
    retries = max(1, int(max_retries))
    delay = max(0.0, float(retry_delay_seconds))
    model_name = str(kwargs.get("model", "")).strip()
    node_name = str(kwargs.get("node", "llm_call")).strip() or "llm_call"

    for attempt in range(1, retries + 1):
        try:
            _append_workflow_event(
                "detail",
                f"LLM 等待中：第 {attempt}/{retries} 次请求已发出，等待模型返回。",
                node=node_name,
                model=model_name,
                llm_attempt=attempt,
                llm_max_retries=retries,
            )
            result = call_llm(**kwargs)
            if result is None:
                raise RuntimeError("LLM returned None")
            if isinstance(result, str) and (not result.strip()):

                raise RuntimeError("LLM returned empty string")
            _append_workflow_event(
                "detail",
                f"LLM 返回成功：第 {attempt}/{retries} 次请求完成。",
                node=node_name,
                model=model_name,
                llm_attempt=attempt,
                llm_max_retries=retries,
            )
            return result
        except Exception as e:
            print(f"[WARN] LLM 调用失败(第 {attempt}/{retries} 次): {e}")
            _append_workflow_event(
                "detail",
                f"LLM 调用失败(第 {attempt}/{retries} 次): {e}",
                node=node_name,
                model=model_name,
                llm_attempt=attempt,
                llm_max_retries=retries,
            )
            if attempt >= retries:
                print("[ERROR] LLM 达到最大重试次数，触发流程暂停。")
                _append_workflow_event(
                    "key",
                    "LLM 达到最大重试次数，流程将暂停等待继续重试。",
                    node=node_name,
                    model=model_name,
                    llm_attempt=attempt,
                    llm_max_retries=retries,
                )
                raise RuntimeError("LLM_RETRY_EXHAUSTED") from e
            sleep_seconds = delay * attempt
            if sleep_seconds > 0:
                _append_workflow_event(
                    "detail",
                    f"LLM 准备重试：{sleep_seconds:.1f}s 后发起第 {attempt + 1}/{retries} 次请求。",
                    node=node_name,
                    model=model_name,
                    llm_attempt=attempt,
                    llm_max_retries=retries,
                )
                time.sleep(sleep_seconds)


def _infer_review_key(section: Dict[str, Any], review_library: Dict[str, str]) -> str:
    title = f"{section.get('major_title', '')} {section.get('title', '')}".lower()
    sub_id = str(section.get("sub_chapter_id", ""))
    keys = set(review_library.keys())

    if sub_id.startswith("0.") or "front matter" in title or "摘要" in title or "abstract" in title:
        if "front_matter_review" in keys:
            return "front_matter_review"
        if "abstract_review" in keys:
            return "abstract_review"
    if "introduction" in title or "引言" in title:
        if "introduction_review" in keys:
            return "introduction_review"
    if "method" in title or "方法" in title:
        if "methods_review" in keys:
            return "methods_review"
    if "result" in title or "结果" in title:
        if "results_review" in keys:
            return "results_review"
    if "discussion" in title or "讨论" in title:
        if "discussion_review" in keys:
            return "discussion_review"
    if "conclusion" in title or "结论" in title:
        if "conclusion_review" in keys:
            return "conclusion_review"
    return "none"


def _safe_get(url: str, params: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _extract_json_payload(text: str) -> Any:
    cleaned = str(text).strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    array_match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except Exception:
            pass

    obj_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except Exception:
            pass

    return text


def _coerce_dict_or_none(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = _extract_json_payload(value)
        if isinstance(parsed, dict):
            return parsed
    return None


def _coerce_list_or_none(value: Any) -> Optional[list]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ["queries", "query_list", "search_queries", "keywords", "items", "data"]:
            candidate = value.get(key)
            if isinstance(candidate, list):
                return candidate
            if isinstance(candidate, str):
                parsed = _extract_json_payload(candidate)
                if isinstance(parsed, list):
                    return parsed
    if isinstance(value, str):
        parsed = _extract_json_payload(value)
        if isinstance(parsed, list):
            return parsed
        # 兼容非 JSON 输出：按行/分号抽取检索词候选。
        candidates = []
        text = str(parsed if isinstance(parsed, str) else value)
        for raw in re.split(r"[\n\r;]+", text):
            line = str(raw or "").strip()
            if not line:
                continue
            line = re.sub(r"^[-*\d\.\)\(\s]+", "", line).strip()
            if line.lower().startswith("data:"):
                continue
            if not line:
                continue
            candidates.append(line)
        if candidates:
            return candidates
    return None


def _normalize_image_item(item: Any) -> Optional[Dict[str, str]]:
    if not isinstance(item, dict):
        return None

    detailed = str(
        item.get("detailed_description", item.get("description", item.get("图片的超级详细的描述", "")))
    ).strip()
    title = str(item.get("title", item.get("图标题", ""))).strip()
    image_id = str(item.get("image_id", item.get("图片编号", ""))).strip()
    if not detailed:
        return None

    return {
        "detailed_description": detailed,
        "title": title,
        "image_id": image_id,
    }


def _normalize_image_list(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    result: List[Dict[str, str]] = []
    for item in raw:
        normalized = _normalize_image_item(item)
        if normalized is None:
            continue
        result.append(normalized)
    return result


def _image_dedup_key(item: Dict[str, str]) -> str:
    detailed = re.sub(r"\s+", " ", str(item.get("detailed_description", "")).strip().lower())
    title = re.sub(r"\s+", " ", str(item.get("title", "")).strip().lower())
    return f"{detailed}||{title}"


def _merge_image_pools(user_images: List[Dict[str, str]], planned_images: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    seen: set[str] = set()

    for source in [user_images, planned_images]:
        for item in source:
            normalized = _normalize_image_item(item)
            if normalized is None:
                continue
            dedup_key = _image_dedup_key(normalized)
            if (not dedup_key) or (dedup_key in seen):
                continue
            seen.add(dedup_key)
            merged.append({
                "detailed_description": str(normalized.get("detailed_description", "")).strip(),
                "title": str(normalized.get("title", "")).strip(),
            })
    return merged


def _with_major_image_ids(images: List[Dict[str, str]], major_id: str, start_index: int = 1) -> tuple[List[Dict[str, str]], int]:
    normalized_major_id = str(major_id or "").strip() or "0"
    next_index = max(1, int(start_index))
    result: List[Dict[str, str]] = []
    for item in images:
        row = dict(item)
        current_image_id = str(row.get("image_id", "")).strip()
        if not current_image_id:
            current_image_id = f"{normalized_major_id}.{next_index}"
        row["image_id"] = current_image_id
        result.append(row)
        next_index += 1
    return result, next_index


def _ensure_image_blocks_in_draft(content: str, images: List[Dict[str, str]]) -> str:
    cleaned = str(content or "").strip()
    if not images:
        return cleaned

    for item in images:
        detailed = str(item.get("detailed_description", "")).strip()
        if not detailed:
            continue
        image_id = str(item.get("image_id", "")).strip()
        title = str(item.get("title", "")).strip()
        block = f"【{detailed}】\n【{(f'{image_id} {title}').strip()}】"
        if block not in cleaned:
            cleaned = f"{cleaned}\n\n{block}" if cleaned else block
    return cleaned.strip()


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "是"}:
        return True
    if text in {"false", "0", "no", "n", "否"}:
        return False
    return default


def _extract_openalex_abstract(item: Dict[str, Any]) -> str:
    # OpenAlex commonly stores abstracts in inverted index format.
    inverted = item.get("abstract_inverted_index")
    if isinstance(inverted, dict) and inverted:
        pos_to_word: Dict[int, str] = {}
        for word, positions in inverted.items():
            if not isinstance(positions, list):
                continue
            for pos in positions:
                if isinstance(pos, int):
                    pos_to_word[pos] = str(word)
        if pos_to_word:
            return " ".join(pos_to_word[idx] for idx in sorted(pos_to_word.keys()))

    raw_abstract = item.get("abstract", "")
    return str(raw_abstract or "").strip()


def _search_semantic_scholar(query: str, limit: int = 8) -> list[Dict[str, Any]]:
    data = _safe_get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        {
            "query": query,
            "limit": limit,
            "fields": "title,year,abstract,authors,url,venue",
        },
    )
    papers = []
    for item in data.get("data", []) or []:
        papers.append({
            "title": item.get("title", ""),
            "authors": ", ".join([a.get("name", "") for a in (item.get("authors", []) or []) if a.get("name")]),
            "year": item.get("year", ""),
            "abstract": item.get("abstract", ""),
            "source": "Semantic Scholar",
            "url": item.get("url", ""),
            "venue": item.get("venue", ""),
        })
    return papers


def _search_openalex(query: str, limit: int = 8, api_key: str = "") -> list[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "search": query,
        "per-page": limit,
        "sort": "relevance_score:desc",
    }
    if api_key:
        params["api_key"] = api_key

    data = _safe_get(
        "https://api.openalex.org/works",
        params,
    )
    papers = []
    for item in data.get("results", []) or []:
        authors = []
        for auth in item.get("authorships", []) or []:
            name = (auth.get("author") or {}).get("display_name", "")
            if name:
                authors.append(name)
        papers.append({
            "title": item.get("title", ""),
            "authors": ", ".join(authors),
            "year": item.get("publication_year", ""),
            "abstract": _extract_openalex_abstract(item),
            "source": "OpenAlex",
            "url": item.get("id", ""),
            "venue": ((item.get("host_venue") or {}).get("display_name", "")),
        })
    return papers


def _search_core(query: str, limit: int = 8) -> list[Dict[str, Any]]:
    api_key = os.getenv("CORE_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    data = _safe_get(
        "https://core.ac.uk/api-v2/articles/search",
        {
            "q": query,
            "page": 1,
            "pageSize": limit,
        },
        headers=headers,
    )
    papers = []
    for item in data.get("data", []) or []:
        papers.append({
            "title": item.get("title", ""),
            "authors": ", ".join(item.get("authors", []) or []),
            "year": item.get("yearPublished", ""),
            "abstract": item.get("abstract", ""),
            "source": "CORE",
            "url": item.get("downloadUrl", "") or item.get("doi", ""),
            "venue": item.get("publisher", ""),
        })
    return papers


def _is_good_query(query: str) -> bool:
    q = " ".join(str(query or "").split())
    if not q:
        return False

    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", q))
    if cjk_count > 0:
        if cjk_count < 4:
            return False
    else:
        if len(q) < 8:
            return False

    lowered = q.lower()
    if lowered in {"data: [done]", "[done]", "done"}:
        return False
    if lowered.startswith("data:"):
        return False
    banned = {"ai", "artificial intelligence", "machine learning", "review"}
    return lowered not in banned


def _clean_query(query: str) -> str:
    q = " ".join(str(query or "").replace("\n", " ").split())
    return q.strip(" -;,.\"'")


def _dedupe_queries(queries: list[str]) -> list[str]:
    result = []
    seen = set()
    for q in queries:
        cleaned = _clean_query(q)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _strip_heading_number_prefix(title: str) -> str:
    text = str(title or "").strip()
    if not text:
        return ""

    text = re.sub(r"^(chapter|section)\s*\d+(?:\.\d+)*\s*[:\.)\-、]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^第\s*\d+(?:\.\d+)*\s*[章节篇部]\s*", "", text)
    text = re.sub(r"^\d+(?:\.\d+)*\s*[:\.)\-、]\s*", "", text)
    text = re.sub(r"^\d+(?:\.\d+)*\s+", "", text)
    return text.strip()


def _sanitize_title_with_id(title: str, chapter_id: str) -> str:
    cleaned = _strip_heading_number_prefix(title)
    cid = str(chapter_id or "").strip()
    if cid and cleaned:
        cleaned = re.sub(rf"^{re.escape(cid)}\s*[:\.)\-、]\s*", "", cleaned)
        cleaned = re.sub(rf"^{re.escape(cid)}\s+", "", cleaned)
    return cleaned.strip()


def _sanitize_outline_titles(outline: Any) -> list[Dict[str, Any]]:
    if not isinstance(outline, list):
        return []

    sanitized: list[Dict[str, Any]] = []
    for major in outline:
        if not isinstance(major, dict):
            continue

        major_copy = dict(major)
        major_id = str(major_copy.get("major_chapter_id", "")).strip()
        major_title_raw = str(major_copy.get("major_title", "")).strip()
        major_title_clean = _sanitize_title_with_id(major_title_raw, major_id)
        if major_title_clean:
            major_copy["major_title"] = major_title_clean

        chapter_header_title = str(major_copy.get("chapter_header_title", "")).strip()
        chapter_header_clean = _sanitize_title_with_id(chapter_header_title, major_id)
        if chapter_header_clean:
            major_copy["chapter_header_title"] = chapter_header_clean

        cleaned_sub_sections: list[Dict[str, Any]] = []
        for sub in (major_copy.get("sub_sections", []) or []):
            if not isinstance(sub, dict):
                continue
            sub_copy = dict(sub)
            sub_id = str(sub_copy.get("sub_chapter_id", "")).strip()
            sub_title_raw = str(sub_copy.get("sub_title", "")).strip()
            sub_title_clean = _sanitize_title_with_id(sub_title_raw, sub_id)
            if sub_title_clean:
                sub_copy["sub_title"] = sub_title_clean
            cleaned_sub_sections.append(sub_copy)

        major_copy["sub_sections"] = cleaned_sub_sections
        sanitized.append(major_copy)

    return sanitized


def _build_search_queries_with_llm(state: PaperWriterState) -> list[str]:
    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["paper_search_query_builder"].safe_substitute(
        topic=state.topic if state.topic.strip() else "未提供",
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        existing_sections=state.existing_sections,
        existing_material=state.existing_material,
        research_gaps=state.research_gaps if str(state.research_gaps).strip() else "暂无",
    )
    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)

    try:
        out_path = project_path("completed_history", "query_builder_last_output.txt")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(str(response))
    except Exception:
        pass

    queries = _coerce_list_or_none(response)
    if (not queries) and isinstance(response, dict):
        for key in ["result", "output", "text"]:
            val = response.get(key)
            queries = _coerce_list_or_none(val)
            if queries:
                break

    if isinstance(queries, list):
        filtered = [q for q in queries if isinstance(q, str)]
        filtered = [q for q in filtered if _is_good_query(q)]
        filtered = _dedupe_queries(filtered)
        if filtered:
            return filtered[:8]

    print("| [DEBUG] SearchQueryBuilder 原始LLM输出:")
    print(str(response))

    return []


def _persist_topic_to_inputs_json(topic: str) -> None:
    clean_topic = str(topic or "").strip()
    if not clean_topic:
        return

    path = resolve_inputs_path()
    payload: Dict[str, Any] = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                payload = loaded
    except Exception:
        payload = {}

    payload["topic"] = clean_topic
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _save_llm_call_checkpoint(state: PaperWriterState, node_tag: str) -> None:
    try:
        checkpoint_path = str(getattr(state, "runtime_checkpoint_path", "") or "").strip()
        if not checkpoint_path:
            _, checkpoint_path = build_output_paths(state.model, state.topic, state.get_prompt_language())
            state.runtime_checkpoint_path = checkpoint_path
        state.mark_progress(
            node=node_tag,
            reason=f"llm_call_ok:{node_tag}",
            major_id=str(getattr(state, "current_major_chapter_id", "") or ""),
            sub_id=str(getattr(state, "current_sub_chapter_id", "") or ""),
        )
        save_state_checkpoint(state, checkpoint_path)
    except Exception as e:
        print(f"| [WARN] LLM 调用后保存细粒度断点失败({node_tag}): {e}")


def node_title_builder(state: PaperWriterState) -> PaperWriterState:
    """
    Title Builder Node: 在流程最开始统一确定论文题目。
    """
    current_topic = str(getattr(state, "topic", "") or "").strip()
    topic_lower = current_topic.lower()
    if current_topic and topic_lower not in {"auto_title_pending", "未提供", "none", "n/a", "null"}:
        print(f"| [TitleBuilder] 使用现有题目: {current_topic}")
        return state

    print("\n[Node: TitleBuilder] 生成论文标题...")
    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["title_builder"].safe_substitute(
        topic=current_topic if current_topic else "未提供",
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        existing_sections=state.existing_sections,
        existing_material=state.existing_material,
        research_gaps=state.research_gaps if str(state.research_gaps).strip() else "暂无",
    )
    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_title_builder")

    candidate = ""
    if isinstance(response, dict):
        for key in ["title", "topic", "paper_title"]:
            text = str(response.get(key, "") or "").strip()
            if text:
                candidate = text
                break
    else:
        candidate = str(response or "").strip()

    candidate = candidate.replace("\n", " ").strip()
    candidate = re.sub(r"^#{1,6}\s*", "", candidate)
    candidate = re.sub(r"^(标题|题目|title)\s*[:：]\s*", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.strip(" \t\r\n\"'“”‘’")

    if candidate:
        state.topic = candidate
        try:
            _persist_topic_to_inputs_json(candidate)
        except Exception as e:
            print(f"| [WARN] [TitleBuilder] 题目写回 inputs.json 失败: {e}")
        _save_llm_call_checkpoint(state, "node_title_builder")
        print(f"| [OK] [TitleBuilder] 题目已确定: {state.topic}")
    else:
        print("| [WARN] [TitleBuilder] 未生成有效题目，保留原始topic。")
    return state


def _is_valid_paper_item(paper: Dict[str, Any]) -> bool:
    title = str(paper.get("title", "") or "").strip()
    url = str(paper.get("url", "") or "").strip()
    if not title or title.upper() == "N/A":
        return False
    if not url:
        return False
    return True


def _fetch_openalex_papers_by_queries(
    queries: list[str],
    total_limit: int,
    openalex_api_key: str,
) -> list[Dict[str, Any]]:
    merged: list[Dict[str, Any]] = []
    seen = set()
    for idx, query in enumerate(queries, start=1):
        if len(merged) >= total_limit:
            break
        remain = total_limit - len(merged)
        per_query_limit = min(12, max(3, remain))
        print(f"| 检索词[{idx}/{len(queries)}]: {query}")
        try:
            result = _search_openalex(query, limit=per_query_limit, api_key=openalex_api_key)
            print(f"| OpenAlex: 获取 {len(result)} 条")
        except Exception as e:
            print(f"| [WARN] OpenAlex 检索失败: {e}")
            continue

        for paper in result:
            if not _is_valid_paper_item(paper):
                continue
            key = (
                str(paper.get("url", "")).strip().lower(),
                str(paper.get("title", "")).strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(paper)
            if len(merged) >= total_limit:
                break
    return merged


def _format_related_works_markdown(papers: list[Dict[str, Any]]) -> str:
    lines = ["# Related Works", ""]
    if not papers:
        lines.append("未检索到可用文献，请手动补充。")
        return "\n".join(lines)

    for idx, paper in enumerate(papers, start=1):
        title = str(paper.get("title", "") or "N/A").strip()
        authors = str(paper.get("authors", "") or "N/A").strip()
        year = str(paper.get("year", "") or "N/A").strip()
        source = str(paper.get("source", "") or "N/A").strip()
        venue = str(paper.get("venue", "") or "N/A").strip()
        url = str(paper.get("url", "") or "N/A").strip()
        abstract = str(paper.get("abstract", "") or "N/A").strip()

        lines.extend([
            f"## {idx}. {title}",
            f"- Authors: {authors}",
            f"- Year: {year}",
            f"- Source: {source}",
            f"- Venue: {venue}",
            f"- URL: {url}",
            f"- Abstract: {abstract}",
            "",
        ])
    return "\n".join(lines).strip()


def node_search_query_builder(state: PaperWriterState) -> PaperWriterState:
    """
    Search Query Builder Node: 使用全量输入生成高质量检索词句列表。
    """
    print("\n[Node: SearchQueryBuilder] 生成关键检索词句...")
    queries = _build_search_queries_with_llm(state)
    if not queries:
        raise RuntimeError("SEARCH_QUERY_BUILDER_EMPTY")

    state.search_queries = queries
    print(f"| [SearchQueryBuilder] 已生成检索词 {len(queries)} 条")
    for idx, query in enumerate(queries, start=1):
        print(f"| [SearchQueryBuilder] 关键词[{idx}/{len(queries)}]: {query}")
    return state


def _build_chapter_opening_markdown(major_id: str, header_title: str, lead: str) -> str:
    safe_header_title = _sanitize_title_with_id(header_title, major_id) or str(header_title).strip()
    title_line = f"## {str(major_id).strip()} {safe_header_title}".strip()
    parts = [title_line, ""]
    if str(lead).strip():
        parts.extend([str(lead).strip(), ""])
    return "\n".join(parts).strip()


def _ensure_chapter_header_in_first_subsection(
    content: str,
    major_id: str,
    header_title: str,
    lead: str,
    opening_markdown: str = "",
) -> str:
    text = str(content or "").strip()
    lines = text.splitlines()

    # 移除旧的大章节标题与旧总起段，保留到第一个三级标题开始。
    if lines and lines[0].strip().startswith("## "):
        i = 1
        while i < len(lines) and not lines[i].strip().startswith("### "):
            i += 1
        lines = lines[i:]

    opening = str(opening_markdown or "").strip() or _build_chapter_opening_markdown(major_id, header_title, lead)
    rebuilt = [opening, ""]
    rebuilt.extend(lines)
    return "\n".join(rebuilt).strip()


def _normalize_zero_chapter_content(content: str) -> str:
    text = str(content or "").strip()
    if not text:
        return text

    normalized_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # 第0章禁止出现 0.x 编号标题，统一清洗为无编号前置信息。
        if re.match(r"^#{1,6}\s*0\.\d+", stripped):
            continue
        if re.match(r"^0\.\d+", stripped):
            continue
        lowered = stripped.lower()
        if lowered.startswith("this title explicitly encodes"):
            continue
        if lowered.startswith("standardized placeholders aligned with"):
            continue
        normalized_lines.append(line)

    return "\n".join(normalized_lines).strip()


def _build_zero_chapter_minimal_block(state: PaperWriterState, sub_id: str, sub_title: str) -> str:
    sid = str(sub_id or "").strip()
    language = str(getattr(state, "language", "English") or "English").strip().lower()

    if sid == "0.1":
        title = str(getattr(state, "topic", "") or "").strip() or str(sub_title or "Title").strip()
        return f"# {title}".strip()

    if sid == "0.2":
        if language == "chinese":
            return "作者：<请填写作者姓名>"
        return "Authors: <Fill in author names>"

    return ""


def _coerce_keywords_list(value: Any) -> list[str]:
    parsed = _coerce_list_or_none(value)
    if not parsed:
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in parsed:
        text = str(item or "").strip()
        if not text:
            continue
        text = re.sub(r"^[-*\d\.\)\(\s]+", "", text).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned[:8]


def _build_keywords_block(keywords: list[str], language: str) -> str:
    lang = str(language or "English").strip().lower()
    heading = "## 关键词" if lang == "chinese" else "## Keywords"
    payload = ", ".join([str(x).strip() for x in keywords if str(x).strip()])
    if not payload:
        payload = "keyword1, keyword2, keyword3"
    return f"{heading}\n\nKeywords: {payload}".strip()


def _default_zero_chapter_subsection(sub_id: str, language: str) -> str:
    sid = str(sub_id or "").strip()
    lang = str(language or "English").strip().lower()

    if sid == "0.3":
        heading = "## 摘要" if lang == "chinese" else "## Abstract"
        body = "<请填写摘要内容>" if lang == "chinese" else "<Provide abstract text>"
        return f"{heading}\n\n{body}".strip()

    if sid == "0.4":
        return _build_keywords_block(["keyword1", "keyword2", "keyword3"], language)

    fallback_title = _strip_heading_number_prefix(sub_id)
    if lang == "chinese":
        return f"## {fallback_title or '前置信息'}\n\n<请填写内容>".strip()
    return f"## {fallback_title or 'Front Matter'}\n\n<Provide content>".strip()


def node_search_paper(state: PaperWriterState) -> PaperWriterState:
    """
    Paper Search Node: 根据主题与领域检索相关文献，并生成 related_works.md。
    """
    topic_hint = state.topic.strip() if state.topic.strip() else "(题目缺省，请根据材料自动识别主题)"
    queries = list(getattr(state, "search_queries", []) or [])
    if not queries:
        state = node_search_query_builder(state)
        queries = list(getattr(state, "search_queries", []) or [])
    if not queries:
        queries = [topic_hint]

    print("\n[Node: SearchPaper] 开始检索相关文献...")
    total_limit = max(1, int(getattr(state, "paper_search_limit", 20)))
    openalex_api_key = str(getattr(state, "openalex_api_key", "")).strip()
    print(f"| 检索配置: source=OpenAlex, total_limit={total_limit}, query_count={len(queries)}")

    papers = _fetch_openalex_papers_by_queries(
        queries=queries,
        total_limit=total_limit,
        openalex_api_key=openalex_api_key,
    )
    if not papers:
        fallback = "# Related Works\n\n未检索到可用文献，请手动补充。"
        with open(state.related_works_path, "w", encoding="utf-8") as f:
            f.write(fallback)
        state.related_works_summary = fallback
        return state

    related_works_md = _format_related_works_markdown(papers)

    with open(state.related_works_path, "w", encoding="utf-8") as f:
        f.write(related_works_md)

    state.related_works_summary = related_works_md
    print(f"| [OK] [SearchPaper] 已生成文献综述列表: {state.related_works_path}")
    return state


def node_chapter_header(state: PaperWriterState, current_major: Dict[str, Any]) -> PaperWriterState:
    """
    Chapter Header Node: 为大章节生成专用章节标题与总起句。
    """
    major_id = str(current_major.get("major_chapter_id", "")).strip()
    if major_id == "0":
        return state

    major_title_clean = _sanitize_title_with_id(current_major.get("major_title", ""), major_id) or str(current_major.get("major_title", "")).strip()
    if major_title_clean:
        current_major["major_title"] = major_title_clean

    sub_sections_info = json.dumps(current_major.get("sub_sections", []), ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["chapter_header_builder"].safe_substitute(
        topic=state.topic,
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        major_chapter_id=major_id,
        major_title=major_title_clean,
        major_purpose=current_major.get("major_purpose", ""),
        sub_sections_info=sub_sections_info,
        research_gaps=state.research_gaps if str(state.research_gaps).strip() else "暂无",
        existing_material=state.existing_material,
    )
    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_chapter_header")
    data = _coerce_dict_or_none(response) or {}

    title = _sanitize_title_with_id(data.get("chapter_header_title", ""), major_id)
    if not title:
        title = _sanitize_title_with_id(current_major.get("major_title", ""), major_id) or str(current_major.get("major_title", "")).strip()
    lead = str(data.get("chapter_header_lead", "")).strip()

    current_major["chapter_header_title"] = title
    current_major["chapter_header_lead"] = lead
    print(f"| [OK] [ChapterHeader] {major_id} 标题/总起句已生成")
    return state


def node_chapter_opening(state: PaperWriterState, current_major: Dict[str, Any]) -> PaperWriterState:
    """
    Chapter Opening Node: 使用专用提示词生成章节开篇 markdown（仅二级标题+总起句）。
    """
    major_id = str(current_major.get("major_chapter_id", "")).strip()
    if major_id == "0":
        return state

    header_title = _sanitize_title_with_id(current_major.get("chapter_header_title", current_major.get("major_title", "")), major_id) or str(current_major.get("major_title", "")).strip()
    current_major["chapter_header_title"] = header_title
    header_lead = str(current_major.get("chapter_header_lead", "")).strip()
    fallback_opening = _build_chapter_opening_markdown(major_id, header_title, header_lead)

    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["chapter_opening_writer"].safe_substitute(
        topic=state.topic,
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        major_chapter_id=major_id,
        major_title=_sanitize_title_with_id(current_major.get("major_title", ""), major_id) or str(current_major.get("major_title", "")).strip(),
        chapter_header_title=header_title,
        chapter_header_lead=header_lead,
        major_purpose=current_major.get("major_purpose", ""),
        sub_sections_info=json.dumps(current_major.get("sub_sections", []), ensure_ascii=False, indent=2),
    )

    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_chapter_opening")
    opening = "" if response is None else str(response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()

    if opening:
        kept_lines = []
        for line in opening.splitlines():
            if line.strip().startswith("### "):
                break
            kept_lines.append(line)
        opening = "\n".join(kept_lines).strip()

    if (not opening) or (not opening.splitlines()[0].strip().startswith("## ")):
        opening = fallback_opening

    if not str(header_lead).strip():
        # 总起句为空时保持纯标题开篇，避免误注入无关正文。
        opening = f"## {major_id} {header_title}".strip()

    current_major["chapter_opening_markdown"] = opening
    print(f"| [OK] [ChapterOpening] {major_id} 开篇块已生成")
    return state


def node_research_gaps(state: PaperWriterState) -> PaperWriterState:
    """
    Research Gaps Node: 基于主题、文献列表与补充文档生成研究空白与潜在贡献。
    """
    print("\n[Node: ResearchGaps] 开始生成研究空白与贡献...")
    related_works = state.related_works_summary
    if not related_works and os.path.exists(state.related_works_path):
        with open(state.related_works_path, "r", encoding="utf-8") as f:
            related_works = f.read().strip()

    topic_hint = state.topic.strip() if state.topic.strip() else "(题目缺省，请先给出可投稿标题并据此分析)"
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["research_gap_analyst"].safe_substitute(
        topic=topic_hint,
        language=state.language,
        user_requirements=state.user_requirements,
        related_works=related_works if related_works else "暂无相关文献列表",
        references_material="该输入通道已停用，请仅基于 related_works 与用户要求输出",
    )
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_research_gaps")
    research_gap_md = "" if response is None else str(response).strip()
    if not research_gap_md:
        research_gap_md = "# Research Gaps and Contributions\n\n未生成结果，请手动补充。"

    with open(state.research_gap_output_path, "w", encoding="utf-8") as f:
        f.write(research_gap_md)

    state.research_gaps = research_gap_md
    print(f"| [OK] [ResearchGaps] 已输出: {state.research_gap_output_path}")
    return state

def node_architect(state: PaperWriterState) -> PaperWriterState:
    """
    Node 1: 顶刊级学术架构师 (Lead Academic Architect)
    基于初始素材，精准界定研究领域，提取 Gap 与 Contribution，并规划 IMRaD 全局大纲。
    """
    print("\n" +"|"+ "=" * 40)
    print("|[RUN] 开始执行: 顶刊级学术架构规划...")
    print("|"+"=" * 40)

    # 1. 组装 User Prompt
    # 使用 safe_substitute 安全注入 State 中的变量
    topic_for_architect = state.topic if state.topic.strip() else "（题目未提供：请先自动构建一个高质量论文标题）"
    architecture_feedback = "None"
    if getattr(state, "architecture_issues", []):
        payload = {
            "summary": getattr(state, "architecture_summary", ""),
            "issues": getattr(state, "architecture_issues", []),
            "improvement_actions": getattr(state, "architecture_improvement_actions", []),
        }
        architecture_feedback = json.dumps(payload, ensure_ascii=False, indent=2)
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["architect"].safe_substitute(
        topic=topic_for_architect,
        existing_sections=state.existing_sections,
        existing_material=state.existing_material,
        research_gap_all=state.research_gaps,  # 注意映射到 state.research_gaps
        overall_guidance=state.get_overall_guidance(),
        language=state.language,
        architecture_review_feedback=architecture_feedback,
    )

    # 3. 调用大模型底层函数
    print("|[WAIT] 正在调用大模型生成全局架构大纲，请稍候...")
    result = _call_llm_safe(
        system_input=system_prompt,
        thinking=False,
        model=state.model,
    )
    _save_llm_call_checkpoint(state, "node_architect")

    # 4. 解析结果并更新状态 (State Management)
    outline = _coerce_list_or_none(result)
    outline = _sanitize_outline_titles(outline)
    if outline:
        # 将生成的关键信息写入 State
        state.outline = outline
        print(f"| [OK] [Node 1] 执行成功！")
        print(f"| [OK] [Architect] 执行成功！共规划了 {len(outline)} 个章节。")
    _save_llm_call_checkpoint(state, "node_architect")
    # 5. 返回更新后的状态机，供下一个节点使用
    return state


def node_architecture_review(state: PaperWriterState) -> PaperWriterState:
    """
    Architecture Reviewer Node:
    审查架构是否存在高优先级问题；若存在则返回可执行改进意见。
    """
    if not isinstance(getattr(state, "outline", None), list) or not state.outline:
        raise RuntimeError("architecture review requires a non-empty outline")

    state.architecture_review_round = int(getattr(state, "architecture_review_round", 0)) + 1
    print(f"| [Node: ArchitectureReview] Round {state.architecture_review_round} ...")

    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["architecture_reviewer"].safe_substitute(
        topic=state.topic,
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        outline=json.dumps(state.outline, ensure_ascii=False, indent=2),
        research_gap_all=state.research_gaps,
        overall_guidance=state.get_overall_guidance(),
        architecture_review_round=state.architecture_review_round,
        max_architecture_review_rounds=getattr(state, "max_architecture_review_rounds", 3),
    )
    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_architecture_review")

    review = _coerce_dict_or_none(response) or {}
    issues = review.get("issues", []) if isinstance(review.get("issues", []), list) else []
    actions = review.get("improvement_actions", []) if isinstance(review.get("improvement_actions", []), list) else []
    summary = str(review.get("summary", "")).strip()

    # 默认规则：无 high 问题即通过。
    has_high = any(str(item.get("severity", "")).strip().lower() == "high" for item in issues if isinstance(item, dict))
    model_passed = _coerce_bool(review.get("passed", not has_high), default=not has_high)
    state.architecture_passed = bool(model_passed and (not has_high))
    state.architecture_summary = summary
    state.architecture_issues = issues
    state.architecture_improvement_actions = actions

    print(
        f"| [ArchitectureReview] passed={state.architecture_passed}, "
        f"issues={len(issues)}, high_blockers={1 if has_high else 0}"
    )
    return state


def node_image_planner(state: PaperWriterState) -> PaperWriterState:
    """
    Image Planner Node:
    在架构确定后，融合用户图片描述与模型补充图片，形成统一图片池供后续 planner/writer 使用。
    """
    print("| [Node: ImagePlanner] 开始图片规划与补充...")

    user_images = _normalize_image_list(
        getattr(state, "user_image_descriptions", getattr(state, "image_descriptions", []))
    )
    outline = _coerce_list_or_none(getattr(state, "outline", [])) or []

    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["image_planner"].safe_substitute(
        topic=getattr(state, "topic", ""),
        language=getattr(state, "language", "English"),
        user_requirements=getattr(state, "user_requirements", ""),
        outline=json.dumps(outline, ensure_ascii=False, indent=2),
        user_image_descriptions=json.dumps(user_images, ensure_ascii=False, indent=2),
        overall_guidance=state.get_overall_guidance(),
    )

    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_image_planner")

    response_dict = _coerce_dict_or_none(response) or {}
    planned_raw = response_dict.get("planned_image_descriptions", [])
    planned_images = _normalize_image_list(planned_raw)

    merged_images = _merge_image_pools(user_images, planned_images)
    if not merged_images:
        merged_images = copy.deepcopy(user_images)

    added_count = max(0, len(merged_images) - len(user_images))
    state.user_image_descriptions = copy.deepcopy(user_images)
    state.image_descriptions = copy.deepcopy(merged_images)
    state.planned_image_descriptions = copy.deepcopy(merged_images)
    state.image_planning_done = True
    state.image_planning_summary = (
        f"user_images={len(user_images)}, model_added={added_count}, total={len(merged_images)}"
    )

    print(
        f"| [ImagePlanner] 完成，用户图片 {len(user_images)} 条，"
        f"模型补充 {added_count} 条，最终共 {len(merged_images)} 条。"
    )
    return state


def node_planner(state: PaperWriterState, current_major: Dict) -> PaperWriterState:
    """
    Planner Node (Major Level): 接收整个大章节，一次性为下属【所有小节】生成段落蓝图与上下文路由。
    """
    major_title = current_major.get("major_title", "Unknown")
    print(f"\n| [Node: Planner] 正在为大章节 [{major_title}] 统筹制定下属所有小节的蓝图与路由...")
    # 1. 提取所有小节的信息并转为易读的字符串，喂给大模型
    sub_sections_info = json.dumps(
        [{k: v for k, v in sub.items() if k != "draft_content"} for sub in current_major.get("sub_sections", [])],
        ensure_ascii=False, indent=2
    )
    available_images = _normalize_image_list(getattr(state, "image_descriptions", []))

    # 2. 组装 Prompt (这里需要你的 PROMPT_PLANNER 升级为接受大章节下属所有小节信息的版本)
    # 系统提示词中，我们会要求模型输出一个包含多个对象的数组，每个对象对应一个 sub_chapter_id
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["planner"].safe_substitute(
        language=getattr(state, "language", "English"),
        paper_outline=json.dumps(getattr(state, "outline", []), ensure_ascii=False),
        current_major_id=current_major.get("major_chapter_id", ""),
        major_title=major_title,
        major_purpose=current_major.get("major_purpose", ""),
        current_writing_order=current_major.get("writing_order", 99),
        sub_sections_info=sub_sections_info,  # 喂入该大章节下的所有小节概况
        overall_guidance=state.get_overall_guidance(),
        writing_guidance_catalog=serialize_guidance_catalog(getattr(state, "writing_guidance_library", {})),
        available_image_descriptions=json.dumps(available_images, ensure_ascii=False, indent=2),
    )
    # 3. 调用大模型
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_planner")
    response_dict = _coerce_dict_or_none(response)
    # 4. 解析结果并分发到各个小节的 state 中
    if response_dict and "plans" in response_dict:
        # 假设 LLM 返回格式为: {"plans": [{"sub_chapter_id": "2.1", "context_routing": {...}, ...}]}
        plans_list = response_dict.get("plans", [])

        # 将计划映射回大纲树中
        major_id = str(current_major.get("major_chapter_id", "")).strip() or "0"
        image_serial = 1
        for sub in current_major.get("sub_sections", []):
            target_id = sub.get("sub_chapter_id")
            # 找到对应的规划结果
            matched_plan = next((p for p in plans_list if p.get("sub_chapter_id") == target_id), None)

            if matched_plan:
                sub["context_routing"] = matched_plan.get("context_routing", {})
                sub["paragraph_blueprints"] = matched_plan.get("paragraph_blueprints", [])
                sub["selected_guidance_key"] = matched_plan.get("selected_guidance_key", "none")
                sub["guidance_reason"] = matched_plan.get("guidance_reason", "")
                required_images = _normalize_image_list(matched_plan.get("required_images", []))
                required_images, image_serial = _with_major_image_ids(required_images, major_id=major_id, start_index=image_serial)
                sub["required_images"] = required_images
                print(f"| 小节 [{target_id}] 蓝图与路由已挂载。")
            else:
                print(f"   [WARN] 未找到小节 [{target_id}] 的规划结果！")

        print(f"| [OK] [Planner] 大章节 [{major_title}] 统筹规划完成！")
    else:
        print(f"| [WARN] [Planner] 执行未完全成功，未能获取或解析合法的结构化响应。")
    _save_llm_call_checkpoint(state, "node_planner")
    return state


def node_writer(state: PaperWriterState, current_major: Dict, current_sub: Dict) -> PaperWriterState:
    """
    Writer Node (Sub Level): 根据 Planner 分发的蓝图，精准抽取前文 ID 对应的草稿，撰写正文并追加到线性历史记录中。
    """
    sub_id = current_sub.get('sub_chapter_id')
    sub_title = _sanitize_title_with_id(current_sub.get('sub_title', ''), sub_id) or str(current_sub.get('sub_title', '')).strip()
    current_sub['sub_title'] = sub_title
    print(f"| | [Node: Writer] 正在撰写正文: {sub_id} {sub_title} ...")

    # 1. 提取动态路由开关
    routing = current_sub.get("context_routing", {})
    # 2. 动态组装外部长文本
    context_material = state.existing_material if routing.get("need_existing_material") else "无需参考核心实验数据。"
    context_gap = state.research_gaps if routing.get("need_research_gap_all") else "无需参考全局文献Gap。"
    # 3. 【核心】：根据 Planner 给出的 ID 列表，去 state.completed_sections 中精准捞取前文
    required_ids = routing.get("required_section_ids", [])
    context_sections = ""
    if required_ids and hasattr(state, "completed_sections"):
        for past_sec in state.completed_sections:
            if past_sec["sub_chapter_id"] in required_ids:
                # 把捞到的前文拼装起来
                context_sections += f"### {past_sec['content']}\n\n"
    if not context_sections:
        context_sections = "无需参考前文草稿。"
    # 4. 格式化段落蓝图
    blueprints_str = json.dumps(current_sub.get("paragraph_blueprints", []), ensure_ascii=False, indent=2)
    is_zero_chapter = str(current_major.get("major_chapter_id", "")).strip() == "0" or str(sub_id).startswith("0.")
    major_id = str(current_major.get("major_chapter_id", "")).strip()
    major_title_clean = _sanitize_title_with_id(current_major.get("major_title", ""), major_id) or str(current_major.get("major_title", "")).strip()
    if major_title_clean:
        current_major["major_title"] = major_title_clean
    header_title = _sanitize_title_with_id(current_major.get("chapter_header_title", current_major.get("major_title", "")), major_id) or str(current_major.get("major_title", "")).strip()
    current_major["chapter_header_title"] = header_title
    header_lead = str(current_major.get("chapter_header_lead", "")).strip()
    guidance_key = str(current_sub.get("selected_guidance_key", "none")).strip()
    guidance_library = getattr(state, "writing_guidance_library", {})
    selected_guidance = guidance_library.get(guidance_key, "") if guidance_key != "none" else ""
    if not selected_guidance:
        selected_guidance = "未指定模块写作指导建议。"
    required_images = _normalize_image_list(current_sub.get("required_images", []))
    required_images, _ = _with_major_image_ids(required_images, major_id=major_id, start_index=1)
    current_sub["required_images"] = copy.deepcopy(required_images)
    required_images_json = json.dumps(required_images, ensure_ascii=False, indent=2)

    if is_zero_chapter:
        minimal_block = _build_zero_chapter_minimal_block(state, str(sub_id), sub_title)
        if minimal_block:
            cleaned_draft = minimal_block
            current_sub["draft_content"] = cleaned_draft

            actual_order = len(state.completed_sections) + 1
            state.completed_sections.append({
                "actual_order_index": actual_order,
                "major_title": major_title_clean,
                "sub_chapter_id": sub_id,
                "title": sub_title,
                "content": cleaned_draft
            })
            _save_llm_call_checkpoint(state, "node_writer")
            print(f"| | [OK] [Writer] 第0章最小块已生成: {sub_id}")
            return state

        zero_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["zero_chapter_writer"].safe_substitute(
            language=getattr(state, "language", "English"),
            topic=str(getattr(state, "topic", "") or "").strip(),
            sub_chapter_id=sub_id,
            sub_title=sub_title,
            user_requirements=getattr(state, "user_requirements", ""),
            existing_material=context_material,
            research_gap_all=context_gap,
        )
        zero_response = _call_llm_safe(system_input=zero_prompt, thinking=False, model=state.model)
        _save_llm_call_checkpoint(state, "node_writer")

        language_value = str(getattr(state, "language", "English") or "English")
        if str(sub_id).strip() == "0.4":
            keywords = _coerce_keywords_list(zero_response)
            if keywords:
                cleaned_draft = _build_keywords_block(keywords, language_value)
            else:
                cleaned_draft = _default_zero_chapter_subsection(str(sub_id), language_value)
        else:
            cleaned_draft = "" if zero_response is None else str(zero_response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
            cleaned_draft = _normalize_zero_chapter_content(cleaned_draft)
            if not cleaned_draft:
                cleaned_draft = _default_zero_chapter_subsection(str(sub_id), language_value)

        current_sub["draft_content"] = cleaned_draft
        actual_order = len(state.completed_sections) + 1
        state.completed_sections.append({
            "actual_order_index": actual_order,
            "major_title": major_title_clean,
            "sub_chapter_id": sub_id,
            "title": sub_title,
            "content": cleaned_draft
        })
        _save_llm_call_checkpoint(state, "node_writer")
        print(f"| | [OK] [Writer] 第0章专用提示词生成完成: {sub_id}")
        return state

    # 5. 组装 Prompt
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["writer"].safe_substitute(
        major_chapter_id=current_major.get("major_chapter_id", ""),
        major_title=major_title_clean,
        chapter_header_title=header_title,
        chapter_header_lead=header_lead,
        sub_chapter_id=sub_id,
        sub_title=sub_title,
        architecture_role=current_sub.get("architecture_role", ""),
        content_anchors=current_sub.get("content_anchors", ""),
        expected_words=current_sub.get("expected_words", ""),
        paragraph_blueprints=blueprints_str,
        existing_material=context_material,
        research_gap_all=context_gap,
        existing_sections=context_sections,  # 精准喂入的前文
        selected_writing_guidance=selected_guidance,
        required_images=required_images_json,
        language=getattr(state, "language", "English"),
        user_requirements=getattr(state, "user_requirements", ""),
        is_zero_chapter="true" if is_zero_chapter else "false",
        target_reminder=f"Only write subsection {sub_id} {sub_title}. Do not write any other subsection or previous chapter content.",
    )

    # 6. 调用大模型生成纯文本
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_writer")
    cleaned_draft = "" if response is None else str(response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    if response is None or not cleaned_draft:
        cleaned_draft = f"### {sub_id} {sub_title}\n\n[LLM 响应为空，待补写]"

    if is_zero_chapter:
        cleaned_draft = _normalize_zero_chapter_content(cleaned_draft)

    if (not is_zero_chapter) and str(sub_id).endswith(".1"):
        cleaned_draft = _ensure_chapter_header_in_first_subsection(
            content=cleaned_draft,
            major_id=major_id,
            header_title=header_title or str(current_major.get("major_title", "")).strip(),
            lead=header_lead,
            opening_markdown=str(current_major.get("chapter_opening_markdown", "")).strip(),
        )

    if not is_zero_chapter:
        cleaned_draft = _ensure_image_blocks_in_draft(cleaned_draft, required_images)
    # 7. 更新状态树中的草稿 (方便UI树状展示)
    current_sub["draft_content"] = cleaned_draft


    actual_order = len(state.completed_sections) + 1

    state.completed_sections.append({
        "actual_order_index": actual_order,
        "major_title": major_title_clean,
        "sub_chapter_id": sub_id,
        "title": sub_title,
        "content": cleaned_draft
    })
    _save_llm_call_checkpoint(state, "node_writer")
    print(f"| | [OK] [Writer] 撰写完成！已生成 {len(cleaned_draft)} 字符。已存入线性历史第 {actual_order} 顺位。")
    return state


def node_overall_review(state: PaperWriterState) -> PaperWriterState:
    """
    Overall Reviewer Node: 总审稿师先给出各大章节审稿计划（上下文与规则文件选择）。
    """
    state.review_round += 1
    print(f"| [Node: OverallReview] 开始第 {state.review_round} 轮总审稿规划...")

    sections_payload = []
    major_map = {}
    review_library = getattr(state, "review_guidance_library", {})
    for sec in state.completed_sections:
        sub_id = str(sec.get("sub_chapter_id", ""))
        major_id = sub_id.split(".")[0] if "." in sub_id else "unknown"
        major_map.setdefault(major_id, {
            "major_chapter_id": major_id,
            "major_title": sec.get("major_title", ""),
            "sub_section_ids": []
        })
        major_map[major_id]["sub_section_ids"].append(sub_id)
        sections_payload.append({
            "sub_chapter_id": sub_id,
            "major_title": sec.get("major_title", ""),
            "title": sec.get("title", ""),
            "content": sec.get("content", "")
        })

    major_sections = list(major_map.values())

    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["overall_reviewer"].safe_substitute(
        topic=state.topic,
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        overall_review_rules=state.get_overall_review(),
        completed_sections=json.dumps(sections_payload, ensure_ascii=False, indent=2),
        major_sections=json.dumps(major_sections, ensure_ascii=False, indent=2),
        review_guidance_catalog=serialize_review_catalog(review_library),
    )

    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_overall_review")
    response_dict = _coerce_dict_or_none(response)
    if not response_dict:
        print("[WARN] [OverallReview] 未返回可解析JSON，回退为默认大章节审稿计划。")
        state.major_review_plans = []
        for major in major_sections:
            state.major_review_plans.append({
                "major_chapter_id": major.get("major_chapter_id", ""),
                "major_title": major.get("major_title", ""),
                "need_rewrite": True,
                "rewrite_rationale": "总审稿输出异常，回退为全量大章节复审",
                "required_context_section_ids": major.get("sub_section_ids", []),
                "review_guidance_keys": [k for k in review_library.keys() if k != "overall_review"],
                "review_focus": "默认全量审稿"
            })
        state.review_summary = "总审稿师输出非结构化，已使用默认计划。"
        return state

    state.review_summary = str(response_dict.get("global_summary", "")).strip()
    raw_plans = response_dict.get("major_review_plans", [])
    if not isinstance(raw_plans, list):
        raw_plans = []

    major_id_to_meta = {
        str(item.get("major_chapter_id", "")).strip(): item
        for item in major_sections
        if str(item.get("major_chapter_id", "")).strip()
    }

    normalized_plans = []
    for plan in raw_plans:
        if not isinstance(plan, dict):
            continue
        major_id = str(plan.get("major_chapter_id", "")).strip()
        if not major_id:
            continue
        major_meta = major_id_to_meta.get(major_id, {})

        required_context_ids = plan.get("required_context_section_ids", [])
        if not isinstance(required_context_ids, list):
            required_context_ids = []
        required_context_ids = [
            str(x).strip() for x in required_context_ids
            if str(x).strip()
        ]

        raw_review_keys = plan.get("review_guidance_keys", [])
        if not isinstance(raw_review_keys, list):
            raw_review_keys = []
        review_keys = []
        for key in raw_review_keys:
            key_str = str(key).strip()
            if key_str and key_str != "overall_review" and key_str in review_library and key_str not in review_keys:
                review_keys.append(key_str)

        normalized_plans.append({
            "major_chapter_id": major_id,
            "major_title": str(plan.get("major_title", "")).strip() or str(major_meta.get("major_title", "")).strip(),
            "need_rewrite": _coerce_bool(plan.get("need_rewrite", True), default=True),
            "rewrite_rationale": str(plan.get("rewrite_rationale", "")).strip(),
            "required_context_section_ids": required_context_ids,
            "review_guidance_keys": review_keys,
            "review_focus": str(plan.get("review_focus", "")).strip(),
        })

    state.major_review_plans = normalized_plans

    if state.review_summary:
        print(f"[INFO] [Overall Review Summary] {state.review_summary}")
        print(f"[INFO] [OverallReview] 生成大章节审稿计划: {len(state.major_review_plans)} 项")
    return state


def node_major_review(state: PaperWriterState) -> PaperWriterState:
    """
    Major Reviewer Node: 按总审稿计划对每个大章节执行一次审稿，并产出待重写小节。
    """
    print("\n| [Node: MajorReview] 开始逐大章节审稿...")
    review_library = getattr(state, "review_guidance_library", {})
    all_sections = state.completed_sections
    valid_ids = {sec.get("sub_chapter_id", "") for sec in all_sections}
    merged_review_items = []
    major_summaries = []
    reviewed_major_count = 0

    for plan in getattr(state, "major_review_plans", []):
        major_id = str(plan.get("major_chapter_id", "")).strip()
        major_title = str(plan.get("major_title", "")).strip()
        need_rewrite = _coerce_bool(plan.get("need_rewrite", True), default=True)
        rewrite_rationale = str(plan.get("rewrite_rationale", "")).strip()

        if not need_rewrite:
            msg = f"{major_id} {major_title}: 总审稿判定无需重写"
            if rewrite_rationale:
                msg = f"{msg}（{rewrite_rationale}）"
            major_summaries.append(msg)
            continue

        reviewed_major_count += 1
        required_context_ids = plan.get("required_context_section_ids", []) or []
        review_keys = plan.get("review_guidance_keys", []) or []
        review_focus = str(plan.get("review_focus", "")).strip()

        major_sections = [sec for sec in all_sections if str(sec.get("sub_chapter_id", "")).startswith(f"{major_id}.")]
        context_sections = [sec for sec in all_sections if sec.get("sub_chapter_id", "") in required_context_ids]
        if not context_sections:
            context_sections = major_sections

        selected_rules = []
        for key in review_keys:
            if key in review_library and key != "overall_review":
                selected_rules.append({"review_key": key, "content": review_library.get(key, "")})
        if not selected_rules:
            # fallback: infer by section titles
            inferred = []
            for sec in major_sections:
                k = _infer_review_key(sec, review_library)
                if k != "none" and k != "overall_review" and k not in inferred:
                    inferred.append(k)
            for key in inferred:
                selected_rules.append({"review_key": key, "content": review_library.get(key, "")})

        system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["major_reviewer"].safe_substitute(
            topic=state.topic,
            language=state.language,
            user_requirements=getattr(state, "user_requirements", ""),
            major_chapter_id=major_id,
            major_title=major_title,
            review_focus=review_focus,
            major_sections=json.dumps(major_sections, ensure_ascii=False, indent=2),
            required_context=json.dumps(context_sections, ensure_ascii=False, indent=2),
            review_guidance_catalog=serialize_review_catalog(review_library),
            review_guidance_payload=json.dumps(selected_rules, ensure_ascii=False, indent=2)
        )

        response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
        _save_llm_call_checkpoint(state, "node_major_review")
        response_dict = _coerce_dict_or_none(response)
        if not response_dict:
            major_summaries.append(f"{major_id} {major_title}: 非结构化输出")
            continue

        major_summary = str(response_dict.get("major_summary", "")).strip()
        if major_summary:
            major_summaries.append(f"{major_id} {major_title}: {major_summary}")
        for item in response_dict.get("sections_to_revise", []) or []:
            sub_id = str(item.get("sub_chapter_id", "")).strip()
            if sub_id in valid_ids:
                merged_review_items.append(item)

        # 章节标题/总起句专审
        if major_id != "0":
            major_outline = next((m for m in state.outline if str(m.get("major_chapter_id", "")).strip() == major_id), None)
            if major_outline:
                header_title = str(major_outline.get("chapter_header_title", major_outline.get("major_title", ""))).strip()
                header_lead = str(major_outline.get("chapter_header_lead", "")).strip()
                header_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["chapter_header_reviewer"].safe_substitute(
                    topic=state.topic,
                    language=state.language,
                    user_requirements=getattr(state, "user_requirements", ""),
                    major_chapter_id=major_id,
                    major_title=major_title,
                    chapter_header_title=header_title,
                    chapter_header_lead=header_lead,
                    major_sections=json.dumps(major_sections, ensure_ascii=False, indent=2),
                )
                header_resp = _call_llm_safe(system_input=header_prompt, thinking=False, model=state.model)
                _save_llm_call_checkpoint(state, "node_major_review")
                header_data = _coerce_dict_or_none(header_resp) or {}
                if bool(header_data.get("need_rewrite", False)):
                    merged_review_items.append({
                        "item_type": "chapter_header",
                        "major_chapter_id": major_id,
                        "sub_chapter_id": f"{major_id}.1",
                        "priority": str(header_data.get("priority", "medium")),
                        "issues": header_data.get("issues", []),
                        "rewrite_guidance": header_data.get("rewrite_guidance", {}),
                    })

    if reviewed_major_count == 0:
        state.reviewed_sections = []
        state.passed = True
        if major_summaries:
            state.review_summary = "\n".join(major_summaries)
        else:
            state.review_summary = "总审稿未选择任何需要重写的大章节。"
        print("[INFO] [MajorReview] 总审稿未指派需要细审的大章节，直接判定通过。")
        return state

    state.reviewed_sections = merged_review_items
    state.passed = len(merged_review_items) == 0
    if major_summaries:
        state.review_summary = "\n".join(major_summaries)
    print(f"[INFO] [MajorReview] 待重写小节数量: {len(state.reviewed_sections)}")
    return state


def node_rewrite(state: PaperWriterState, review_item: Dict[str, Any]) -> PaperWriterState:
    """
    Rewriter Node: 根据 reviewer 的结构化建议对目标小节执行定向重写。
    """
    if str(review_item.get("item_type", "")).strip() == "chapter_header":
        major_id = str(review_item.get("major_chapter_id", "")).strip()
        major_outline = next((m for m in state.outline if str(m.get("major_chapter_id", "")).strip() == major_id), None)
        if not major_outline:
            print(f"[WARN] [Rewrite] 未找到目标大章节: {major_id}")
            return state

        current_title = str(major_outline.get("chapter_header_title", major_outline.get("major_title", ""))).strip()
        current_lead = str(major_outline.get("chapter_header_lead", "")).strip()
        prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["chapter_header_rewriter"].safe_substitute(
            topic=state.topic,
            language=state.language,
            major_chapter_id=major_id,
            major_title=major_outline.get("major_title", ""),
            current_header_title=current_title,
            current_header_lead=current_lead,
            review_guidance=json.dumps(review_item, ensure_ascii=False, indent=2),
            research_gaps=state.research_gaps,
            existing_material=state.existing_material,
        )
        response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
        _save_llm_call_checkpoint(state, "node_rewrite")
        data = _coerce_dict_or_none(response) or {}
        new_title = str(data.get("chapter_header_title", "")).strip() or current_title
        new_lead = str(data.get("chapter_header_lead", "")).strip()

        major_outline["chapter_header_title"] = new_title
        major_outline["chapter_header_lead"] = new_lead
        major_outline["chapter_opening_markdown"] = _build_chapter_opening_markdown(major_id, new_title, new_lead)

        # 同步更新该大章节首个小节正文中的章节标题与总起句。
        target = next((sec for sec in state.completed_sections if sec.get("sub_chapter_id") == f"{major_id}.1"), None)
        if target:
            target["content"] = _ensure_chapter_header_in_first_subsection(
                content=target.get("content", ""),
                major_id=major_id,
                header_title=new_title,
                lead=new_lead,
                opening_markdown=str(major_outline.get("chapter_opening_markdown", "")).strip(),
            )
        print(f"| [OK] [Rewrite] 大章节 {major_id} 标题/总起句重写完成")
        return state

    sub_id = str(review_item.get("sub_chapter_id", "")).strip()
    target = next((sec for sec in state.completed_sections if sec.get("sub_chapter_id") == sub_id), None)
    if not target:
        print(f"[WARN] [Rewrite] 未找到目标小节: {sub_id}")
        return state

    print(f"| | [Node: Rewrite] 正在重写小节: {sub_id} {target.get('title', '')}")

    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["rewriter"].safe_substitute(
        topic=state.topic,
        language=state.language,
        sub_chapter_id=sub_id,
        sub_title=target.get("title", ""),
        original_content=target.get("content", ""),
        review_guidance=json.dumps(review_item, ensure_ascii=False, indent=2),
        existing_material=state.existing_material,
        research_gaps=state.research_gaps
    )

    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    _save_llm_call_checkpoint(state, "node_rewrite")
    rewritten = "" if response is None else str(response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    if not rewritten:
        print(f"[WARN] [Rewrite] 小节 {sub_id} 返回空结果，保留原稿。")
        return state

    if (not str(sub_id).startswith("0.")) and str(sub_id).endswith(".1"):
        major_id = str(sub_id).split(".")[0]
        major_outline = next((m for m in state.outline if str(m.get("major_chapter_id", "")).strip() == major_id), None)
        if major_outline:
            rewritten = _ensure_chapter_header_in_first_subsection(
                content=rewritten,
                major_id=major_id,
                header_title=str(major_outline.get("chapter_header_title", major_outline.get("major_title", ""))).strip(),
                lead=str(major_outline.get("chapter_header_lead", "")).strip(),
                opening_markdown=str(major_outline.get("chapter_opening_markdown", "")).strip(),
            )

    target["content"] = rewritten
    print(f"\t[OK] [Rewrite] 小节 {sub_id} 重写完成，长度 {len(rewritten)} 字符。")
    return state
