"""Security tests for plan-mode artifact tools.

Tests cover #51 (cross-session), #52 (path boundary / root),
and #53 (ULID validation / path traversal) fixes.
"""

import os
from pathlib import Path

import pytest

from aede.tools.plan_mode import (
    ULID_PATTERN,
    _assert_path_in_project,
    _validate_session_id,
    read_plan_artifact,
    write_plan_artifact,
)

SID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
SID_B = "01ARZ3NDEKTSV4RRFFQ69G5FAW"
SID_C = "01ARZ3NDEKTSV4RRFFQ69G5FAX"


def test_validate_session_id_rejects_non_ulid():
    with pytest.raises(ValueError, match="Invalid session_id"):
        _validate_session_id("../../../etc/passwd")
    with pytest.raises(ValueError, match="Invalid session_id"):
        _validate_session_id("not-a-ulid")
    with pytest.raises(ValueError, match="Invalid session_id"):
        _validate_session_id("short")


def test_validate_session_id_accepts_valid_ulid():
    _validate_session_id(SID_A)
    _validate_session_id(SID_B.lower())  # case-insensitive


def test_ulid_pattern_rejects_crockford_excluded():
    """Crockford base32 excludes I, L, O, U."""
    for bad in "ILOU":
        sid = "01ARZ3NDEKTSV4RRFFQ69G5FA" + bad
        assert ULID_PATTERN.match(sid) is None, f"Expected {bad} to be rejected"


def test_assert_path_in_project_accepts_valid(tmp_path):
    """Normal plan path within project_dir should pass."""
    filepath = tmp_path / "docs-internal" / "plans" / "test.md"
    _assert_path_in_project(filepath, tmp_path)


def test_assert_path_in_project_rejects_root(tmp_path):
    """project_dir at filesystem root must raise."""
    root = Path(tmp_path.anchor)
    filepath = root / "docs-internal" / "plans" / "test.md"
    with pytest.raises(ValueError, match="project_dir must not be a filesystem root"):
        _assert_path_in_project(filepath, root)


def test_assert_path_in_project_rejects_escape(tmp_path):
    """Plan path that resolves outside project_dir must raise."""
    filepath = tmp_path / ".." / "outside-plans" / "test.md"
    with pytest.raises(ValueError, match="escapes project directory"):
        _assert_path_in_project(filepath, tmp_path)


# -- #53: ULID validation prevents path traversal --


def test_read_plan_artifact_rejects_traversal_session_id(tmp_path):
    """read_plan_artifact must reject model-supplied path traversal session_id."""
    with pytest.raises(ValueError, match="Invalid session_id"):
        read_plan_artifact(
            {"session_id": "../../../etc/passwd"},
            project_dir=tmp_path,
            session_id=SID_A,
        )


def test_write_plan_artifact_rejects_traversal_session_id(tmp_path):
    """write_plan_artifact must reject session_id with path traversal chars."""
    with pytest.raises(ValueError, match="Invalid session_id"):
        write_plan_artifact(
            {"content": "x"},
            project_dir=tmp_path,
            session_id="../../../etc/passwd",
        )


# -- #52: project_dir boundary check --


def test_project_dir_root_rejected(tmp_path):
    """project_dir at filesystem root must be rejected."""
    root = Path(tmp_path.anchor)
    with pytest.raises(ValueError, match="project_dir must not be a filesystem root"):
        write_plan_artifact(
            {"content": "x"},
            project_dir=root,
            session_id=SID_A,
        )


@pytest.mark.skipif(
    os.name == "nt" and not os.environ.get("OPENCODE_SYMLINKS"),
    reason="symlinks need developer mode on Windows",
)
def test_plan_artifact_escape_via_symlink(tmp_path):
    """Plan paths that resolve outside project_dir via symlink must be rejected."""
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_plans = outside / "docs-internal" / "plans"
    outside_plans.mkdir(parents=True)
    (outside_plans / f"{SID_A}.md").write_text("escaped content")

    (tmp_path / "docs-internal").symlink_to(outside / "docs-internal")

    with pytest.raises(ValueError, match="escapes project directory"):
        read_plan_artifact({}, project_dir=tmp_path, session_id=SID_A)


# -- #51: cross-session isolation --


def test_read_plan_artifact_rejects_cross_session(tmp_path):
    """read_plan_artifact must reject model-supplied session_id matching another session."""
    with pytest.raises(ValueError, match="not the current session"):
        read_plan_artifact(
            {"session_id": SID_B},
            project_dir=tmp_path,
            session_id=SID_A,
        )


def test_read_plan_artifact_rejects_cross_session_no_args(tmp_path):
    """read_plan_artifact must reject if args has session_id differing from current."""
    write_plan_artifact({"content": "cross content"}, project_dir=tmp_path, session_id=SID_B)
    with pytest.raises(ValueError, match="not the current session"):
        read_plan_artifact(
            {"session_id": SID_B},
            project_dir=tmp_path,
            session_id=SID_A,
        )


# -- positive round-trip --


def test_plan_artifact_round_trip(tmp_path):
    """Valid ULID + valid project_dir should allow write + read round-trip."""
    content = "# My Plan\n\n1. Research\n2. Implement\n3. Test"
    write_plan_artifact({"content": content}, project_dir=tmp_path, session_id=SID_A)
    result = read_plan_artifact({}, project_dir=tmp_path, session_id=SID_A)
    assert result == content


def test_read_plan_artifact_missing_file(tmp_path):
    """read_plan_artifact must return status message for non-existent plan."""
    result = read_plan_artifact({}, project_dir=tmp_path, session_id=SID_C)
    assert "no plan found" in result.lower()


def test_write_plan_artifact_empty_content(tmp_path):
    """write_plan_artifact must return early for empty content (no validation error)."""
    result = write_plan_artifact(
        {"content": ""},
        project_dir=tmp_path,
        session_id=SID_A,
    )
    assert "nothing written" in result.lower()
