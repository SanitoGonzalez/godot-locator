"""Unit tests for the snapshot parser/matcher. Runs without godot."""

import pytest

from snapshot import Node, expect_nodes, parse


SAMPLE = """\
- VBoxContainer [Form]:
  - Label [Title] "Welcome"
  - LineEdit [NameInput ref=e1] placeholder="Name" text=""
  - Button [Submit ref=e2] "Submit" disabled
  - Label [Status]
"""


def test_parse_extracts_each_field():
    nodes = parse(SAMPLE)
    assert len(nodes) == 5
    assert nodes[0] == Node(cls="VBoxContainer", name="Form", depth=0)
    assert nodes[1] == Node(cls="Label", name="Title", text="Welcome", depth=1)
    assert nodes[2] == Node(
        cls="LineEdit",
        name="NameInput",
        ref="e1",
        attrs={"placeholder": "Name", "text": ""},
        depth=1,
    )
    assert nodes[3] == Node(
        cls="Button",
        name="Submit",
        ref="e2",
        text="Submit",
        flags=frozenset({"disabled"}),
        depth=1,
    )
    assert nodes[4] == Node(cls="Label", name="Status", depth=1)


def test_parse_ignores_blank_and_non_node_lines():
    snap = """
not a node line
- Label "hello"

  - Button "ok"
"""
    nodes = parse(snap)
    assert [n.cls for n in nodes] == ["Label", "Button"]


def test_parse_raises_on_malformed_line():
    with pytest.raises(ValueError, match="unparseable"):
        parse("- 123notaclass")


def test_expect_matches_subsequence():
    # Title and NameInput are consecutive siblings under Form.
    expect_nodes(SAMPLE, [Node("Label", text="Welcome"), Node("LineEdit")])


def test_expect_only_class_required():
    expect_nodes(SAMPLE, [Node("Button")])


def test_expect_full_form_with_nested_children():
    expect_nodes(
        SAMPLE,
        [
            Node("VBoxContainer", name="Form", children=[
                Node("Label", name="Title", text="Welcome"),
                Node("LineEdit", name="NameInput"),
                Node("Button", name="Submit"),
                Node("Label", name="Status"),
            ]),
        ],
    )


def test_expect_fails_on_class_mismatch():
    with pytest.raises(AssertionError, match="did not match"):
        expect_nodes(SAMPLE, [Node("Sprite2D")])


def test_expect_fails_on_text_mismatch():
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [Node("Label", text="Goodbye")])


def test_expect_fails_on_name_mismatch():
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [Node("Label", name="NotATitle")])


def test_expect_fails_on_attr_mismatch():
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [Node("LineEdit", attrs={"placeholder": "Email"})])


def test_expect_fails_when_required_flag_absent():
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [Node("Label", flags=frozenset({"disabled"}))])


def test_expect_succeeds_when_actual_has_extra_flags():
    # expectation says nothing about flags, so 'disabled' on Button is fine
    expect_nodes(SAMPLE, [Node("Button", text="Submit")])


def test_expect_strict_requires_exact_root_count():
    # SAMPLE has one root (VBoxContainer); strict mode rejects extra siblings.
    with pytest.raises(AssertionError):
        expect_nodes(
            SAMPLE,
            [Node("VBoxContainer"), Node("Label", text="Welcome")],
            strict=True,
        )


def test_expect_strict_passes_with_nested_exact_match():
    expect_nodes(
        SAMPLE,
        [
            Node("VBoxContainer", name="Form", children=[
                Node("Label", name="Title"),
                Node("LineEdit", name="NameInput"),
                Node("Button", name="Submit"),
                Node("Label", name="Status"),
            ]),
        ],
        strict=True,
    )


def test_depth_check():
    expect_nodes(SAMPLE, [Node("VBoxContainer", depth=0)])
    expect_nodes(SAMPLE, [Node("Label", depth=1)])
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [Node("VBoxContainer", depth=2)])


# --- hierarchy ---------------------------------------------------------------

def test_expect_fails_when_parent_listed_as_sibling_of_child():
    """A parent and its descendant cannot both appear in a flat sibling list.
    Express the relationship via ``children=[...]`` instead."""
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [
            Node("VBoxContainer", name="Form"),
            Node("Label", name="Title"),
        ])


def test_expect_children_must_be_actual_children():
    """If ``children=`` is set, the matched node's actual children must
    contain that subsequence — Status is not a child of Title."""
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [
            Node("Label", name="Title", children=[
                Node("Label", name="Status"),
            ]),
        ])


def test_expect_nested_children_are_subsequence():
    """Nested children only need to appear as a contiguous subsequence —
    it's fine to omit some of the actual children."""
    expect_nodes(SAMPLE, [
        Node("VBoxContainer", name="Form", children=[
            Node("LineEdit", name="NameInput"),
            Node("Button", name="Submit"),
        ]),
    ])


def test_expect_nested_children_require_contiguity():
    """Title and Submit are siblings of Form but not contiguous (LineEdit
    sits between them) — so listing only those two as children fails."""
    with pytest.raises(AssertionError):
        expect_nodes(SAMPLE, [
            Node("VBoxContainer", name="Form", children=[
                Node("Label", name="Title"),
                Node("Button", name="Submit"),
            ]),
        ])


def test_error_message_shows_aligned_window():
    try:
        expect_nodes(SAMPLE, [Node("Button", text="Cancel")])
    except AssertionError as e:
        msg = str(e)
        assert "expected:" in msg
        assert "actual" in msg
        assert "full snapshot:" in msg
    else:
        pytest.fail("expected AssertionError")
