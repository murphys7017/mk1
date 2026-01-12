from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from DataClass.PromptNode import PromptNode


def _tag_name(tag: Any) -> str:
    return tag.value if hasattr(tag, "value") else str(tag)


@dataclass
class NodeRef:
    """
    你想要的“节点操作句柄”：
    - add(): 往节点内部加文本（子项）
    - tag(): 往节点内部加标签块（子项）
    - container(): 往节点内部加纯容器（子项）
    - include(x): 把 x 作为子项挂到本节点内部
    - extend(x): 把 x 作为兄弟节点挂到本节点同级
    """
    builder: "PromptBuilder"
    node: PromptNode

    # ---------- content ----------
    def add(
        self,
        text: str,
        *,
        priority: int = 0,
        enabled: bool = True,
        meta: Optional[dict] = None,
    ) -> "NodeRef":
        child = self.builder._add_text(text, parent=self.node, priority=priority, enabled=enabled, meta=meta)
        return NodeRef(self.builder, child)

    # ---------- nested constructs ----------
    def tag(
        self,
        tag: Any,
        *,
        priority: int = 0,
        enabled: bool = True,
        meta: Optional[dict] = None,
    ) -> "NodeRef":
        return self.builder._create_tag(tag, parent=self.node, priority=priority, enabled=enabled, meta=meta)

    def container(
        self,
        *,
        priority: int = 0,
        enabled: bool = True,
        meta: Optional[dict] = None,
    ) -> "NodeRef":
        return self.builder._create_container(parent=self.node, priority=priority, enabled=enabled, meta=meta)

    # ---------- composition ----------
    def include(self, item: Any, *, clone: bool = True) -> "NodeRef":
        """include: 把 item 挂到本节点内部（子项）"""
        self.builder._include_into_parent(item, parent=self.node, clone=clone)
        return self

    def extend(self, item: Any, *, clone: bool = True) -> "NodeRef":
        """extend: 把 item 挂到本节点同级（兄弟）"""
        self.builder._extend_as_sibling(item, sibling_of=self.node, clone=clone)
        return self


class PromptBuilder:
    """
    最终 DSL（完全匹配你的设想）：

    - b = PromptBuilder("PROMPT")     # 有根标签
      b.add("...")                    # 加到 <PROMPT> 内
      b.tag("MEMORY").add("...")      # <MEMORY> 内加文本
      b.extend(other)                 # 在 <PROMPT> 的同级增加 other
      b.include(other)                # 把 other 放进 <PROMPT> 内

    - tmp = PromptBuilder()           # 无根标签：纯容器/临时存储
      tmp.tag("X").add("...")
      b.include(tmp)                  # 把 tmp 的根节点们挂进去
    """

    def __init__(self, root_tag: Optional[Any] = None, *, indent_size: int = 2, newline: str = "\n"):
        self.indent_size = indent_size
        self.newline = newline
        self.roots: list[PromptNode] = []
        self._seq = 0

        # root_ref: 你日常写 b.add/b.tag/b.include 的默认目标
        if root_tag is None:
            # 没指定标签：builder 自身就是“纯容器”，不会渲染自己的标签
            self._root_node = PromptNode(text="", meta={"kind": "container_root", "_seq": self._next_seq()})
            self._has_explicit_root_tag = False
        else:
            # 指定标签：builder 自身就是一个标签块（会渲染）
            name = _tag_name(root_tag)
            self._root_node = PromptNode(
                text=f"<{name}>",
                meta={"kind": "tag_start", "tag": name, "_seq": self._next_seq()},
            )
            # 自动闭合 end，作为最后子节点
            self._root_node.add_child(
                PromptNode(
                    text=f"</{name}>",
                    priority=-10**9,
                    meta={"kind": "tag_end", "tag": name, "_seq": self._next_seq()},
                )
            )
            self._has_explicit_root_tag = True

        # 有根标签时，把 root_node 作为唯一根输出
        if self._has_explicit_root_tag:
            self.roots.append(self._root_node)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    # --------------------
    # Public: default operations on "builder root"
    # --------------------

    def ref(self) -> NodeRef:
        """返回 builder 的默认操作节点（有根标签时是该标签；无根标签时是容器根）"""
        return NodeRef(self, self._root_node)

    def add(self, text: str, *, priority: int = 0, enabled: bool = True, meta: Optional[dict] = None) -> NodeRef:
        """默认往 builder root 内部加文本"""
        return self.ref().add(text, priority=priority, enabled=enabled, meta=meta)

    def tag(self, tag: Any, *, priority: int = 0, enabled: bool = True, meta: Optional[dict] = None) -> NodeRef:
        """默认在 builder root 内部创建标签块"""
        return self.ref().tag(tag, priority=priority, enabled=enabled, meta=meta)

    def container(self, *, priority: int = 0, enabled: bool = True, meta: Optional[dict] = None) -> NodeRef:
        """默认在 builder root 内部创建纯容器节点（不输出自身标签/文本）"""
        return self.ref().container(priority=priority, enabled=enabled, meta=meta)

    def include(self, item: Any, *, clone: bool = True) -> "PromptBuilder":
        """默认把 item 作为子项挂进 builder root 内部"""
        self.ref().include(item, clone=clone)
        return self

    def extend(self, item: Any, *, clone: bool = True) -> "PromptBuilder":
        """
        默认把 item 作为 builder root 的同级添加：
        - 有根标签时：与 <ROOT> 同级（进入 self.roots）
        - 无根标签时：等价于把 item 加到 self.roots（因为 builder 本身不输出标签）
        """
        if self._has_explicit_root_tag:
            self._extend_as_sibling(item, sibling_of=self._root_node, clone=clone)
        else:
            self._extend_to_roots(item, clone=clone)
        return self

    # --------------------
    # Internal: node creation
    # --------------------

    def _add_text(self, text: str, *, parent: PromptNode, priority: int, enabled: bool, meta: Optional[dict]) -> PromptNode:
        node = PromptNode(
            text=text,
            priority=priority,
            parent=parent,
            enabled=enabled,
            meta={**(meta or {}), "_seq": (meta or {}).get("_seq") or self._next_seq()},
        )
        parent.add_child(node)
        return node

    def _create_container(self, *, parent: PromptNode, priority: int, enabled: bool, meta: Optional[dict]) -> NodeRef:
        node = PromptNode(
            text="",
            priority=priority,
            parent=parent,
            enabled=enabled,
            meta={**(meta or {}), "kind": "container", "_seq": (meta or {}).get("_seq") or self._next_seq()},
        )
        parent.add_child(node)
        return NodeRef(self, node)

    def _create_tag(self, tag: Any, *, parent: PromptNode, priority: int, enabled: bool, meta: Optional[dict]) -> NodeRef:
        name = _tag_name(tag)
        start = PromptNode(
            text=f"<{name}>",
            priority=priority,
            parent=parent,
            enabled=enabled,
            meta={**(meta or {}), "kind": "tag_start", "tag": name, "_seq": (meta or {}).get("_seq") or self._next_seq()},
        )
        parent.add_child(start)

        # end 作为 start 的最后子节点
        start.add_child(
            PromptNode(
                text=f"</{name}>",
                priority=-10**9,
                enabled=enabled,
                meta={**(meta or {}), "kind": "tag_end", "tag": name, "_seq": self._next_seq()},
            )
        )
        return NodeRef(self, start)

    # --------------------
    # Internal: include / extend composition
    # --------------------

    def _iter_item_roots(self, item: Any, *, clone: bool) -> Iterable[PromptNode]:
        """
        支持 item 类型：
        - NodeRef
        - PromptNode
        - PromptBuilder
        """
        if isinstance(item, NodeRef):
            yield item.node.clone() if clone else item.node
            return

        if isinstance(item, PromptNode):
            yield item.clone() if clone else item
            return

        if isinstance(item, PromptBuilder):
            # item 有显式 root_tag：item.roots 只有一个 root；无 root_tag：item.roots 是扩展出来的根
            for r in item.roots:
                yield r.clone() if clone else r
            # 同时把它“容器根”的 children（如果无显式 root）也导出
            if not item._has_explicit_root_tag:
                for c in item._root_node.children:
                    yield c.clone() if clone else c
            return

        raise TypeError(f"Unsupported item type: {type(item)}")

    def _include_into_parent(self, item: Any, *, parent: PromptNode, clone: bool) -> None:
        for n in self._iter_item_roots(item, clone=clone):
            parent.add_child(n)

    def _extend_to_roots(self, item: Any, *, clone: bool) -> None:
        for n in self._iter_item_roots(item, clone=clone):
            n.parent = None
            self.roots.append(n)

    def _extend_as_sibling(self, item: Any, *, sibling_of: PromptNode, clone: bool) -> None:
        parent = sibling_of.parent
        if parent is None:
            # sibling_of 是根：挂到 self.roots
            self._extend_to_roots(item, clone=clone)
        else:
            # sibling_of 有父：挂到 sibling_of.parent
            self._include_into_parent(item, parent=parent, clone=clone)

    # --------------------
    # Render
    # --------------------

    def build(self) -> str:
        lines: list[str] = []

        # 渲染顺序：
        # - 有显式 root_tag：roots 里包含 root 节点，直接渲染
        # - 无显式 root_tag：先渲染 container_root 的 children（默认 add/tag/include 都在这里），再渲染 roots（extend 出来的同级）
        if not self._has_explicit_root_tag:
            for child in sorted(self._root_node.children, key=self._sort_key):
                self._render(child, lines)
            for r in sorted(self.roots, key=self._sort_key):
                self._render(r, lines)
        else:
            for r in sorted(self.roots, key=self._sort_key):
                self._render(r, lines)

        # 去掉末尾多余空行
        while lines and lines[-1] == "":
            lines.pop()

        return self.newline.join(lines)

    def _render(self, node: PromptNode, lines: list[str]) -> None:
        if not node.enabled:
            return

        kind = node.meta.get("kind")
        is_container = kind in {"container", "container_root"}

        indent_depth = node.depth
        # tag_end 节点是 tag_start 的 child，但渲染时应该和 <TAG> 同级缩进
        if kind == "tag_end":
            if node.parent is not None:
                indent_depth = node.parent.depth
            else:
                indent_depth = max(node.depth - 1, 0)

        indent = " " * (indent_depth * self.indent_size)

        if node.text:
            for line in node.text.splitlines():
                lines.append(indent + line)
        else:
            # 容器节点不输出空行；普通空文本节点才输出空行
            if not is_container:
                lines.append("")

        for child in sorted(node.children, key=self._sort_key):
            self._render(child, lines)

    @staticmethod
    def _sort_key(n: PromptNode):
        seq = n.meta.get("_seq")
        if isinstance(seq, int):
            return (-n.priority, seq)
        return (-n.priority, id(n))

    # --------------------
    # Debug (optional)
    # --------------------

    def debug_tree(self) -> str:
        out: list[str] = []
        if not self._has_explicit_root_tag:
            out.append("== container_root children ==")
            for c in sorted(self._root_node.children, key=self._sort_key):
                self._debug_node(c, out, 0)
            out.append("== extra roots (extend) ==")
            for r in sorted(self.roots, key=self._sort_key):
                self._debug_node(r, out, 0)
        else:
            out.append("== roots ==")
            for r in sorted(self.roots, key=self._sort_key):
                self._debug_node(r, out, 0)
        return self.newline.join(out)

    def _debug_node(self, node: PromptNode, out: list[str], level: int) -> None:
        flag = "" if node.enabled else " (disabled)"
        meta = f" meta={node.meta}" if node.meta else ""
        txt = node.text.replace("\n", "\\n")
        if len(txt) > 120:
            txt = txt[:117] + "..."
        out.append(f'{"  " * level}- p={node.priority} depth={node.depth}{flag} text="{txt}"{meta}')
        for c in sorted(node.children, key=self._sort_key):
            self._debug_node(c, out, level + 1)
