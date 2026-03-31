"""Tests for CJK character detection utilities."""

from __future__ import annotations

from src.core.cjk import contains_cjk, extract_cjk_and_latin


class TestContainsCjk:
    """Tests for contains_cjk()."""

    def test_chinese(self) -> None:
        assert contains_cjk("你好世界") is True

    def test_japanese_kanji(self) -> None:
        assert contains_cjk("漢字") is True

    def test_japanese_hiragana(self) -> None:
        assert contains_cjk("こんにちは") is True

    def test_japanese_katakana(self) -> None:
        assert contains_cjk("カタカナ") is True

    def test_korean(self) -> None:
        assert contains_cjk("안녕하세요") is True

    def test_english_only(self) -> None:
        assert contains_cjk("hello world") is False

    def test_numbers_and_symbols(self) -> None:
        assert contains_cjk("123 !@# abc") is False

    def test_mixed(self) -> None:
        assert contains_cjk("fix 用户认证 module") is True

    def test_empty(self) -> None:
        assert contains_cjk("") is False


class TestExtractCjkAndLatin:
    """Tests for extract_cjk_and_latin()."""

    def test_pure_chinese(self) -> None:
        cjk, latin = extract_cjk_and_latin("用户认证")
        assert cjk == "用户认证"
        assert latin == ""

    def test_pure_english(self) -> None:
        cjk, latin = extract_cjk_and_latin("hello world")
        assert cjk == ""
        assert latin == "hello world"

    def test_mixed(self) -> None:
        cjk, latin = extract_cjk_and_latin("fix 用户认证 module")
        assert cjk == "用户认证"
        assert latin == "fix  module"

    def test_empty(self) -> None:
        cjk, latin = extract_cjk_and_latin("")
        assert cjk == ""
        assert latin == ""

    def test_cjk_with_numbers(self) -> None:
        cjk, latin = extract_cjk_and_latin("测试123")
        assert cjk == "测试"
        assert latin == "123"
