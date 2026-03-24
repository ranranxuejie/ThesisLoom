# 传统大型语言模型（LLMs）在长篇学术写作中的局限
虽然当前以Gemini-3-Pro和GPT-4为代表的LLMs在单一回答或短篇合成中表现优异，但在生成长达数万字的规范化“完整长篇学术论文”时，面临以下明显的research gaps：

1. **上下文遗忘与连贯性坍塌 (Context Degradation & Coherence Collapse)**：传统的基于自回归机制的长文本生成往往只能捕获局部注意力，在经过漫长的生成后，其逻辑路线极易偏离初始目标和规划（Drifting off-topic）。
2. **缺乏多视角的评判-修改迭代机制 (Lack of Multi-Actor Review-Revise Iterative Capability)**：学术写作是一个需要“规划-起草-审稿-修改”多次循环的深度任务。现有的单次推理或Few-shot Prompt无法内生实现真正的“局部批判性反馈（Critic）”以及根据反馈做针对性重构的能力。
3. **结构一致性的松散 (Structural Laxity)**：各小节、段落间的情境、指代和专业术语的一致性很难跨越大量Token进行维持。
4. **事实性审查的黑盒困境 (Factuality Assurance)**：缺乏结构化的控制通道来保证长文档中的推演逻辑严格符合给定的理论框架和外部素材，容易产生逻辑断裂和知识幻觉。
因此，开发一种高度模块化的状态图多智能体系统（如 ThesisLoom），对大模型推理流进行强制解耦和流程控制，成了迫切的研究空白。
