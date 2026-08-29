"""Pure parsing of analyzer-script stdout into a FileDescription."""

from __future__ import annotations

from uuid import uuid4

from vera_core.models.ids import FileId
from vera_core.policies import build_partial_description, parse_analyzer_stdout

FID = FileId(uuid4())

CSV_STDOUT = """\
--- Essential Information ---
row_count: 1234
--- Fields ---
- name=merchant_id; dtype=string; samples=Acme, Beta, Gamma
- name=amount; dtype=float; samples=1.5, 2.0
--- Sample Rows ---
{"merchant_id": "Acme", "amount": 1.5}
{"merchant_id": "Beta", "amount": 2.0}
--- Notes ---
amount is post-fee
"""


def test_parses_row_count_fields_and_sample_rows() -> None:
    d = parse_analyzer_stdout(FID, CSV_STDOUT)
    assert d.file_id == FID
    assert d.partial is False
    assert d.row_count == 1234
    assert [f.name for f in d.schema_fields] == ["merchant_id", "amount"]
    assert d.schema_fields[0].dtype == "string"
    assert d.schema_fields[0].sample_values == ["Acme", "Beta", "Gamma"]
    assert d.sample_rows == [
        {"merchant_id": "Acme", "amount": 1.5},
        {"merchant_id": "Beta", "amount": 2.0},
    ]
    assert "amount is post-fee" in d.summary_text


def test_missing_sections_leave_fields_empty_not_raising() -> None:
    d = parse_analyzer_stdout(FID, "--- Essential Information ---\nnothing structured here\n")
    assert d.row_count is None
    assert d.schema_fields == []
    assert d.sample_rows is None
    assert d.sheet_names is None
    assert "nothing structured here" in d.summary_text


def test_sheet_names_parsed_for_xlsx_shaped_output() -> None:
    d = parse_analyzer_stdout(FID, "--- Essential Information ---\nsheet_names: Q1, Q2, Q3\n")
    assert d.sheet_names == ["Q1", "Q2", "Q3"]


def test_summary_text_truncated_to_8192() -> None:
    d = parse_analyzer_stdout(FID, "x" * 10_000)
    assert len(d.summary_text) == 8192


def test_malformed_sample_rows_are_skipped() -> None:
    d = parse_analyzer_stdout(FID, '--- Sample Rows ---\n{not json}\n{"ok": 1}\n')
    assert d.sample_rows == [{"ok": 1}]


def test_partial_from_csv_header_sample() -> None:
    d = build_partial_description(FID, "merchant_id,amount,date\nAcme,1.5,2025-01-01\n")
    assert d.partial is True
    assert d.row_count is None
    assert [f.name for f in d.schema_fields] == ["merchant_id", "amount", "date"]
    assert all(f.dtype == "unknown" for f in d.schema_fields)


def test_partial_from_json_object_sample() -> None:
    d = build_partial_description(FID, '{"a": 1, "b": {"c": 2}, "d": [1,2]}')
    assert d.partial is True
    assert sorted(f.name for f in d.schema_fields) == ["a", "b", "d"]


def test_partial_from_json_array_sample() -> None:
    d = build_partial_description(FID, '[{"x": 1, "y": 2}, {"x": 3}]')
    assert [f.name for f in d.schema_fields] == ["x", "y"]


def test_partial_from_unrecognisable_sample_is_still_valid() -> None:
    d = build_partial_description(FID, "\x00\x01 binary junk")
    assert d.partial is True
    assert d.schema_fields == []
    assert d.summary_text
