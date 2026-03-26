import os
import sys
import time
import threading
import json
import requests
from typing import Any
from volcenginesdkarkruntime import Ark


def _load_llm_runtime_config_from_inputs() -> tuple[str, str]:
    candidate_paths = [
        "inputs/inputs_safe.json",
        "inputs_safe.json",
        "inputs.json",
        "inputs/inputs.json",
    ]
    inputs_path = ""
    for path in candidate_paths:
        if os.path.exists(path):
            inputs_path = path
            break

    if not os.path.exists(inputs_path):
        return "", ""

    try:
        with open(inputs_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return str(data.get("base_url", "")).strip(), str(data.get("model_api_key", "")).strip()
    except Exception:
        return "", ""

def call_llm(system_input: str,
             user_input: str="",
             json_schema: dict=None,
            #  model: str = "doubao-seed-2-0-pro-260215",
             model: str = "gemini-3-pro",
             thinking: bool = True,
             max_completion_tokens: int = 2**15,
             request_timeout: tuple[float, float] = (20.0, 240.0)) -> Any:
    cfg_base_url, cfg_model_api_key = _load_llm_runtime_config_from_inputs()

    # 用一个字典作为容器，用来在主线程和子线程之间传递结果或异常
    result_container = {}
    if 'doubao' in model:
        api_key = os.getenv("ARK_API_KEY") or cfg_model_api_key
        if not api_key:
            raise EnvironmentError("Please set ARK_API_KEY environment variable")
        client = Ark(base_url="https://ark.cn-beijing.volces.com/api/v3", api_key=api_key,timeout=1800)


        def _api_call():
            """这是一个将在后台运行的子线程函数"""
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_input},
                        {"role": "user", "content": user_input},
                    ],
                    max_completion_tokens=max_completion_tokens,
                    thinking={
                        "type": "enabled" if thinking else "disabled"
                    }
                )
                result_container['response'] = completion.choices[0].message.content
            except Exception as e:
                result_container['error'] = e

        print(f"\t\t\t[RUN] 发起模型请求 (模型: {model}, 思考模式: {'开启' if thinking else '关闭'})")

        # 1. 启动后台子线程执行耗时的 API 调用
        api_thread = threading.Thread(target=_api_call)

    else:
        base_url = os.getenv("LOCAL_API_URL") or cfg_base_url
        token = os.getenv("LOCAL_API_TOKEN") or cfg_model_api_key
        # --- 新增：调用你本地的 FastAPI 代理服务 ---
        if not base_url:
            raise EnvironmentError("Please set LOCAL_API_URL LOCAL environment variables")
        proxy_url = f"{base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": token if token else "ANY_TOKEN"
        }

        # 组装消息列表
        messages = []
        if system_input:
            messages.append({"role": "user", "content": system_input})

        payload = {
            "model": model,
            "messages": messages
        }

        def _proxy_call():
            try:
                full_content = ""
                # 使用 stream=True 接收流式返回
                with requests.post(
                    proxy_url,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=request_timeout,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith("data: "):
                                raw_data = decoded_line[6:].strip()
                                if raw_data == "[DONE]":
                                    break

                                try:
                                    data_obj = json.loads(raw_data)
                                    choices = data_obj.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})

                                        # 注意：这里我们只收集 'content'，主动忽略 'reasoning_content'
                                        # 因为我们要保证后续 json.loads() 能解析出干净的结构化数据
                                        if "content" in delta:
                                            full_content += delta["content"]
                                except json.JSONDecodeError:
                                    continue

                result_container['response'] = full_content
            except Exception as e:
                result_container['error'] = str(e)

        print(f"\t\t\t[RUN] 发起BaseURL请求 (模型: {model})")
        api_thread = threading.Thread(target=_proxy_call)
    # --- 共通逻辑：启动线程并渲染计时器 ---
    api_thread.start()
    start_time = time.time()

    while api_thread.is_alive():
        elapsed_time = time.time() - start_time
        sys.stdout.write(f"\r\t\t[WAIT] 等待模型响应中... 已耗时: {elapsed_time:.1f} 秒")
        sys.stdout.flush()
        time.sleep(0.02)
    total_time = time.time() - start_time
    sys.stdout.write(f"\r\t\t\t[OK] 请求完成！总耗时: {total_time:.1f} 秒" + " " * 10 + "\n")
    sys.stdout.flush()

    if 'error' in result_container:
        raise RuntimeError(f"LLM request failed: {result_container['error']}")

    response = result_container.get('response', '')
    if not str(response).strip():
        raise RuntimeError("LLM request returned empty response")


    try:
        # 核心：安全解析字符串为 JSON
        json_data = json.loads(response)
        # 保存为文件
        with open("demo.json","w+", encoding="utf-8") as f:
            json.dump(json_data,f,ensure_ascii=False,indent=2)
        return json_data
    except json.JSONDecodeError:
        return response


if __name__ == "__main__":
    try:
        resp = call_llm(system_input='''\n<Role>顶刊级学术架构师 (Lead Academic Architect)</Role>\n<Task>基于初始输入素材，规划出符合目标期刊风格的严密 IMRaD 全局大纲。你需要将论文拆解为一个由“大章节 (Major Sections)”组成的数组，并在每个大章节内部嵌套高精细度的“细分小节 (Sub-sections)”。同时，你需要像资深学者一样，为大章节制定最科学的【撰写优先级顺序】。</Task>\n\n<Context>\n研究题目：基于动态强化学习的城市交通信号自适应控制\n用户草稿：无\n实验成果：本次实验基于 SUMO (Simulation of Urban MObility) 搭建了超大规模微观交通流仿真平台，选取了具有高度拓扑复杂性的北京市三环路网核心区（包含 64 个信控交叉口，超过 300 条有向路段）作为测试基准。实验导入了由滴滴出行滴滴盖亚数据开放计划提供的连续 6 个月的真实百亿级车辆轨迹数据作为需求输入（Travel Demand）。在硬件上，算法训练部署于配备 8 张 NVIDIA A100 (80GB) GPU 的集群上，累计执行了超过 $5 \\times 10^6$ 个仿真时间步（Time Steps）。\n\n在核心的延迟指标上，本文提出的基于自适应奖惩机制的动态强化学习模型（ADRL-TSC）展现了压倒性的效能。具体而言，在平均交叉口延迟（Average Intersection Delay）方面，ADRL-TSC 相较于传统的定时控制（Fixed-Time, FT）与自适应执行器控制（Actuated Control, AC）分别降低了 45.2% 和 36.8%。在与顶尖深度强化学习基线算法的横向对比中，新模型比标准 DQN 降低了 28.4%，比 MAPPO (Multi-Agent PPO) 降低了 18.5%，比专门针对交通场景优化的 PressLight 算法降低了 11.2%。\n\n在应对极高流量波动的长尾压力测试（Tail-Risk Stress Test）中，我们模拟了突发性大型降雨天气（路面摩擦系数从 0.8 骤降至 0.4）叠加大型演唱会散场（$t=3600s$ 至 $t=5400s$ 局部流量生成率激增 400%）的极端非平稳场景。在此场景下，基线 MAPPO 算法在 $t=4100s$ 左右发生了明显的策略崩溃（Policy Collapse），导致路网内产生激波（Shockwave），最大排队长度飙升至 215 辆车，系统遭遇大面积死锁（Gridlock）。而 ADRL-TSC 凭借其内部的“自演化状态表征模块”，在 3 个信号周期内迅速调整了相位绿信比，成功将最大排队长度死死压制在 68 辆车以内，同时路网整体吞吐量（System Throughput）在极端时段内逆势提升了 22.4%。\n\n消融实验（Ablation Study）进一步验证了机制的有效性：移除“动态排队惩罚函数”后，算法在高并发期的延迟反弹了 15.6%；而切断“多智能体时空图注意力通信拓扑（Spatial-Temporal GAT）”后，相邻路口的协同效应完全丧失，导致绿波带（Green Wave）断裂，系统整体燃油消耗量（Fuel Consumption）和 CO2 排放量上升了约 14.3%。最终的奖励收敛曲线表明，ADRL-TSC 在经过 $1.2 \\times 10^5$ 个 episode 后即稳定收敛，方差极小。\n研究综述：尽管深度强化学习（Deep Reinforcement Learning, DRL）在智能交通信号控制（Intelligent Traffic Signal Control, ITSC）领域引发了范式重构，但面对具有高度时空非平稳性（Spatiotemporal Non-stationarity）的复杂城市路网，现有的研究成果仍暴露出三条难以逾越的理论鸿沟。\n\n首先，在奖励函数的工程设计上，当前 90% 以上的文献严重依赖静态、同质化的标量奖励（例如单纯以负的平均等待时间作为全局 Reward）。这种静态机制在平稳车流下尚可运行，但在极高流量波动或面临罕见的长尾交通事件（Corner Cases）时，极易引发严重的“奖励稀疏（Reward Sparsity）”与“信度分配灾难（Credit Assignment Problem）”。智能体往往为了追求短期局部吞吐量而牺牲路网整体稳定性，学界至今缺乏一种能够根据宏观拥堵指数动态自适应调节各子目标权重的弹性奖励函数。\n\n其次，多智能体强化学习（MARL）在交通路网部署中的“非平稳环境（Non-stationary Environment）”挑战依然未解。由于相连交叉口的 Agent 在同时更新各自的策略，某个交叉口的相位动作 $a_t$ 会直接改变下游交叉口的状态转移概率矩阵 $P(s\'|s,a)$。现有的独立 Q-learning (IQL) 方法完全无视了这种耦合作用，而基于集中式训练分布式执行（CTDE）框架的算法（如 QMIX 或 MADDPG）则在状态空间扩展至数十个交叉口时，遭遇了灾难性的维度爆炸（Curse of Dimensionality），导致计算复杂度呈指数级上升，几乎无法满足真实交通场景下 100 毫秒级的实时推理延迟要求。\n\n最后，现有研究在时空特征提取（Spatiotemporal Feature Extraction）上存在明显的视野局限。目前主流的方法大多采用图卷积网络（GCN）对路网进行拓扑建模，但这些模型通常仅关注静态的物理连接矩阵，而忽视了交通流激波（Traffic Shockwave）的动态传播时滞（Time-Delay）。这就导致模型对早晚高峰的突变流量预测严重滞后，无法在拥堵向外围蔓延前采取预防性的截流或疏导策略。如何将图神经网络与强化学习的价值函数评估深度绑定，实现对非欧几里得空间下动态交通流特征的零延迟感知，仍是该领域亟待攻克的终极痛点。\n期刊风格：目标期刊：IEEE Transactions on Intelligent Transportation Systems (T-ITS)。写作风格要求：1.【极度冷峻的客观主义】：严禁情绪化词汇，必须使用严谨定量描述（如 statistically significant）。2.【数据驱动】：任何观点必须紧跟数值或置信区间。3.【被动语态】：主语通常为无生命物体或模型，避免 \'We/I\'。4.【高密度逻辑链】：段落需遵循硬核逻辑递进，使用复杂复合句。5.【术语精准】：变量首次出现需全拼，后续统一缩写，描述需高度专业化（如将‘堵车’描述为‘交通流拥堵演化与局部死锁’）。 \n论文语言：中文\n</Context>\n\n<Rules>\n1. 宏观层规划 (Major Sections)：构建标准的 IMRaD 结构（如 1. Introduction, 2. Methods...）。每个大章节必须明确其在全局的核心目标。\n2. 动态写作策略 (Writing Order)：真实的学术写作通常非线性（如先锚定 Methods 和 Results，再推演 Discussion，最后包装 Introduction）。请为每个大章节分配 `writing_order`（从 1 开始的整数，不能重复），代表最合理的撰写先后顺序。\n3. 微观层深剖 (Sub-sections)：在大章节内部，必须将其拆解为逻辑严密的细分小节（如 2.1, 2.2）。这是保证内容精细度的核心。\n4. 颗粒度要求：细分小节的“内容锚点 (content_anchors)”必须极度具体，必须绑定 <Context> 中具体的实验数据、算法名称或需要填补的文献 Gap，杜绝泛泛而谈。\n5. 语言规范：严格使用 <Context> 指定的语言，保持冷峻、客观的顶刊学术语调。总字数控制在顶刊常规标准（约 4000-8000 字）。\n6. 格式红线 (Critical)：必须且只能输出一个合法的 JSON 数组 (Array)。绝对禁止任何前言后语、解释性文字，绝对禁止使用 Markdown 代码块（如 ```json）包裹！\n</Rules>\n\n<JSON_Schema>\n{\n  'type": "array",\n  "description": "按全文最终排版顺序排列的大章节数组 (Major Sections)",\n  "items": {\n    "type": "object",\n    "properties": {\n      "major_chapter_id": {\n        "type": "string",\n        "description": "大章节最终排版序号，如 \'1\', \'2\'"\n      },\n      "major_title": {\n        "type": "string",\n        "description": "大章节标题，如 \'Introduction\', \'Methods\'"\n      },\n      "writing_order": {\n        "type": "integer",\n        "description": "建议的撰写优先级序号（整数，从1开始递增）。例如优先写Methods设为1，Results设为2，最后写Introduction可能设为4"\n      },\n      "major_purpose": {\n        "type": "string",\n        "description": "宏观架构意图：该大章节在整篇论文逻辑链中承担的核心任务"\n      },\n      "sub_sections": {\n        "type": "array",\n        "description": "该大章节下的细分小节列表，用于保证极高的内容精细度和写作引导性",\n        "items": {\n          "type": "object",\n          "properties": {\n            "sub_chapter_id": {\n              "type": "string",\n              "description": "小节排版序号，如 \'1.1\', \'2.3\'"\n            },\n            "sub_title": {\n              "type": "string",\n              "description": "小节标题，如 \'Dataset and Preprocessing\'"\n            },\n            "architecture_role": {\n              "type": "string",\n              "description": "微观逻辑：该小节在当前大章节中的具体推演作用（例如：通过对比引出核心 Gap）"\n            },\n            "content_anchors": {\n              "type": "string",\n              "description": "高精度内容锚点：必须包含具体的实验数据指标、需要引用的文献特征或方法论细节，作为后续生成正文的直接弹药"\n            },\n            "expected_words": {\n              "type": "integer",\n              "description": "该小节的预期字数"\n            }\n          },\n          "required": ["sub_chapter_id", "sub_title", "architecture_role", "content_anchors", "expected_words"],\n          "additionalProperties": false\n        }\n      }\n    },\n    "required": ["major_chapter_id", "major_title", "writing_order", "major_purpose", "sub_sections"],\n    "additionalProperties": false\n  }\n}\n</JSON_Schema>\n''',
                        user_input=""
                        )
        print(resp)
    except Exception as e:
        print("Error:", e)
