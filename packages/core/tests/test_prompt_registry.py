import pytest
from jinja2 import UndefinedError
from vera_core.prompts import PromptRegistry


def test_get_resolves_highest_version():
    reg = PromptRegistry()
    t = reg.get("planner")
    assert t.version == "v5"
    assert t.agent == "planner"
    assert len(t.sha256) == 64


def test_render_requires_all_vars():
    reg = PromptRegistry()
    with pytest.raises(UndefinedError):
        reg.get("verifier").render()  # StrictUndefined -> missing vars raise


def test_sha256_changes_with_content(tmp_path):
    d = tmp_path / "coder"
    d.mkdir()
    (d / "v1.jinja").write_text("hello {{ x }}")
    a = PromptRegistry(tmp_path).get("coder").sha256
    (d / "v1.jinja").write_text("hello {{ x }}!")
    b = PromptRegistry(tmp_path).get("coder").sha256
    assert a != b


def test_unknown_agent_raises():
    with pytest.raises(KeyError):
        PromptRegistry().get("nonesuch")


def test_list_versions_sorted():
    assert PromptRegistry().list_versions("verifier") == ["v6"]


@pytest.mark.parametrize(
    "kind", ["csv", "json", "xlsx", "parquet", "md", "txt", "pdf", "sqlite", "zip"]
)
def test_analyzer_template_renders_for_every_file_kind(kind: str) -> None:
    rendered = (
        PromptRegistry()
        .get("analyzer")
        .render(file_id="f1", filename=f"sample.{kind}", kind=kind, sample="a,b\n1,2\n")
    )
    assert "--- Essential Information ---" in rendered
    assert "source" in rendered
    assert "specifics" in rendered  # the per-kind format sub-template was included


def test_analyzer_template_forbids_try_except_language() -> None:
    rendered = (
        PromptRegistry()
        .get("analyzer")
        .render(file_id="f", filename="x.csv", kind="csv", sample="")
    )
    assert "try/except" in rendered
