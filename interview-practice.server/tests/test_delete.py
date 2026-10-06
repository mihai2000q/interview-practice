"""Deleting Applications and Interviews. No database: the cascade is the database's, so
what is tested is the best-effort removal of the portrait files and that the routes are
registered."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.app import create_app
from app.services.portrait_files import remove_portrait_files


@pytest.fixture
def instance(tmp_path: Path) -> Iterator[Path]:
    app = create_app()
    app.instance_path = str(tmp_path / "instance")
    (tmp_path / "instance" / "uploads" / "personas").mkdir(parents=True)
    with app.app_context():
        yield tmp_path / "instance"


def test_removes_the_portrait_files(instance: Path) -> None:
    first = instance / "uploads" / "personas" / "a.png"
    second = instance / "uploads" / "personas" / "b.jpg"
    first.write_bytes(b"x")
    second.write_bytes(b"x")

    remove_portrait_files(["uploads/personas/a.png", "uploads/personas/b.jpg"])

    assert not first.exists()
    assert not second.exists()


def test_a_missing_file_is_ignored(instance: Path) -> None:
    remove_portrait_files(["uploads/personas/gone.png"])


def test_an_os_error_is_logged_not_raised(
    instance: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    kept = instance / "uploads" / "personas" / "kept.png"
    kept.write_bytes(b"x")
    removable = instance / "uploads" / "personas" / "b.png"
    removable.write_bytes(b"x")
    real_unlink = Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self.name == "kept.png":
            raise PermissionError("read-only volume")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)

    with caplog.at_level(logging.ERROR):
        remove_portrait_files(["uploads/personas/kept.png", "uploads/personas/b.png"])

    assert kept.exists()
    assert not removable.exists()  # one failure doesn't stop the others
    assert "kept.png" in caplog.text


def test_a_path_outside_the_instance_folder_is_never_removed(
    instance: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")

    remove_portrait_files(["../outside.png", str(outside)])

    assert outside.exists()


def test_a_symlink_out_of_the_instance_folder_is_not_followed(
    instance: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    (instance / "link.png").symlink_to(outside)

    remove_portrait_files(["link.png"])

    assert outside.exists()


def test_delete_routes_are_registered() -> None:
    rules = {
        (rule.rule, method)
        for rule in create_app().url_map.iter_rules()
        for method in rule.methods or ()
    }
    assert ("/api/applications/<uuid:application_id>", "DELETE") in rules
    assert ("/api/interviews/<uuid:interview_id>", "DELETE") in rules
