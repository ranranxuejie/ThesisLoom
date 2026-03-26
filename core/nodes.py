import json
import os
import glob
import re
from typing import Optional, Dict, Any
import requests
# 假设你的其他模块是这样组织的，请根据实际情况调整导入路径
from core.state import PaperWriterState, serialize_guidance_catalog, serialize_review_catalog
# 假设 call_doubao 函数放在 utils 或 llm 模块中
from core.llm import call_llm
from core.prompts import PROMPT_TEMPLATE


def _call_llm_safe(**kwargs) -> Any:
    try:
        return call_llm(**kwargs)
    except Exception as e:
        print(f"[WARN] LLM 调用失败: {e}")
        return None


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
    if isinstance(value, str):
        parsed = _extract_json_payload(value)
        if isinstance(parsed, list):
            return parsed
    return None


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
    if len(q) < 12:
        return False
    lowered = q.lower()
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
    queries = _coerce_list_or_none(response)
    if isinstance(queries, list):
        filtered = [q for q in queries if isinstance(q, str)]
        filtered = [q for q in filtered if _is_good_query(q)]
        filtered = _dedupe_queries(filtered)
        if filtered:
            return filtered[:8]

    # fallback: 保底规则生成，避免检索词过宽/过窄
    topic = _clean_query(state.topic)
    material_hint = _clean_query(" ".join(str(state.existing_material or "").split()[:20]))
    candidates = []
    if topic:
        candidates.append(topic)
    if topic and material_hint:
        candidates.append(f"{topic}; method and evaluation")
    return _dedupe_queries([q for q in candidates if _is_good_query(q)])[:4]


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


def _collect_research_gap_refs(folder: str) -> str:
    if not os.path.isdir(folder):
        return ""
    chunks = []
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            chunks.append(f"## {os.path.basename(path)}\n{content}")
    return "\n\n".join(chunks)


def node_search_query_builder(state: PaperWriterState) -> PaperWriterState:
    """
    Search Query Builder Node: 使用全量输入生成高质量检索词句列表。
    """
    print("\n[Node: SearchQueryBuilder] 生成关键检索词句...")
    queries = _build_search_queries_with_llm(state)
    if not queries:
        topic_hint = state.topic.strip() if state.topic.strip() else "research topic"
        queries = [topic_hint]

    state.search_queries = queries
    print(f"| [SearchQueryBuilder] 已生成检索词 {len(queries)} 条")
    return state


def _ensure_chapter_header_in_first_subsection(content: str, major_id: str, header_title: str, lead: str) -> str:
    text = str(content or "").strip()
    lines = text.splitlines()

    # 移除旧的大章节标题与旧总起段，保留到第一个三级标题开始。
    if lines and lines[0].strip().startswith("## "):
        i = 1
        while i < len(lines) and not lines[i].strip().startswith("### "):
            i += 1
        lines = lines[i:]

    rebuilt = [f"## {major_id}.{header_title}", ""]
    if str(lead).strip():
        rebuilt.extend([str(lead).strip(), ""])
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
        if re.match(r"^0\.\d+\s+", stripped):
            continue
        normalized_lines.append(line)

    return "\n".join(normalized_lines).strip()


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
    print(f"[OK] [SearchPaper] 已生成文献综述列表: {state.related_works_path}")
    return state


def node_chapter_header(state: PaperWriterState, current_major: Dict[str, Any]) -> PaperWriterState:
    """
    Chapter Header Node: 为大章节生成专用章节标题与总起句。
    """
    major_id = str(current_major.get("major_chapter_id", "")).strip()
    if major_id == "0":
        return state

    sub_sections_info = json.dumps(current_major.get("sub_sections", []), ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["chapter_header_builder"].safe_substitute(
        topic=state.topic,
        language=state.language,
        user_requirements=getattr(state, "user_requirements", ""),
        major_chapter_id=major_id,
        major_title=current_major.get("major_title", ""),
        major_purpose=current_major.get("major_purpose", ""),
        sub_sections_info=sub_sections_info,
        research_gaps=state.research_gaps if str(state.research_gaps).strip() else "暂无",
        existing_material=state.existing_material,
    )
    response = _call_llm_safe(system_input=prompt, thinking=False, model=state.model)
    data = _coerce_dict_or_none(response) or {}

    title = str(data.get("chapter_header_title", "")).strip() or str(current_major.get("major_title", "")).strip()
    lead = str(data.get("chapter_header_lead", "")).strip()

    current_major["chapter_header_title"] = title
    current_major["chapter_header_lead"] = lead
    print(f"[OK] [ChapterHeader] {major_id} 标题/总起句已生成")
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

    refs_material = _collect_research_gap_refs(state.research_gaps_refs_dir)
    topic_hint = state.topic.strip() if state.topic.strip() else "(题目缺省，请先给出可投稿标题并据此分析)"
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["research_gap_analyst"].safe_substitute(
        topic=topic_hint,
        language=state.language,
        user_requirements=state.user_requirements,
        related_works=related_works if related_works else "暂无相关文献列表",
        references_material=refs_material if refs_material else "暂无补充文献笔记",
    )
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    research_gap_md = "" if response is None else str(response).strip()
    if not research_gap_md:
        research_gap_md = "# Research Gaps and Contributions\n\n未生成结果，请手动补充。"

    with open(state.research_gap_output_path, "w", encoding="utf-8") as f:
        f.write(research_gap_md)

    state.research_gaps = research_gap_md
    print(f"[OK] [ResearchGaps] 已输出: {state.research_gap_output_path}")
    return state

def node_architect(state: PaperWriterState) -> PaperWriterState:
    """
    Node 1: 顶刊级学术架构师 (Lead Academic Architect)
    基于初始素材，精准界定研究领域，提取 Gap 与 Contribution，并规划 IMRaD 全局大纲。
    """
    print("\n" + "=" * 40)
    print("[RUN] 开始执行: 顶刊级学术架构规划...")
    print("=" * 40)

    # 1. 组装 User Prompt
    # 使用 safe_substitute 安全注入 State 中的变量
    topic_for_architect = state.topic if state.topic.strip() else "（题目未提供：请先自动构建一个高质量论文标题）"
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["architect"].safe_substitute(
        topic=topic_for_architect,
        existing_sections=state.existing_sections,
        existing_material=state.existing_material,
        research_gap_all=state.research_gaps,  # 注意映射到 state.research_gaps
        overall_guidance=state.get_overall_guidance(),
        language=state.language
    )

    # 3. 调用大模型底层函数
    print("[WAIT] 正在调用大模型生成全局架构大纲，请稍候...")
    result = _call_llm_safe(
        system_input=system_prompt,
        thinking=False,
        model=state.model,
    )

    # 4. 解析结果并更新状态 (State Management)
    outline = _coerce_list_or_none(result)
    if outline:
        # 将生成的关键信息写入 State
        state.outline = outline
        print("\n[OK] [Node 1] 执行成功！")
        print(f"\n[OK] [Architect] 执行成功！共规划了 {len(outline)} 个章节。")

    else:
        # 容错处理：当 LLM 空响应或非结构化时，使用保底 IMRaD 大纲继续流程。
        topic_hint = state.topic.strip() if state.topic.strip() else "Research Topic"
        fallback_outline = [
            {
                "major_chapter_id": "0",
                "major_title": "Front Matter",
                "major_purpose": "Provide title, abstract, and keywords.",
                "writing_order": 1,
                "sub_sections": [
                    {
                        "sub_chapter_id": "0.1",
                        "sub_title": "Title, Abstract, and Keywords",
                        "architecture_role": "Summarize study motivation, method, and key findings.",
                        "content_anchors": topic_hint,
                        "expected_words": 300,
                    }
                ],
            },
            {
                "major_chapter_id": "1",
                "major_title": "Introduction",
                "major_purpose": "Define problem context, research gap, and contributions.",
                "writing_order": 2,
                "sub_sections": [
                    {
                        "sub_chapter_id": "1.1",
                        "sub_title": "Background and Motivation",
                        "architecture_role": "Establish domain context and significance.",
                        "content_anchors": topic_hint,
                        "expected_words": 600,
                    },
                    {
                        "sub_chapter_id": "1.2",
                        "sub_title": "Research Gap and Contributions",
                        "architecture_role": "State unresolved issues and explicit contributions.",
                        "content_anchors": state.research_gaps,
                        "expected_words": 700,
                    },
                ],
            },
            {
                "major_chapter_id": "2",
                "major_title": "Methodology",
                "major_purpose": "Describe proposed framework and implementation details.",
                "writing_order": 3,
                "sub_sections": [
                    {
                        "sub_chapter_id": "2.1",
                        "sub_title": "System Framework",
                        "architecture_role": "Introduce architecture, modules, and workflow.",
                        "content_anchors": state.existing_material,
                        "expected_words": 900,
                    },
                    {
                        "sub_chapter_id": "2.2",
                        "sub_title": "Algorithm and Training Procedure",
                        "architecture_role": "Explain optimization objective, algorithm, and settings.",
                        "content_anchors": state.existing_material,
                        "expected_words": 900,
                    },
                ],
            },
            {
                "major_chapter_id": "3",
                "major_title": "Experiments and Results",
                "major_purpose": "Report setup, baselines, metrics, and empirical findings.",
                "writing_order": 4,
                "sub_sections": [
                    {
                        "sub_chapter_id": "3.1",
                        "sub_title": "Experimental Setup",
                        "architecture_role": "Describe datasets, baselines, and evaluation metrics.",
                        "content_anchors": state.existing_material,
                        "expected_words": 700,
                    },
                    {
                        "sub_chapter_id": "3.2",
                        "sub_title": "Main Results and Analysis",
                        "architecture_role": "Present quantitative and qualitative results.",
                        "content_anchors": state.existing_material,
                        "expected_words": 1000,
                    },
                ],
            },
            {
                "major_chapter_id": "4",
                "major_title": "Conclusion",
                "major_purpose": "Summarize findings, limitations, and future work.",
                "writing_order": 5,
                "sub_sections": [
                    {
                        "sub_chapter_id": "4.1",
                        "sub_title": "Conclusion and Future Work",
                        "architecture_role": "Conclude contributions and discuss outlook.",
                        "content_anchors": topic_hint,
                        "expected_words": 500,
                    }
                ],
            },
        ]
        state.outline = fallback_outline
        print("\n[WARN] [Node 1] 未获取合法章节 JSON，已切换为保底 IMRaD 大纲继续执行。")
        print(f"[OK] [Architect] 保底大纲已生成，共 {len(fallback_outline)} 个章节。")

    # 5. 返回更新后的状态机，供下一个节点使用
    return state


def node_planner(state: PaperWriterState, current_major: Dict) -> PaperWriterState:
    """
    Planner Node (Major Level): 接收整个大章节，一次性为下属【所有小节】生成段落蓝图与上下文路由。
    """
    major_title = current_major.get("major_title", "Unknown")
    print(f"\n[Node: Planner] 正在为大章节 [{major_title}] 统筹制定下属所有小节的蓝图与路由...")
    # 1. 提取所有小节的信息并转为易读的字符串，喂给大模型
    sub_sections_info = json.dumps(
        [{k: v for k, v in sub.items() if k != "draft_content"} for sub in current_major.get("sub_sections", [])],
        ensure_ascii=False, indent=2
    )
    # 2. 组装 Prompt (这里需要你的 PROMPT_PLANNER 升级为接受大章节下属所有小节信息的版本)
    # 系统提示词中，我们会要求模型输出一个包含多个对象的数组，每个对象对应一个 sub_chapter_id
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["planner"].safe_substitute(
        paper_outline=json.dumps(getattr(state, "outline", []), ensure_ascii=False),
        current_major_id=current_major.get("major_chapter_id", ""),
        major_title=major_title,
        major_purpose=current_major.get("major_purpose", ""),
        current_writing_order=current_major.get("writing_order", 99),
        sub_sections_info=sub_sections_info,  # 喂入该大章节下的所有小节概况
        overall_guidance=state.get_overall_guidance(),
        writing_guidance_catalog=serialize_guidance_catalog(getattr(state, "writing_guidance_library", {}))
    )
    # 3. 调用大模型
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
    response_dict = _coerce_dict_or_none(response)
    # 4. 解析结果并分发到各个小节的 state 中
    if response_dict and "plans" in response_dict:
        # 假设 LLM 返回格式为: {"plans": [{"sub_chapter_id": "2.1", "context_routing": {...}, ...}]}
        plans_list = response_dict.get("plans", [])

        # 将计划映射回大纲树中
        for sub in current_major.get("sub_sections", []):
            target_id = sub.get("sub_chapter_id")
            # 找到对应的规划结果
            matched_plan = next((p for p in plans_list if p.get("sub_chapter_id") == target_id), None)

            if matched_plan:
                sub["context_routing"] = matched_plan.get("context_routing", {})
                sub["paragraph_blueprints"] = matched_plan.get("paragraph_blueprints", [])
                sub["selected_guidance_key"] = matched_plan.get("selected_guidance_key", "none")
                sub["guidance_reason"] = matched_plan.get("guidance_reason", "")
                print(f"| 小节 [{target_id}] 蓝图与路由已挂载。")
            else:
                print(f"   [WARN] 未找到小节 [{target_id}] 的规划结果！")

        print(f"[OK] [Planner] 大章节 [{major_title}] 统筹规划完成！")
    else:
        print("[WARN] [Planner] 执行未完全成功，未能获取或解析合法的结构化响应。")
    return state


def node_writer(state: PaperWriterState, current_major: Dict, current_sub: Dict) -> PaperWriterState:
    """
    Writer Node (Sub Level): 根据 Planner 分发的蓝图，精准抽取前文 ID 对应的草稿，撰写正文并追加到线性历史记录中。
    """
    sub_id = current_sub.get('sub_chapter_id')
    sub_title = current_sub.get('sub_title')
    print(f"\t\t[Node: Writer] 正在撰写正文: {sub_id} {sub_title} ...")

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
    header_title = str(current_major.get("chapter_header_title", current_major.get("major_title", ""))).strip()
    header_lead = str(current_major.get("chapter_header_lead", "")).strip()
    guidance_key = str(current_sub.get("selected_guidance_key", "none")).strip()
    guidance_library = getattr(state, "writing_guidance_library", {})
    selected_guidance = guidance_library.get(guidance_key, "") if guidance_key != "none" else ""
    if not selected_guidance:
        selected_guidance = "未指定模块写作指导建议。"

    # 5. 组装 Prompt
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["writer"].safe_substitute(
        major_chapter_id=current_major.get("major_chapter_id", ""),
        major_title=current_major.get("major_title", ""),
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
        language=getattr(state, "language", "English"),
        user_requirements=getattr(state, "user_requirements", ""),
        is_zero_chapter="true" if is_zero_chapter else "false"
    )

    # 6. 调用大模型生成纯文本
    response = _call_llm_safe(system_input=system_prompt, thinking=False, model=state.model)
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
        )
    # 7. 更新状态树中的草稿 (方便UI树状展示)
    current_sub["draft_content"] = cleaned_draft


    actual_order = len(state.completed_sections) + 1

    state.completed_sections.append({
        "actual_order_index": actual_order,
        "major_title": current_major.get("major_title", ""),
        "sub_chapter_id": sub_id,
        "title": sub_title,
        "content": cleaned_draft
    })
    print(f"\t\t[OK] [Writer] 撰写完成！已生成 {len(cleaned_draft)} 字符。已存入线性历史第 {actual_order} 顺位。")
    return state


def node_overall_review(state: PaperWriterState) -> PaperWriterState:
    """
    Overall Reviewer Node: 总审稿师先给出各大章节审稿计划（上下文与规则文件选择）。
    """
    state.review_round += 1
    print(f"\n[Node: OverallReview] 开始第 {state.review_round} 轮总审稿规划...")

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
    response_dict = _coerce_dict_or_none(response)
    if not response_dict:
        print("[WARN] [OverallReview] 未返回可解析JSON，回退为默认大章节审稿计划。")
        state.major_review_plans = []
        for major in major_sections:
            state.major_review_plans.append({
                "major_chapter_id": major.get("major_chapter_id", ""),
                "major_title": major.get("major_title", ""),
                "required_context_section_ids": major.get("sub_section_ids", []),
                "review_guidance_keys": [k for k in review_library.keys() if k != "overall_review"],
                "review_focus": "默认全量审稿"
            })
        state.review_summary = "总审稿师输出非结构化，已使用默认计划。"
        return state

    state.review_summary = str(response_dict.get("global_summary", "")).strip()
    plans = response_dict.get("major_review_plans", [])
    if not isinstance(plans, list):
        plans = []
    state.major_review_plans = plans

    if state.review_summary:
        print(f"[INFO] [Overall Review Summary] {state.review_summary}")
        print(f"[INFO] [OverallReview] 生成大章节审稿计划: {len(state.major_review_plans)} 项")
    return state


def node_major_review(state: PaperWriterState) -> PaperWriterState:
    """
    Major Reviewer Node: 按总审稿计划对每个大章节执行一次审稿，并产出待重写小节。
    """
    print("\n[Node: MajorReview] 开始逐大章节审稿...")
    review_library = getattr(state, "review_guidance_library", {})
    all_sections = state.completed_sections
    valid_ids = {sec.get("sub_chapter_id", "") for sec in all_sections}
    merged_review_items = []
    major_summaries = []

    for plan in getattr(state, "major_review_plans", []):
        major_id = str(plan.get("major_chapter_id", "")).strip()
        major_title = str(plan.get("major_title", "")).strip()
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
        data = _coerce_dict_or_none(response) or {}
        new_title = str(data.get("chapter_header_title", "")).strip() or current_title
        new_lead = str(data.get("chapter_header_lead", "")).strip()

        major_outline["chapter_header_title"] = new_title
        major_outline["chapter_header_lead"] = new_lead

        # 同步更新该大章节首个小节正文中的章节标题与总起句。
        target = next((sec for sec in state.completed_sections if sec.get("sub_chapter_id") == f"{major_id}.1"), None)
        if target:
            target["content"] = _ensure_chapter_header_in_first_subsection(
                content=target.get("content", ""),
                major_id=major_id,
                header_title=new_title,
                lead=new_lead,
            )
        print(f"\t[OK] [Rewrite] 大章节 {major_id} 标题/总起句重写完成")
        return state

    sub_id = str(review_item.get("sub_chapter_id", "")).strip()
    target = next((sec for sec in state.completed_sections if sec.get("sub_chapter_id") == sub_id), None)
    if not target:
        print(f"[WARN] [Rewrite] 未找到目标小节: {sub_id}")
        return state

    print(f"\t[Node: Rewrite] 正在重写小节: {sub_id} {target.get('title', '')}")

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
    rewritten = "" if response is None else str(response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    if not rewritten:
        print(f"[WARN] [Rewrite] 小节 {sub_id} 返回空结果，保留原稿。")
        return state

    target["content"] = rewritten
    print(f"\t[OK] [Rewrite] 小节 {sub_id} 重写完成，长度 {len(rewritten)} 字符。")
    return state
