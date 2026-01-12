from __future__ import annotations


from tools.PromptBuilder import PromptBuilder


def test_root_tag_closing_indentation():
    b = PromptBuilder("ROOT")
    b.add("first")
    b.add("second")
    ind = " " * b.indent_size
    assert b.build().splitlines() == [
        "<ROOT>",
        f"{ind}first",
        f"{ind}second",
        "</ROOT>",
    ]


def test_nested_tag_closing_indentation():
    b = PromptBuilder("ROOT")
    b.tag("X").add("x1")
    ind1 = " " * b.indent_size
    ind2 = " " * (b.indent_size * 2)
    assert b.build().splitlines() == [
        "<ROOT>",
        f"{ind1}<X>",
        f"{ind2}x1",
        f"{ind1}</X>",
        "</ROOT>",
    ]


def test_insertion_order_is_top_to_bottom():
    b = PromptBuilder("ROOT")
    b.tag("A").add("a")
    b.tag("B").add("b")
    out = b.build().splitlines()

    ind = " " * b.indent_size

    # A block should appear before B block (先进在上面)
    a_open = out.index(f"{ind}<A>")
    b_open = out.index(f"{ind}<B>")
    assert a_open < b_open
