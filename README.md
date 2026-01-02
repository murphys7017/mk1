# mk1 智能体系统
## 目前刚启动开发、未经过测试
## 项目简介

mk1 是一个具备“感知-记忆-推理-行动”完整认知闭环的智能体原型，支持多轮对话、长期记忆、摘要、遗忘等能力，目标是实现可持续成长、可自我调节的 AI 角色。

## 主要模块结构

- **PerceptionSystem**：负责输入文本的分析（如问题识别、实体提取、情感线索等），输出结构化 ChatMessage。
- **MessageModel**：定义了 ChatMessage（单轮消息）、DialogueMessage（对话摘要）等核心数据结构。
- **RawChatHistory**：管理原始对话历史和摘要历史，支持文件持久化与追加写入。
- **DialogueStorage**：负责原始对话的缓冲、摘要生成与管理，集成本地/云端模型进行摘要与裁判。
- **MemoryStorage/MemoryAssembler/MemorySystem**：聚合 identity、对话摘要、近期对话，组装成 LLM 可用的 messages。
- **Aice (Alice)**：顶层智能体，集成感知、记忆、推理、行动，负责与用户交互。

## 主要特性

- **多轮对话与长期记忆**：支持原始对话与摘要分层管理，摘要可持续追加与合并。
- **可扩展的感知与分析**：PerceptionSystem 可扩展为多模态输入，当前已支持文本分析。
- **本地/云端模型摘要**：支持通过本地 Ollama 或云端大模型进行摘要与裁判。
- **记忆遗忘机制（规划中）**：支持对超长、超时、低权重记忆的自动遗忘。
- **可持续成长的 AI 角色**：Identity/Persona 可长期演化，具备自我调节能力。

## 目录结构

- `Aice.py`                智能体主入口
- `PerceptionSystem/`      感知系统
- `MemorySystem/`          记忆系统（含存储、组装、摘要等）
- `MessageModel.py`        消息与摘要数据结构
- `RawChatHistory.py`      历史管理与持久化
- `LocalModelFunc.py`      本地模型API调用与摘要/裁判逻辑
- `docs/`                  设计文档与开发计划

## 快速开始

1. 安装依赖：
   ```shell
   uv sync
   ```
2. 运行主程序：
   ```shell
   uv run .\main.py
   ```
3. 按照命令行提示与 Alice 进行多轮对话。

## 开发计划（见 docs/TODO.md）
- [ ] 启动时自动加载历史摘要
- [ ] 测试摘要系统
- [ ] 设计并实现遗忘机制

## 设计理念摘录

- 认知闭环：感知→记忆→推理→行动→记忆更新，模拟真实智能体的成长与遗忘。
- 记忆分层：Identity/World/Episodic/Semantic/Dialogue/Meta，支持多种类型的长期与短期记忆。
- 摘要与裁判分离：先判断是否需要摘要，再决定如何摘要，提升记忆质量。
- 可持续成长：每次对话都能影响 AI 的长期行为和个性。

---

如需详细设计与原理说明，请参考 docs/1.md、2.md、3.md 及 DialogueStorage AI评价.md。
