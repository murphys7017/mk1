# mk1 智能体系统
## 目前刚启动开发、未经过测试
## 项目简介

mk1 是一个具备“感知-记忆-推理-行动”完整认知闭环的智能体原型，支持多轮对话、长期记忆、摘要、遗忘等能力，目标是实现可持续成长、可自我调节的 AI 角色。

## 主要模块结构

- **PerceptionSystem**：负责输入文本的分析（如问题识别、实体提取、情感线索等），输出结构化 ChatMessage。
- **DateClass**：定义了 ChatMessage（单轮消息）、DialogueMessage（对话摘要）等核心数据结构。
- **RawChatHistory**：管理原始对话历史和摘要历史，支持文件持久化与追加写入。
- **DialogueStorage**：负责原始对话的缓冲、摘要生成与管理，集成本地/云端模型进行摘要与裁判。
- **MemoryStorage/MemoryAssembler/MemorySystem**：聚合 identity、对话摘要、近期对话，组装成 LLM 可用的 messages。
- **Aice (Alice)**：顶层智能体，集成感知、记忆、推理、行动，负责与用户交互。
# mk1 — Alice 智能体系统

轻量原型，目标是实现一个可持续成长的对话智能体：感知 → 记忆 → 推理 → 行动 → 记忆更新。

注意：项目处于开发中，部分模块为重构/接入阶段，参考 `docs/` 中的设计文档以获得更详细信息。

---

## 快速开始

1. 安装依赖（使用 `uv` 管理）：

```bash
uv sync
```

2. 在项目根目录创建 `.env`（可选）并填入你的 API Key：

```text
OPENAI_API_KEY=sk-...
# 或者在 shell 中导出环境变量
```

3. 运行程序：

```bash
uv run .\main.py
```

4. 交互：在命令行输入文本与 Alice 对话；输入 `退出` 结束会话。

---

## 本次更新要点

- `main.py` 已改为从环境变量读取 `OPENAI_API_KEY`（支持 `.env`）。
- `PerceptionSystem` 已并发化（`asyncio` + executor），输入协议统一为 `{"text": "..."}`。
- 引入 `LLM/` 目录以统一管理 Ollama / Qwen（云端）调用。
- `ContextAssembler/DefaultGlobalContextAssembler` 已能把 `MemorySystem.assemble()` 与 `ChatStateSystem.assemble()` 合并为 system prompt。
- `summarize_dialogue` 参数名问题已修复（`summary_text` / `dialogues_text` 对齐）。

---

## 项目结构概览

- `main.py` — 启动脚本、异步交互入口
- `Alice.py` — 顶层编排器（感知 → 记忆 → 组装 → LLM → 更新历史）
- `PerceptionSystem/` — 分析器注册与并发执行（目前包含 `text`）
- `DataClass/` — 领域模型（`ChatMessage`, `DialogueMessage`, `ChatState`, `PromptTemplate`, 等）
- `MemorySystem/` — 记忆策略、存储、组装（`MemoryPolicy`, `MemoryAssembler`, `MemoryStore`）
- `RawChatHistory/` — 历史持久化（SQLite / 文件）
- `LLM/` — LLM 抽象与具体实现（`Ollama`, `QwenFormated`, `LLMManagement`）
- `ContextAssembler/` — 全局 messages 组装器（system prompt + recent messages）
- `ChatStateSystem/` — 对话状态判断与 assemble 接口（默认实现在 `DefaultChatStateSystem.py`）
- `docs/` — 设计文档、TODO、项目总结、收尾清单

---

## 常见问题与提示

- 如果 LLM 不能正确生成摘要或决策：请确认 `SystemPrompt` 的 `PromptTemplate.required_fields` 与 `LLMManagement.generate()` 的命名一致（项目现在已修复 `summarize_dialogue` 的命名不一致问题）。

---

## 开发者指南（要点）

- 要跑通主链路，需要确保：
  - `main.py` 传入的输入遵循 `{ "text": "..." }` 格式；
  - `Alice` 初始化时注入 `DefaultGlobalContextAssembler`（使用 `MemorySystem` 与 `DefaultChatStateSystem`）；
  - `pyproject.toml` 中包含运行所需依赖（如 `python-dotenv`、`loguru`、`sqlalchemy`、`openai` 等）。

- 增加新 prompt 时：在 `SystemPrompt.load_template()` 注册 `PromptTemplate`，并在 `LLMManagement.generate()` 调用时使用与 `required_fields` 一致的关键字参数。

---

如需更详细的设计说明、模块间调用序列图或部署说明，请查看 `docs/项目总结.md` 与 `docs/集成收尾问题清单.md`。欢迎告诉我是否要我：

- 把 `DefaultGlobalContextAssembler` 注入 `Alice.respond()` 并完成主链路（我可以直接修改并跑一次静态检查）；
- 或者将 `python-dotenv` 添加到 `pyproject.toml` 的依赖中。
