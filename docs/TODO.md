# TODO 任务清单

## 2026年1月6日 时间14:30:00

- [ ] 将输入和输出分开，做到可以多次输入，然后ai看情况输出
  - [ ] 实现类似管线化或者其他的方式
- [ ] 添加文本转语音 和 语音转文本功能 做到可以和ai语音交流
- [ ] 设计长期记忆模块，做到ai至少可以记住用户的基本信息



## 2026年1月8日 02点54分

- [ ] 修改ChatMessage、PerceptionSystem等添加对多模态的支持创建AnalysisResult类，ChatMessage的content只是文本，新加属性等（已完成：AnalyzeResult/字段预留/SQLite 持久化；未完成：图片/音频/视频分析器与端到端接线）
- [x] ltp安装完成为PerceptionSystem添加ltp分析
- [x] 将分析结果体现在prompt中，而非message（已完成：AnalyzeResult 以轻量信号注入 system prompt，同时仍会落库）
- [x] 添加标签语义说明（TagType + ResponseProtocol + 语义说明草案）

## 2026年1月11日

- [x] 修复/统一 LLMManagement 的 `model_map` 与 `llm_map`（已重构为 `generate()`/`chat()` 双入口）
- [x] 明确“结构化 JSON 输出”与“自然语言回复”两条调用链（OllamaFormated vs OllamaChat）
- [x] 清理数据模型并存状态（`MessageModel.py` 已移除，统一使用 `src/DataClass/`）

NOTE: `python-dotenv` 已补齐（或已移除），相关依赖与 `.env` 使用已处理并加入 .gitignore。

## 2026年1月13日

- [x] 目录结构重构为 `src/` layout，并补充基础测试用例（PromptBuilder/normalize/ltp/AnalyzeResult merge 等）
- [x] 引入 Prompt 构建系统（PromptBuilder + PromptNode），支持 include/extend/tag/container 的组合式拼装
- [ ] 清理/确认 import 风格与包结构一致性（避免“直接运行 vs 安装为包”时导入差异）

## 2026年1月19日

- [x] 引入 QuerySystem（QuerySchema + property builders），并在主链路为 user 消息生成 query_schema
- [x] 引入 PostTreatmentSystem（PostHandleSystem + Live2D Motion3Builder），并接入 PostTurnProcessor 异步调度
- [x] RawChatHistory 增加近期 history/dialogue 内存缓存，减少频繁读库
- [x] 对话摘要决策升级为 SummaryDecision（支持 merge/new），并尽量异步触发摘要更新
- [ ] QuerySchema 驱动检索/工具调用闭环：从 query_schema.retrieve/mode/top_k 触发实际检索/筛选/注入上下文
- [ ] QuerySchema 落库与回放：确定是否写入 SQLite（extra/json 列）或单独表，以便调试与评估
- [ ] system_prompt.yaml 收敛为单一来源：统一 prompt 文本、required_fields、输出 schema，并实现安全字段替换（仅替换 required_fields）
- [ ] LLMManagement 映射策略收敛：按配置映射 vs supportModel()/自动发现，选定并固化
- [ ] PostTreatmentSystem 可靠性：handler 失败隔离/重试/幂等策略，补齐 POST_HANDLE_COMPLETED 的消费逻辑

~~~json
{
  "strategy": {
    "interaction": "...",
    "user_attitude": "...",
    "emotional_state": "...",
    "leading_approach": "...",
    "updated_every_n_turns": 4,
    "last_updated_turn": 12
  },
  "perception": {
    "is_question": false,
    "mentions_assistant": true,
    "sentiment": {"label": "pos", "score": 0.82},
    "topics": ["affection"],
    "entities": {"person": [], "org": [], "loc": []},
    "turn_id": 13
  }
}

----

你会收到若干 XML-like 标签块，它们是系统提供的上下文，不要在回复中显式提及标签名或逐字复述标签内容。

标签语义：
- <IDENTITY_CORE>：核心身份与长期自我约束，最高优先级，不可违背。
- <WORLD_SETTING>：世界设定/运行规则，仅次于核心身份，不随用户请求改变。
- <RESPONSE_PROTOCOL>：回答格式与规范，需严格遵守。
- <IMEMORY_LONG>：长期记忆摘要，可用于个性化，但不应虚构未给出的事实。
- <MEMORY_MID>：中期记忆摘要，优先用于保持话题连续与上下文一致。
- <CHAT_STATE>：对话状态（策略/情绪/引导方式等），用于调整语气与策略，不是事实来源。
- <KNOWLEDGE>：显式知识/背景信息，用于补充解释。

使用原则：遵循优先级；当标签内容冲突时，以更高优先级为准；不要把记忆当作硬性规则。


~~~

