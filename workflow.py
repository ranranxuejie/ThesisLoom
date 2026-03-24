from core.state import PaperWriterState
from core.nodes import node_architect, node_planner,node_writer
import json,os,re
os.makedirs("completed_history", exist_ok=True)
initial_inputs = json.load(open("inputs/inputs.json", "r", encoding="utf-8-sig"))
state = PaperWriterState(initial_inputs)

state = node_architect(state)
writing_queue = sorted(state.outline, key=lambda x: x["writing_order"])

for major_chapter in writing_queue:
    print(f"\n==================================================")
    print(f"🚀 进入大章节: {major_chapter['major_title']} (优先级: {major_chapter['writing_order']})")
    print(f"==================================================")

    # --- 改变点：Planner 提升到这里！一次性规划当前大章节里的所有小节 ---
    state = node_planner(state, major_chapter)

    # --- 然后遍历小节，挨个让 Writer 撰写 ---
    for sub_section in major_chapter.get("sub_sections", []):
        state = node_writer(state, major_chapter, sub_section)
        # 实时保存线性历史记录，防止崩溃
        completed_thesis = sorted(state.completed_sections, key=lambda x: x["sub_chapter_id"])
        completed_thesis = [sec["content"] for sec in completed_thesis]
        completed_thesis = "\n\n".join(completed_thesis)
        # 保存为Markdown文件
        safe_topic = re.sub(r'[\\/*?:"<>|]', '', state.topic)
        safe_topic = safe_topic.replace(" ", "_")
        with open(f"completed_history/{state.model}_{safe_topic}_{state.get_prompt_language()}.md", "w", encoding="utf-8") as f:
            f.write(completed_thesis)
