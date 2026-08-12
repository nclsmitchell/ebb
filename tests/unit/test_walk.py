from pathlib import Path

from ebb.walk import MAX_FILE_SIZE_BYTES, is_binary, iter_files, scan_repo


def test_is_binary_detects_known_magic_bytes() -> None:
    assert is_binary(b"\x89PNG\r\n\x1a\n" + b"rest of a fake png")
    assert is_binary(b"PK\x03\x04" + b"fake zip bytes")
    assert is_binary(b"%PDF-1.4 fake pdf bytes")


def test_is_binary_detects_null_byte_fallback() -> None:
    assert is_binary(b"some \x00 embedded null byte")


def test_is_binary_false_for_plain_text() -> None:
    assert not is_binary(b'MODEL = "gpt-4o-mini"\n')


def test_iter_files_skips_dot_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("should never be walked")
    (tmp_path / "app.py").write_text("x = 1\n")

    found = list(iter_files(tmp_path))

    assert found == [tmp_path / "app.py"]


def test_iter_files_honours_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored/\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "app.py").write_text("x = 1\n")
    (tmp_path / "kept.py").write_text("x = 1\n")

    found = {p.name for p in iter_files(tmp_path)}

    assert found == {".gitignore", "kept.py"}


def test_scan_repo_skips_files_over_the_size_cap(tmp_path: Path) -> None:
    small = tmp_path / "small.py"
    small.write_text('MODEL = "gpt-4o-mini"\n')

    big = tmp_path / "big.py"
    padding = "# " + ("x" * (MAX_FILE_SIZE_BYTES + 1))
    big.write_text(f'MODEL = "claude-3-opus-20240229"\n{padding}\n')
    assert big.stat().st_size > MAX_FILE_SIZE_BYTES

    matches = list(scan_repo(tmp_path))

    assert [m.matched_text for m in matches] == ["gpt-4o-mini"]


def test_scan_repo_skips_binary_files_even_with_a_registered_extension(tmp_path: Path) -> None:
    # A .py file that is actually binary — magic-byte/null-byte detection must win over the
    # extension-based detector lookup.
    fake_binary_py = tmp_path / "weird.py"
    fake_binary_py.write_bytes(b"\x89PNG\r\n\x1a\nMODEL = gpt-4o-mini embedded in binary bytes")

    matches = list(scan_repo(tmp_path))

    assert matches == []
