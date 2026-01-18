# mk1 — Alice 智能体系统

轻量原型，目标是实现一个可持续成长的对话智能体：感知 → 记忆 → 推理 → 行动 → 记忆更新。

当前代码已迁移为 `src/` layout（核心模块在 `src/` 下），并引入 Prompt 构建系统用于可组合地拼装 system prompt。

---

## 快速开始

1. 安装依赖（使用 `uv` 管理）：

```bash
uv sync
```

1. 在项目根目录创建 `.env`（可选）并填入你的 API Key：

```text
OPENAI_API_KEY=sk-...
# 或者在 shell 中导出环境变量
```

1. 运行程序：

```bash
uv run .\main.py
```

1. 交互：在命令行输入文本与 Alice 对话；输入 `退出` 结束会话。

---

## 当前主链路（概览）

- `main.py` 读取 `.env`/环境变量 → `Alice.respond()`
- `PerceptionSystem` 并发分析：OllamaAnalyze + LTP → 合并为 `AnalyzeResult`
- `QuerySystem` 构建 `QuerySchema` 并挂载到 user `ChatMessage`（用于后续检索/路由决策）
- 写入 SQLite 历史（支持 `AnalyzeResult` 关联）
- `DefaultGlobalContextAssembler` 用 PromptBuilder 组装 system prompt（Memory + ChatState + Analyze + ResponseProtocol）并拼接 recent history
- `LLMManagement.chat()` 走本地 Ollama chat 生成回复；回合后通过 EventBus 触发摘要/状态更新，并异步调度 PostTreatmentSystem

---

## 项目结构概览

- `main.py` — 启动脚本、异步交互入口
- `src/Alice.py` — 顶层编排器（感知 → 记忆 → 组装 → LLM → 更新历史）
- `src/PerceptionSystem/` — 分析器注册与并发执行（OllamaAnalyze + LTP）
- `src/QuerySystem/` — QuerySchema 构建（signal density、intent、检索模式等）
- `src/DataClass/` — 领域模型（`ChatMessage`, `AnalyzeResult`, `DialogueMessage`, `ChatState`, `PromptTemplate` 等）
- `src/MemorySystem/` — 记忆策略、存储、组装（`MemoryPolicy`, `MemoryAssembler`, `MemoryStore`）
- `src/RawChatHistory/` — 历史持久化（SQLite / 文件）
- `src/LLM/` — LLM 抽象与实现（`OllamaFormated`, `OllamaChat`, `LLMManagement`）
- `src/ContextAssembler/` — 全局 messages 组装器（PromptBuilder + recent history）
- `src/ChatStateSystem/` — 对话状态判定与 assemble
- `src/PostTreatmentSystem/` — 回合后处理（PostHandleSystem + handlers；可扩展 Live2D 等外部输出）
- `src/Transport/` — 传输层（WebSocket server 等实验性接口）
- `src/tools/` — PromptBuilder、normalize 工具等
- `tests/` — 基础单测
- `docs/` — 设计文档、TODO、项目总结、收尾清单

---

## 常见问题与提示

- 如果结构化生成（摘要/裁判）输出为空：请确认 `SystemPrompt` 的 `PromptTemplate.required_fields` 与 `LLMManagement.generate()` 传参名一致。

## 运行测试

```bash
uv run pytest
```

---

## 开发者指南（要点）

- 要跑通主链路，需要确保：
  - `main.py` 传入的输入遵循 `{ "text": "..." }` 格式；
  - `Alice` 初始化时注入 `DefaultGlobalContextAssembler`（使用 `MemorySystem` 与 `DefaultChatStateSystem`）；
  - `QuerySystem` 已接入主链路（QuerySchema 目前主要运行时使用，后续可打通检索/工具调用闭环）；
  - 回合后通过 `PostTurnProcessor` 异步调度 `PostTreatmentSystem`（可按需补齐完成事件消费与产物落点）；
  - `pyproject.toml` 中包含运行所需依赖（如 `python-dotenv`、`loguru`、`sqlalchemy`、`openai` 等）。

- 增加新 prompt 时：在 `SystemPrompt.load_template()` 注册 `PromptTemplate`，并在 `LLMManagement.generate()` 调用时使用与 `required_fields` 一致的关键字参数。

- 若使用外置 prompt：`config/system_prompt.yaml` 可作为固定 prompt 文本的入口；建议明确与代码 builder 的“单一来源”，避免双源漂移。

---

更详细的设计说明与进展：

- `docs/项目总结.md`
- `docs/阶段进展-2026-01-19.md`
- `docs/集成收尾问题清单.md`
