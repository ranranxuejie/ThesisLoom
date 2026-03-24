# core/nodes.py

import json
from typing import Optional, Dict, Any
# 假设你的其他模块是这样组织的，请根据实际情况调整导入路径
from core.state import PaperWriterState

# 假设 call_doubao 函数放在 utils 或 llm 模块中
from core.llm import call_llm

from core.prompts import PROMPT_TEMPLATE

def node_architect(state: PaperWriterState) -> PaperWriterState:
    """
    Node 1: 顶刊级学术架构师 (Lead Academic Architect)
    基于初始素材，精准界定研究领域，提取 Gap 与 Contribution，并规划 IMRaD 全局大纲。
    """
    print("\n" + "=" * 40)
    print("🚀 开始执行: 顶刊级学术架构规划...")
    print("=" * 40)

    # 1. 组装 User Prompt
    # 使用 safe_substitute 安全注入 State 中的变量
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["architect"].safe_substitute(
        topic=state.topic,
        existing_sections=state.existing_sections,
        existing_material=state.existing_material,
        research_gap_all=state.research_gaps,  # 注意映射到 state.research_gaps
        journal_style=state.journal_style,
        language=state.language
    )

    # 3. 调用大模型底层函数
    print("⏳ 正在调用大模型生成全局架构大纲，请稍候...")
    result: Optional[dict] = call_llm(
        system_input=system_prompt,
        thinking=False,
        model=state.model,
    )

    # 4. 解析结果并更新状态 (State Management)
    if result:
        # 将生成的关键信息写入 State
        state.outline = result
        print("\n✅ [Node 1] 执行成功！")
        print(f"\n✅ [Architect] 执行成功！共规划了 {len(result)} 个章节。")

    else:
        # 容错处理：如果解析失败，可以抛出异常或在 state 中打上错误标记
        print("\n❌ [Node 1] 执行失败：未能获取合法的 JSON 响应。")

    # 5. 返回更新后的状态机，供下一个节点使用
    return state


def node_planner(state: PaperWriterState, current_major: Dict) -> PaperWriterState:
    """
    Planner Node (Major Level): 接收整个大章节，一次性为下属【所有小节】生成段落蓝图与上下文路由。
    """
    major_title = current_major.get("major_title", "Unknown")
    print(f"\n🧠 [Node: Planner] 正在为大章节 [{major_title}] 统筹制定下属所有小节的蓝图与路由...")
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
        sub_sections_info=sub_sections_info  # 喂入该大章节下的所有小节概况
    )
    # 3. 调用大模型
    response = call_llm(system_input=system_prompt, thinking=False, model=state.model)
    # 4. 解析结果并分发到各个小节的 state 中
    if response and isinstance(response, dict) and "plans" in response:
        # 假设 LLM 返回格式为: {"plans": [{"sub_chapter_id": "2.1", "context_routing": {...}, ...}]}
        plans_list = response.get("plans", [])

        # 将计划映射回大纲树中
        for sub in current_major.get("sub_sections", []):
            target_id = sub.get("sub_chapter_id")
            # 找到对应的规划结果
            matched_plan = next((p for p in plans_list if p.get("sub_chapter_id") == target_id), None)

            if matched_plan:
                sub["context_routing"] = matched_plan.get("context_routing", {})
                sub["paragraph_blueprints"] = matched_plan.get("paragraph_blueprints", [])
                print(f"   ↳ 小节 [{target_id}] 蓝图与路由已挂载。")
            else:
                print(f"   ⚠️ 未找到小节 [{target_id}] 的规划结果！")

        print(f"✅ [Planner] 大章节 [{major_title}] 统筹规划完成！")
    else:
        print("⚠️ [Planner] 执行未完全成功，未能获取或解析合法的结构化响应。")
    return state


def node_writer(state: PaperWriterState, current_major: Dict, current_sub: Dict) -> PaperWriterState:
    """
    Writer Node (Sub Level): 根据 Planner 分发的蓝图，精准抽取前文 ID 对应的草稿，撰写正文并追加到线性历史记录中。
    """
    sub_id = current_sub.get('sub_chapter_id')
    sub_title = current_sub.get('sub_title')
    print(f"\t\t✍️ [Node: Writer] 正在撰写正文: {sub_id} {sub_title} ...")

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

    # 5. 组装 Prompt
    system_prompt = PROMPT_TEMPLATE[state.get_prompt_language()]["writer"].safe_substitute(
        major_chapter_id=current_major.get("major_chapter_id", ""),
        major_title=current_major.get("major_title", ""),
        sub_chapter_id=sub_id,
        sub_title=sub_title,
        architecture_role=current_sub.get("architecture_role", ""),
        content_anchors=current_sub.get("content_anchors", ""),
        expected_words=current_sub.get("expected_words", ""),
        paragraph_blueprints=blueprints_str,
        existing_material=context_material,
        research_gap_all=context_gap,
        existing_sections=context_sections,  # 精准喂入的前文
        language=getattr(state, "language", "English"),
        journal_style=getattr(state, "journal_style", "Nature/Science sub-journal style"),
        user_requirements=getattr(state, "user_requirements", ""),
        is_zero_chapter="true" if is_zero_chapter else "false"
    )

    # 6. 调用大模型生成纯文本
    response = call_llm(system_input=system_prompt, thinking=False, model=state.model)
    cleaned_draft = str(response).strip().removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
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
    print(f"\t\t✅ [Writer] 撰写完成！已生成 {len(cleaned_draft)} 字符。已存入线性历史第 {actual_order} 顺位。")
    return state
