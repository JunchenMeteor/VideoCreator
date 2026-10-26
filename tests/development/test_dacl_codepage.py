"""DACL summary is invariant across the console code page and ignores summaries."""

from pathlib import Path

import pytest
from video_creator.application.installer_provisioning import _dacl_entries
from video_creator.domain.errors import EngineError


def _output(encoding: str) -> bytes:
    text = (
        "C:\\instances\\demo\n"
        "    BUILTIN\\Users:(OI)(CI)(RX)\n"
        "    NT AUTHORITY\\SYSTEM:(OI)(CI)(F)\n"
        "已成功处理 2 个文件\n"
    ) if encoding == 'gbk' else (
        "C:\\instances\\demo\n"
        "    BUILTIN\\Users:(OI)(CI)(RX)\n"
        "    NT AUTHORITY\\SYSTEM:(OI)(CI)(F)\n"
        "Successfully processed 2 files\n"
    )
    return text.encode(encoding)


def test_dacl_same_ace_set_across_utf8_and_gbk():
    path = Path("C:/instances/demo")
    utf8 = _dacl_entries(_output('utf-8'), path)
    gbk = _dacl_entries(_output('gbk'), path)
    assert utf8 == gbk
    assert {entry[0] for entry in utf8} == {"BUILTIN\\Users", "NT AUTHORITY\\SYSTEM"}


def test_empty_ace_is_named_failure():
    with pytest.raises(EngineError) as error:
        _dacl_entries(b"Successfully processed 0 files\n", Path("C:/instances/demo"))
    assert error.value.code == "dacl_parse_failed"
