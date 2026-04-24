
import pytest

from weekforge.models.week_summary import SessionLine


def _build_session_lines(statuses: list[str]) -> list[SessionLine]:
    return [
        SessionLine(name=f"Session {i}", status=s, exercises_done=3, exercises_total=3, pain_status=None, comment="")
        for i, s in enumerate(statuses)
    ]


@pytest.mark.parametrize(
    "statuses, expected",
    [
        (["done", "done", "done"], "3/3"),
        (["done", "skip", "partial"], "1/3"),
        (["skip", "skip"], "0/2"),
        (["done"], "1/1"),
        ([], "0/0"),
    ],
    ids=["all-done", "mixed", "all-skip", "single-done", "empty"],
)
def test_session_based_completion(statuses, expected):
    session_lines = _build_session_lines(statuses)
    done_count = sum(1 for sl in session_lines if sl.status == "done")
    total_count = len(session_lines)
    completion = f"{done_count}/{total_count}"
    assert completion == expected
