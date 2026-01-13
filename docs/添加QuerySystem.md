明白 👍
结论我先给你一句**非常明确的话**，然后再给一个**设计时的检查清单**，你照着这个清单实现，基本不会走歪。

---

## 结论先行（重点）

**你的思路是对的，而且是“能长期用、不需要推翻”的那种对。**

你现在这套想法，已经满足三个非常关键的工程标准：

1. **决策前置**
   你没有把“要不要查、查什么”塞给 LLM，而是明确要产出一个 QueryPlan / QuerySchema ——这是整个系统能控的前提。

2. **职责分离清楚**

   * AnalyzeResult：只负责“语言信号是什么”
   * QuerySchema / Plan：只负责“该不该、查哪里、用什么条件”
   * Executor：只负责“照计划拿证据”
   * Assembler：只负责“拼上下文”

   这条线一旦成立，后面加 RAG、加环境、加用户信息都不会互相污染。

3. **能处理低信息输入（这是大多数系统会翻车的地方）**
   你已经意识到“在吗”这种输入不能直接走检索，这一点非常关键。

所以一句话：
👉 **你现在不是在赌设计，而是在按正确方向收敛。**

---

## 明天你实现时，请拿这个“硬检查清单”对照

只要下面每一条你都能打勾，你的实现就一定是健康的。

---

### ✅ 1. QuerySchema / QueryPlan 是“纯数据结构”

* 不访问数据库
* 不做相似度搜索
* 不 include prompt
* 只描述：

  * intent / 信息密度
  * 允许的 sources
  * tags / query / topk / ttl / budget
  * fallback / reasons

> 如果你发现 QuerySchema 里开始出现 “get / fetch / search / db” 之类的行为，那就是越界了。

---

### ✅ 2. **所有检索都必须由 QuerySchema 授权**

实现时请自问一句话：

> “如果我删掉这一轮的 QuerySchema，这个系统还能不能偷偷查点东西？”

如果答案是 **不能**，那你做对了。

---

### ✅ 3. Executor 是“严格执行者”，不是“聪明人”

Executor 只做这些事：

* 遍历 schema.sources
* 对每个 source 执行 schema 里声明的 query / filters
* 裁剪到 topk / token_budget
* 检查 ttl（环境信息）

它 **不允许**：

* 自己决定“这个好像也该查”
* 自己扩大 topk
* 自己加新 source

---

### ✅ 4. ContextAssembler 里 **不出现任何判断逻辑**

Assembler 里只能有：

* include WORLD_CORE
* include executor 返回的 blocks
* include chat_state / analyze / protocol
* append history

如果你在 Assembler 里写了：

```python
if xxx:
    查点什么
```

那说明职责已经混了。

---

### ✅ 5. 低信息输入一定要有“硬闸门”

你实现完后，拿这几个输入手动测：

* 「在吗」
* 「？」
* 「嗯」
* 「hello」

期望行为：

* QuerySchema 明确标记：low signal
* retrieve = False
* 只注入 WORLD_CORE
* **绝不触发任何检索**

如果这点成立，你整个系统会非常稳。

---

## 一个给你安心用的判断标准

你可以用这一句话来判断“我现在是不是写偏了”：

> **我现在写的这段代码，是在“描述计划”，还是在“偷偷执行计划”？**

* 描述 → 对（QuerySchema / Planner）
* 执行 → 对（Executor）
* 偷偷执行 → 错（通常是 Assembler 或 Builder 里）

---

## 最后一句（很重要）

你现在做的这一步，本质上是在给系统**加一个“前额叶”**：
先想清楚，再行动。

这一步做对了，后面所有复杂度（RAG、环境、长期记忆）都是**线性叠加**，而不是指数爆炸。

你明天直接照这个思路实现就行；等你写完哪怕一半，贴出来，我可以帮你做一次**“是否符合目标态”的校验 review**，只看结构，不抠细节。
