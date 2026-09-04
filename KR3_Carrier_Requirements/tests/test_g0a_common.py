import pytest

from conftest import repo_root
from g0a_common import (
    G0AError,
    canonical_json_bytes,
    resolve_repo_relative,
    sha256_bytes,
    sha256_file,
    write_json,
)


def test_canonical_json_bytes_sorts_keys_without_whitespace():
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_sha256_bytes_matches_required_known_digest():
    assert sha256_bytes(b'{"a":1,"b":2}') == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


@pytest.mark.parametrize(
    ("raw_path", "code"),
    [
        (r"C:\outside\a.xls", "PATH_NOT_POSIX"),
        ("../a.xls", "PATH_OUTSIDE_REPO"),
        ("/tmp/a.xls", "PATH_OUTSIDE_REPO"),
    ],
)
def test_resolve_repo_relative_rejects_outside_paths(raw_path, code):
    with pytest.raises(G0AError) as caught:
        resolve_repo_relative(repo_root(), raw_path)
    assert caught.value.code == code


def test_resolve_repo_relative_rejects_backslash_as_non_posix():
    with pytest.raises(G0AError) as caught:
        resolve_repo_relative(repo_root(), "nested\\file.json")
    assert caught.value.code == "PATH_NOT_POSIX"


def test_g0a_error_exposes_code_and_detail():
    error = G0AError("CONTROLLED", "test detail")

    assert error.code == "CONTROLLED"
    assert error.detail == "test detail"
    assert str(error) == "CONTROLLED: test detail"


def test_resolve_repo_relative_resolves_nested_path():
    root = repo_root()
    assert resolve_repo_relative(root, "KR3_Carrier_Requirements/catalog/items.json") == (
        root / "KR3_Carrier_Requirements" / "catalog" / "items.json"
    )


def test_resolve_repo_relative_rejects_symlink_escape(tmp_path):
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")

    with pytest.raises(G0AError) as caught:
        resolve_repo_relative(root, "escape/source.xls")
    assert caught.value.code == "PATH_OUTSIDE_REPO"


def test_write_json_is_sorted_indented_utf8_with_one_terminal_newline(tmp_path):
    output = tmp_path / "out.json"

    write_json(output, {"한글": "값", "a": [1, 2]})

    assert output.read_bytes() == '{\n  "a": [\n    1,\n    2\n  ],\n  "한글": "값"\n}\n'.encode("utf-8")


def test_sha256_file_matches_sha256_bytes_for_binary_content(tmp_path):
    content = b"\x00\xffbinary\x10"
    source = tmp_path / "source.bin"
    source.write_bytes(content)

    assert sha256_file(source) == sha256_bytes(content)
