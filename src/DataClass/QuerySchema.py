"""
DataClass.QuerySchema 的 Docstring
查询模式的定义，主要用于区分不同类型的查询请求。
类似信息密度，查询那些记忆，查询参数等
ueryPlan 是一个强 schema 的结构体，它必须回答这些问题：

这轮输入的 意图是什么

输入的信息密度属于哪一档（low / mid / high）

是否允许检索

允许检索哪些信息源

允许使用哪些主题标签

用什么 query（或不用）

最多取多少条

是否需要 TTL

允许注入多少 token

失败时如何回退

为什么做出这些决定（reasons）
"""