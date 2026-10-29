"""Tests for Paison Phase 1 transpiler."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from paison.cli import main
from paison.runner import run_code, run_file
from paison.transpiler import transpile


class TranspilerTests(unittest.TestCase):
    def execute(self, source):
        output = io.StringIO()
        with redirect_stdout(output):
            run_code(source)
        return output.getvalue()

    def test_print(self):
        self.assertEqual(
            transpile("しゅつりょく 「Hello World!」"), 'print("Hello World!")'
        )
        self.assertEqual(self.execute("しゅつりょく 「Hello World!」"), "Hello World!\n")

    def test_variable_assignment(self):
        source = "なまえ ＝ 「QuQuLa89」\nしゅつりょく なまえ"
        self.assertEqual(transpile(source), 'なまえ = "QuQuLa89"\nprint(なまえ)')
        self.assertEqual(self.execute(source), "QuQuLa89\n")

    def test_if_else(self):
        source = (
            "ねんれい ＝ 20\n"
            "もし ねんれい ＞＝ 20 ならば：\n"
            "    しゅつりょく 「成人です」\n"
            "ちがうなら：\n"
            "    しゅつりょく 「未成年です」"
        )
        self.assertEqual(self.execute(source), "成人です\n")
        self.assertEqual(
            self.execute(source.replace("＝ 20", "＝ 19", 1)), "未成年です\n"
        )

    def test_zenkaku_symbols(self):
        cases = {
            "値 ＝ 1 ＋ 2 － 3 ＊ 4 ／ 5": "値 = 1 + 2 - 3 * 4 / 5",
            "a ＞＝ b": "a >= b",
            "a ＜＝ b": "a <= b",
            "a ＞ b": "a > b",
            "a ＜ b": "a < b",
            "a ＝＝ b": "a == b",
            "a ！＝ b": "a != b",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(transpile(source), expected)

    def test_elif_and_full_width_indentation(self):
        source = (
            "値 ＝ 2\n"
            "もし 値 ＝＝ 1 ならば：\n"
            "　しゅつりょく 「一」\n"
            "それとも 値 ＝＝ 2 ならば：\n"
            "　しゅつりょく 「二」\n"
            "ちがうなら：\n"
            "　しゅつりょく 「その他」"
        )
        self.assertEqual(self.execute(source), "二\n")
        self.assertIn('    print("二")', transpile(source))

    def test_loops(self):
        source = (
            "合計 ＝ 0\n"
            "数 を range(3) で くりかえす：\n"
            "　合計 ＝ 合計 ＋ 数\n"
            "合計 ＜ 5 のあいだ くりかえす：\n"
            "　合計 ＝ 合計 ＋ 1\n"
            "しゅつりょく 合計"
        )
        self.assertEqual(self.execute(source), "5\n")

    def test_boolean_operators_and_identifier_boundaries(self):
        source = (
            "ぎん ＝ しん\n"
            "もし ぎん かつ ぎ または しん ならば：\n"
            "　しゅつりょく ぎ"
        )
        self.assertEqual(self.execute(source), "False\n")
        self.assertIn("ぎん = True", transpile(source))

    def test_literal_contents_are_preserved(self):
        content = "もし しん かつ ぎ ならば：　＝＋！＝ # しゅつりょく"
        for source in (
            f"しゅつりょく 「{content}」",
            f"しゅつりょく 『{content}』",
            f'しゅつりょく "{content}"',
            f"しゅつりょく '{content}'",
            f'しゅつりょく """{content}"""',
            f"しゅつりょく '''{content}'''",
        ):
            with self.subTest(source=source):
                self.assertEqual(self.execute(source), content + "\n")

    def test_quotes_backslashes_and_multiline_literals(self):
        self.assertEqual(
            self.execute('しゅつりょく 「"引用" C:\\sample」'),
            '"引用" C:\\sample\n',
        )
        self.assertEqual(
            self.execute("しゅつりょく 『一行目\n　二行目 '''』"),
            "一行目\n　二行目 '''\n",
        )
        self.assertEqual(
            self.execute(r'しゅつりょく "引用: \"しん＝ぎ\""'),
            '引用: "しん＝ぎ"\n',
        )

    def test_comments(self):
        source = (
            "# 「未完の文字列 しん＝ぎ\n"
            "しゅつりょく 「# 本文」 # しん ＝ ぎ"
        )
        self.assertEqual(self.execute(source), "# 本文\n")
        self.assertTrue(transpile(source).endswith("# しん ＝ ぎ"))

    def test_empty_lines_and_trailing_newline(self):
        self.assertEqual(transpile(""), "")
        self.assertEqual(transpile("\n\n"), "\n\n")
        self.assertEqual(transpile("しゅつりょく 1\r\n"), "print(1)\n")

    def test_placeholder_name_collision(self):
        source = "__paison_literal_0__ ＝ 「値」\nしゅつりょく __paison_literal_0__"
        self.assertEqual(self.execute(source), "値\n")


class RunnerTests(unittest.TestCase):
    def test_script_main_namespace(self):
        output = io.StringIO()
        with redirect_stdout(output):
            run_code("しゅつりょく __name__")
        self.assertEqual(output.getvalue(), "__main__\n")

    def test_syntax_error_filename(self):
        with self.assertRaises(SyntaxError) as error:
            run_code("もし しん ならば：", filename="invalid.pai")
        self.assertEqual(error.exception.filename, "invalid.pai")

    def test_utf8_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.pai"
            path.write_text("しゅつりょく 「こんにちは」", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                run_file(str(path))
            self.assertEqual(output.getvalue(), "こんにちは\n")


class CliTests(unittest.TestCase):
    def test_command(self):
        for flag in ("-c", "--command"):
            with self.subTest(flag=flag):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = main([flag, "しゅつりょく 「こんにちは」"])
                self.assertEqual(result, 0)
                self.assertEqual(output.getvalue(), "こんにちは\n")

    def test_empty_command(self):
        self.assertEqual(main(["-c", ""]), 0)

    def test_file(self):
        with patch("paison.cli.run_file") as execute_file:
            self.assertEqual(main(["sample.pai"]), 0)
        execute_file.assert_called_once_with("sample.pai")

    def test_invalid_arguments(self):
        for argv in ([], ["sample.pai", "-c", "しゅつりょく 1"], ["-c"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(argv)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
