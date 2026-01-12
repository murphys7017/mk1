from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptNode:
    """
    Prompt AST 节点（自动缩进基于 depth）：
    - text: 输出文本（可多行；容器节点 text="" 且 kind="container" 时不输出空行）
    - priority: 同级排序（越大越靠前）
    - children: 子节点
    - parent: 父节点（用于 depth）
    - enabled: 是否输出
    - meta: 元信息（tag、kind 等）
    """
    text: str = ""
    priority: int = 0
    children: list["PromptNode"] = field(default_factory=list)
    parent: Optional["PromptNode"] = None
    enabled: bool = True
    meta: dict = field(default_factory=dict)

    @property
    def depth(self) -> int:
        if not self.parent:
            return 0
        return self.parent.depth + 1

    def add_child(self, node: "PromptNode") -> "PromptNode":
        node.parent = self
        self.children.append(node)
        return node

    def clone(self) -> "PromptNode":
        """深拷贝整棵子树（不共享引用），用于 include/extend 合并"""
        new = PromptNode(
            text=self.text,
            priority=self.priority,
            parent=None,
            enabled=self.enabled,
            meta=dict(self.meta),
        )
        for c in self.children:
            new.add_child(c.clone())
        return new
