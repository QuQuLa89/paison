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
        for source in (
            'しゅつりょく（"Hello World!"）',
            'しゅつりょく("Hello World!")',
            "しゅつりょく（“Hello World!”）",
            "しゅつりょく（‘Hello World!’）",
        ):
            with self.subTest(source=source):
                quote = "'" if "‘" in source else '"'
                self.assertEqual(
                    transpile(source), f"print({quote}Hello World!{quote})"
                )
                self.assertEqual(self.execute(source), "Hello World!\n")

    def test_print_function_arguments(self):
        source = 'しゅつりょく（“一”, “二”, sep=" / ", end="!"）'
        self.assertEqual(transpile(source), 'print("一", "二", sep=" / ", end="!")')
        self.assertEqual(self.execute(source), "一 / 二!")
        self.assertEqual(self.execute("しゅつりょく（）"), "\n")
        self.assertEqual(
            self.execute("しゅつりょく（もじ（しゅつりょく（１）））"),
            "1\nNone\n",
        )

    def test_print_requires_parentheses(self):
        source = "しゅつりょく 1"
        self.assertEqual(transpile(source), source)
        with self.assertRaises(SyntaxError):
            self.execute(source)

    def test_removed_string_delimiters(self):
        for left, right in (("\u300c", "\u300d"), ("\u300e", "\u300f")):
            with self.subTest(left=left):
                source = f"しゅつりょく（{left}本文{right}）"
                self.assertEqual(transpile(source), f"print({left}本文{right})")
                with self.assertRaises(SyntaxError):
                    self.execute(source)

    def test_variable_assignment(self):
        source = "なまえ ＝ “QuQuLa89”\nしゅつりょく（なまえ）"
        self.assertEqual(transpile(source), 'なまえ = "QuQuLa89"\nprint(なまえ)')
        self.assertEqual(self.execute(source), "QuQuLa89\n")

    def test_if_else(self):
        source = (
            "ねんれい ＝ 20\n"
            "もし ねんれい ＞＝ 20 ならば：\n"
            "    しゅつりょく（“成人です”）\n"
            "ちがうなら：\n"
            "    しゅつりょく（“未成年です”）"
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

    def test_zenkaku_numbers(self):
        cases = (
            ("０", "0", "0\n"),
            ("１２３４５６７８９０", "1234567890", "1234567890\n"),
            ("３．１４", "3.14", "3.14\n"),
            ("３.１4", "3.14", "3.14\n"),
            ("．５", ".5", "0.5\n"),
            ("－２．５ ＋ １", "-2.5 + 1", "-1.5\n"),
        )
        for value, expected, output in cases:
            with self.subTest(value=value):
                source = f"値 ＝ {value}\nしゅつりょく（値）"
                self.assertEqual(transpile(source), f"値 = {expected}\nprint(値)")
                self.assertEqual(self.execute(source), output)

        content = "０１２３４５６７８９．"
        for left, right in (
            ('"', '"'),
            ("'", "'"),
            ('"""', '"""'),
            ("'''", "'''"),
            ("“", "”"),
            ("‘", "’"),
        ):
            with self.subTest(left=left):
                self.assertEqual(
                    self.execute(f"しゅつりょく（{left}{content}{right}）"),
                    content + "\n",
                )

        source = f"値 ＝ ３．１４ # {content}"
        self.assertEqual(transpile(source), f"値 = 3.14 # {content}")

    def test_full_width_space_in_expressions(self):
        source = (
            "かんすう　合計（左,　右）：\n"
            "　かえす　左　＋　右\n"
            "値　＝　合計　（１,　２）　# コメント　保持\n"
            "もし　値　＝＝　３　かつ　しん　ならば：\n"
            "　しゅつりょく　（“苗字　名前”,　値）　"
        )
        expected = (
            "def 合計(左, 右):\n"
            "    return 左 + 右\n"
            "値 = 合計 (1, 2) # コメント　保持\n"
            "if 値 == 3 and True:\n"
            '    print ("苗字　名前", 値) '
        )
        self.assertEqual(transpile(source), expected)
        self.assertEqual(self.execute(source), "苗字　名前 3\n")
        self.assertEqual(transpile("# コメント　保持"), "# コメント　保持")

    def test_full_width_spaces_in_literals_are_preserved(self):
        for left, right in (
            ('"', '"'),
            ("'", "'"),
            ('"""', '"""'),
            ("'''", "'''"),
            ("“", "”"),
            ("‘", "’"),
        ):
            with self.subTest(left=left):
                content = "　苗字　名前　"
                source = f"しゅつりょく　（{left}{content}{right}）"
                self.assertEqual(self.execute(source), content + "\n")

    def test_elif_and_full_width_indentation(self):
        source = (
            "値 ＝ 2\n"
            "もし 値 ＝＝ 1 ならば：\n"
            "　しゅつりょく（“一”）\n"
            "それとも 値 ＝＝ 2 ならば：\n"
            "　しゅつりょく（“二”）\n"
            "ちがうなら：\n"
            "　しゅつりょく（“その他”）"
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
            "しゅつりょく（合計）"
        )
        self.assertEqual(self.execute(source), "5\n")

    def test_python_aligned_loops(self):
        for_header_aliases = (
            "くりかえす 数 のなかの",
            "くりかえす 数 のなか",
            "くりかえす 数 で",
            "ふぉー 数 いん",
            "フォー 数 イン",
            "ふぉー 数 イン",
            "フォー 数 いん",
        )
        expected = (
            "合計 = 0\n"
            "for 数 in [1, 2, 3]:\n"
            "    合計 = 合計 + 数\n"
            "回数 = 0\n"
            "while 回数 < 3:\n"
            "    回数 = 回数 + 1\n"
            "print(合計, 回数)"
        )
        for for_header in for_header_aliases:
            for while_keyword in ("あいだ", "つづける", "ほわいる", "ホワイル"):
                with self.subTest(for_header=for_header, while_keyword=while_keyword):
                    source = (
                        "合計 ＝ ０\n"
                        f"{for_header} ［１, ２, ３］：\n"
                        "　合計 ＝ 合計 ＋ 数\n"
                        "回数 ＝ ０\n"
                        f"{while_keyword} 回数 ＜ ３：\n"
                        "　回数 ＝ 回数 ＋ １\n"
                        "しゅつりょく（合計, 回数）"
                    )
                    self.assertEqual(transpile(source), expected)
                    self.assertEqual(self.execute(source), "6 3\n")

    def test_python_aligned_nested_loops(self):
        source = (
            "合計　＝　０\n"
            "くりかえす　数　のなかの　［１,　２］：　# 外側のループ\n"
            "　回数　＝　０\n"
            "　ほわいる　回数　＜　数：\n"
            "　　合計　＝　合計　＋　数\n"
            "　　回数　＝　回数　＋　１\n"
            "しゅつりょく（合計）"
        )
        self.assertIn(
            "for 数 in [1, 2]: # 外側のループ\n    回数 = 0\n    while 回数 < 数:",
            transpile(source),
        )
        self.assertEqual(self.execute(source), "5\n")

    def test_python_aligned_loops_skip_empty_and_false_bodies(self):
        source = (
            "回数 ＝ ０\n"
            "ふぉー 数 いん ［］：\n"
            "　回数 ＝ 回数 ＋ １\n"
            "あいだ ぎ：\n"
            "　回数 ＝ 回数 ＋ １\n"
            "しゅつりょく（回数）"
        )
        self.assertEqual(self.execute(source), "0\n")

    def test_boolean_operators_and_identifier_boundaries(self):
        source = (
            "ぎん ＝ しん\n"
            "もし ぎん かつ ぎ または しん ならば：\n"
            "　しゅつりょく（ぎ）"
        )
        self.assertEqual(self.execute(source), "False\n")
        self.assertIn("ぎん = True", transpile(source))

    def test_loop_control_statements(self):
        for stop in ("ぬける", "やめる", "ぶれーく", "ブレーク"):
            for skip in ("つぎへ", "とばす", "こんてぃにゅー", "コンティニュー"):
                for header in (
                    "ふぉー 数 いん はんい（１, ８）：\n",
                    "数 ＝ ０\nあいだ 数 ＜ ７：\n　数 ＝ 数 ＋ １\n",
                ):
                    with self.subTest(stop=stop, skip=skip, header=header):
                        source = (
                            "値 ＝ ［］\n" + header + "　もし 数 ＝＝ ５：\n"
                            f"　　{stop} # ここで終了します\n"
                            "　もし 数 % ２ ＝＝ ０：\n"
                            f"　　{skip}\n"
                            "　値 に 数 を ついか\n"
                            "しゅつりょく（値）"
                        )
                        self.assertEqual(self.execute(source), "[1, 3]\n")
        for keyword in ("なにもしない", "ぱす", "パス"):
            with self.subTest(keyword=keyword):
                source = (
                    f"かんすう 未実装（）：\n　{keyword}\nしゅつりょく（未実装（））"
                )
                self.assertEqual(self.execute(source), "None\n")

    def test_math_and_collection_builtins(self):
        cases = (
            (("はんい", "れんじ", "レンジ"), "５, ０, －２", "[5, 3, 1]\n"),
            (("しょうすう", "ふろーと", "フロート"), "“2.5”", "2.5\n"),
            (("しんぎ", "ぶーる", "ブール"), "［］", "False\n"),
            (("ごうけい", "さむ", "サム"), "［１, ２, ３］, start=４", "10\n"),
            (("さいだい", "まっくす", "マックス"), "－１, ３, ２", "3\n"),
            (("さいしょう", "みん", "ミン"), "［－１, ３, ２］", "-1\n"),
            (("ぜったいち", "あぶす", "アブス"), "－３．５", "3.5\n"),
            (
                ("じしょ", "でぃくと", "ディクト"),
                "名前=“QuQuLa89”",
                "{'名前': 'QuQuLa89'}\n",
            ),
        )
        for aliases, arguments, expected in cases:
            for alias in aliases:
                for reference in (False, True):
                    with self.subTest(alias=alias, reference=reference):
                        name = "関数" if reference else alias
                        expression = f"{name}（{arguments}）"
                        if alias in ("はんい", "れんじ", "レンジ"):
                            expression = f"はいれつ（{expression}）"
                        source = f"しゅつりょく（{expression}）"
                        if reference:
                            source = f"関数 ＝ {alias}\n" + source
                        self.assertEqual(self.execute(source), expected)
        self.assertEqual(
            self.execute("しゅつりょく（ごうけい（はんい（４）））"), "6\n"
        )
        self.assertEqual(self.execute("しゅつりょく（じしょ（））"), "{}\n")

    def test_none_and_operators(self):
        for constant in ("なし", "のん", "ノン"):
            with self.subTest(constant=constant):
                self.assertEqual(self.execute(f"しゅつりょく（{constant}）"), "None\n")
        for negate in ("でない", "のっと", "ノット"):
            for contains in ("のなかに", "ふくまれる", "いん", "イン"):
                with self.subTest(negate=negate, contains=contains):
                    source = (
                        "値　＝　なし\n"
                        f"もし　{negate}　値：\n"
                        f"　しゅつりょく（２　{contains}　［１,　２］）\n"
                        f"　しゅつりょく（３　{negate}　{contains}　［１,　２］）\n"
                        f"　しゅつりょく（“鍵” {contains} ｛“鍵”： なし｝）\n"
                        "判定 ＝ ［］\n"
                        f"判定 に {negate} 値 を ついか\n"
                        "しゅつりょく（判定）"
                    )
                    self.assertEqual(self.execute(source), "True\nTrue\nTrue\n[True]\n")
        for negate in ("のっと", "ノット"):
            with self.subTest(negate=negate):
                self.assertEqual(transpile(f"{negate} ぎ"), "not False")
                self.assertEqual(
                    self.execute(f"しゅつりょく（{negate} しん, {negate} （ぎ））"),
                    "False True\n",
                )

    def test_full_width_curly_brackets(self):
        source = (
            "データ　＝　｛“数列”： ［１, ２］, “詳細”： ｛“値”： なし｝｝\n"
            "データ［“追加”］ ＝ じしょ（値=３）\n"
            "しゅつりょく（データ［“数列”］, データ［“詳細”］［“値”］）\n"
            "しゅつりょく（データ［“追加”］［“値”］, ｛１, ２｝ ＝＝ {1, 2}, ｛｝）"
        )
        self.assertEqual(self.execute(source), "[1, 2] None\n3 True {}\n")
        self.assertEqual(transpile("［｛｝］"), "[{}]")

    def test_new_keywords_and_symbols_are_preserved(self):
        content = (
            "ぬける やめる ぶれーく ブレーク つぎへ とばす こんてぃにゅー "
            "コンティニュー なにもしない ぱす パス はんい れんじ レンジ "
            "しょうすう ふろーと フロート しんぎ ぶーる ブール ごうけい さむ サム "
            "さいだい まっくす マックス さいしょう みん ミン ぜったいち あぶす アブス "
            "じしょ でぃくと ディクト なし のん ノン でない のっと ノット "
            "のなかに ふくまれる いん イン ｛｝"
        )
        for left, right in (
            ('"', '"'),
            ("'", "'"),
            ('"""', '"""'),
            ("'''", "'''"),
            ("“", "”"),
            ("‘", "’"),
        ):
            with self.subTest(left=left):
                self.assertEqual(
                    self.execute(f"しゅつりょく（{left}{content}{right}）"),
                    content + "\n",
                )
        for keyword in content.split()[:-1]:
            with self.subTest(keyword=keyword):
                for identifier in (f"独自_{keyword}", f"{keyword}の値"):
                    source = f"{identifier} = 1\nprint({identifier})"
                    self.assertEqual(transpile(source), source)
                    self.assertEqual(transpile(f"{identifier}(1)"), f"{identifier}(1)")
        comment = f"# {content}"
        self.assertEqual(transpile(comment), comment)
        self.assertEqual(
            transpile(f"しゅつりょく（なし） {comment}"), f"print(None) {comment}"
        )

    def test_literal_contents_are_preserved(self):
        content = "もし しん かつ ぎ ならば：　＝＋！＝ # しゅつりょく"
        for source in (
            f'しゅつりょく（"{content}"）',
            f"しゅつりょく（'{content}'）",
            f'しゅつりょく（"""{content}"""）',
            f"しゅつりょく（'''{content}'''）",
            f"しゅつりょく（“{content}”）",
            f"しゅつりょく（‘{content}’）",
        ):
            with self.subTest(source=source):
                self.assertEqual(self.execute(source), content + "\n")

    def test_quotes_backslashes_and_multiline_literals(self):
        self.assertEqual(
            self.execute(r'しゅつりょく（“"引用" C:\\sample”）'),
            '"引用" C:\\sample\n',
        )
        self.assertEqual(
            self.execute('しゅつりょく（"""一行目\n　二行目 \'\'\'"""）'),
            "一行目\n　二行目 '''\n",
        )
        self.assertEqual(
            self.execute(r'しゅつりょく（"引用: \"しん＝ぎ\""）'),
            '引用: "しん＝ぎ"\n',
        )

    def test_comments(self):
        source = "# “未完の文字列 しん＝ぎ\n" "しゅつりょく（“# 本文”） # しん ＝ ぎ"
        self.assertEqual(self.execute(source), "# 本文\n")
        self.assertTrue(transpile(source).endswith("# しん ＝ ぎ"))

    def test_empty_lines_and_trailing_newline(self):
        self.assertEqual(transpile(""), "")
        self.assertEqual(transpile("\n\n"), "\n\n")
        self.assertEqual(transpile("しゅつりょく（1）\r\n"), "print(1)\n")

    def test_placeholder_name_collision(self):
        source = "__paison_literal_0__ ＝ “値”\nしゅつりょく（__paison_literal_0__）"
        self.assertEqual(self.execute(source), "値\n")

    def test_function_def_and_return(self):
        source = (
            "かんすう 合計(左, 右)：\n"
            "　かえす 左 ＋ 右\n"
            "しゅつりょく（合計(2, 3)）"
        )
        self.assertEqual(
            transpile(source),
            "def 合計(左, 右):\n    return 左 + 右\nprint(合計(2, 3))",
        )
        self.assertEqual(self.execute(source), "5\n")

    def test_try_except(self):
        source = (
            "こころみる：\n"
            "　しゅつりょく（かず(“数字ではありません”)）\n"
            "しっぱいしたとき：\n"
            "　しゅつりょく（“変換に失敗しました”）"
        )
        self.assertEqual(self.execute(source), "変換に失敗しました\n")
        self.assertEqual(
            self.execute(source.replace("“数字ではありません”", "“42”")),
            "42\n",
        )

    def test_list_append(self):
        source = (
            "項目 ＝ []\n"
            "項目 に “最初” を ついか\n"
            "項目に もじ(2) をついか # 追加します\n"
            "しゅつりょく（項目）"
        )
        self.assertIn('項目.append("最初")', transpile(source))
        self.assertEqual(self.execute(source), "['最初', '2']\n")

    def test_full_width_brackets(self):
        source = (
            "かんすう 二倍（値）：\n"
            "　かえす 値 ＊ 2\n"
            "項目 ＝ ［二倍（3）］\n"
            "しゅつりょく（項目［0］）"
        )
        self.assertEqual(self.execute(source), "6\n")

    def test_curly_quotes_and_literal_preservation(self):
        content = "かんすう かえす こころみる しっぱいしたとき ［（）］ かず(1) #"
        for left, right in (("“", "”"), ("‘", "’")):
            with self.subTest(left=left):
                self.assertEqual(
                    self.execute(f"しゅつりょく（{left}{content}{right}）"),
                    content + "\n",
                )
        self.assertEqual(self.execute('しゅつりょく（“a "b"”）'), 'a "b"\n')
        self.assertEqual(self.execute("しゅつりょく（‘it's’）"), "it's\n")
        self.assertEqual(self.execute(r"しゅつりょく（“一\n二”）"), "一\n二\n")
        self.assertEqual(
            self.execute(r"しゅつりょく（“引用: \"文字\"”）"), '引用: "文字"\n'
        )
        comment = "# “かず（1）” ‘ながさ（［］）’"
        self.assertEqual(transpile(comment), comment)

    def test_pythonic_aliases(self):
        sources = (
            "でふ 説明（値）：\n"
            "　いふ とぅるー あんど 値 ＞ 0：\n"
            "　　りたーん すとりんぐ（いんと（値） ＋ れん（りすと（“ab”）））\n"
            "　えりふ ふぉるす おあ 値 ＝＝ 0 ならば：\n"
            "　　りたーん “ゼロ”\n"
            "　えるす：\n"
            "　　りたーん “負”\n"
            "数 を ［1, 0, -1］ で ふぉー：\n"
            "　ぷりんと（説明（数））\n"
            "回数 ＝ 0\n"
            "回数 ＜ 2 のあいだ ほわいる：\n"
            "　回数 ＝ 回数 ＋ 1\n"
            "とらい：\n"
            "　いんと（“数字ではありません”）\n"
            "えくせぷと：\n"
            "　ぷりんと（回数）",
            "デフ 説明（値）：\n"
            "　イフ トゥルー アンド 値 ＞ 0：\n"
            "　　リターン ストリング（イント（値） ＋ レン（リスト（“ab”）））\n"
            "　エリフ フォルス オア 値 ＝＝ 0 ならば：\n"
            "　　リターン “ゼロ”\n"
            "　エルス：\n"
            "　　リターン “負”\n"
            "数 を ［1, 0, -1］ で フォー：\n"
            "　プリント（説明（数））\n"
            "回数 ＝ 0\n"
            "回数 ＜ 2 のあいだ ホワイル：\n"
            "　回数 ＝ 回数 ＋ 1\n"
            "トライ：\n"
            "　イント（“数字ではありません”）\n"
            "エクセプト：\n"
            "　プリント（回数）",
        )
        expected = (
            "def 説明(値):\n"
            "    if True and 値 > 0:\n"
            '        return str(int(値) + len(list("ab")))\n'
            "    elif False or 値 == 0:\n"
            '        return "ゼロ"\n'
            "    else:\n"
            '        return "負"\n'
            "for 数 in [1, 0, -1]:\n"
            "    print(説明(数))\n"
            "回数 = 0\n"
            "while 回数 < 2:\n"
            "    回数 = 回数 + 1\n"
            "try:\n"
            '    int("数字ではありません")\n'
            "except Exception:\n"
            "    print(回数)"
        )
        for source in sources:
            with self.subTest(source=source):
                self.assertEqual(transpile(source), expected)
                self.assertEqual(self.execute(source), "3\nゼロ\n負\n2\n")

    def test_pythonic_input_aliases_and_mixed_syntax(self):
        for name in ("いんぷっと", "インプット"):
            with self.subTest(name=name):
                source = (
                    "もし とぅるー アンド しん ならば：\n"
                    f"　しゅつりょく（イント（{name}（“数：”）））"
                )
                with patch("builtins.input", return_value="7") as read_input:
                    self.assertEqual(self.execute(source), "7\n")
                read_input.assert_called_once_with("数：")

    def test_pythonic_alias_preservation(self):
        content = (
            "でふ デフ りたーん リターン いふ イフ えりふ エリフ えるす エルス "
            "ふぉー フォー ほわいる ホワイル とらい トライ えくせぷと エクセプト "
            "あいだ つづける いん イン のなかの のなか "
            "とぅるー トゥルー ふぉるす フォルス あんど アンド おあ オア "
            "ぷりんと プリント いんぷっと インプット いんと イント "
            "すとりんぐ ストリング れん レン りすと リスト"
        )
        for name in content.split():
            with self.subTest(name=name):
                for identifier in (f"独自_{name}", f"{name}の値"):
                    self.assertEqual(
                        transpile(f"{identifier}（1）"), f"{identifier}(1)"
                    )
        for left, right in (
            ('"', '"'),
            ("'", "'"),
            ('"""', '"""'),
            ("'''", "'''"),
            ("“", "”"),
            ("‘", "’"),
        ):
            with self.subTest(left=left):
                self.assertEqual(
                    self.execute(f"プリント（{left}{content}{right}）"),
                    content + "\n",
                )
        comment = f"# {content}"
        self.assertEqual(transpile(comment), comment)
        self.assertEqual(transpile(f"プリント（1） {comment}"), f"print(1) {comment}")

    def test_inline_builtins_and_identifier_boundaries(self):
        source = (
            "しゅつりょく（もじ(かず（“42”） ＋ 1)）\n"
            "しゅつりょく（ながさ（はいれつ（“abc”）））"
        )
        self.assertEqual(self.execute(source), "43\n3\n")
        for name in (
            "しゅつりょく",
            "かず",
            "もじ",
            "ながさ",
            "はいれつ",
            "にゅうりょく",
        ):
            with self.subTest(name=name):
                identifier = f"独自_{name}"
                self.assertEqual(transpile(f"{identifier}(1)"), f"{identifier}(1)")
                self.assertEqual(transpile(f"{identifier}（1）"), f"{identifier}(1)")
                self.assertEqual(transpile(f"{name}の値(1)"), f"{name}の値(1)")
                self.assertEqual(transpile(name), name)
        with patch("builtins.input", return_value="7") as read_input:
            self.assertEqual(
                self.execute("しゅつりょく（かず(にゅうりょく（“数：”）)）"), "7\n"
            )
        read_input.assert_called_once_with("数：")


class RunnerTests(unittest.TestCase):
    def test_pythonic_builtin_references(self):
        for aliases in (
            ("ぷりんと", "いんぷっと", "いんと", "すとりんぐ", "れん", "りすと"),
            ("プリント", "インプット", "イント", "ストリング", "レン", "リスト"),
        ):
            with self.subTest(aliases=aliases):
                (
                    output_alias,
                    input_alias,
                    int_alias,
                    str_alias,
                    len_alias,
                    list_alias,
                ) = aliases
                source = (
                    f"出力 ＝ {output_alias}\n"
                    f"入力 ＝ {input_alias}\n"
                    f"整数 ＝ {int_alias}\n"
                    f"文字列 ＝ {str_alias}\n"
                    f"長さ ＝ {len_alias}\n"
                    f"配列 ＝ {list_alias}\n"
                    "でふ 表示（）：\n"
                    "　出力（文字列（整数（入力（“数：”）） ＋ 長さ（配列（“ab”））））\n"
                    "表示（）"
                )
                output = io.StringIO()
                with patch("builtins.input", return_value="5") as read_input:
                    with redirect_stdout(output):
                        run_code(source)
                self.assertEqual(output.getvalue(), "7\n")
                read_input.assert_called_once_with("数：")

    def test_japanese_builtin_aliases(self):
        source = (
            "出力 ＝ しゅつりょく\n"
            "入力 ＝ にゅうりょく\n"
            "整数 ＝ かず\n"
            "文字列 ＝ もじ\n"
            "長さ ＝ ながさ\n"
            "配列 ＝ はいれつ\n"
            "かんすう 表示():\n"
            "    出力(文字列(整数(入力(“数：”)) ＋ 長さ(配列(“ab”))))\n"
            "表示()"
        )
        output = io.StringIO()
        with patch("builtins.input", return_value="5") as read_input:
            with redirect_stdout(output):
                run_code(source)
        self.assertEqual(output.getvalue(), "7\n")
        read_input.assert_called_once_with("数：")

    def test_script_main_namespace(self):
        output = io.StringIO()
        with redirect_stdout(output):
            run_code("しゅつりょく（__name__）")
        self.assertEqual(output.getvalue(), "__main__\n")

    def test_syntax_error_filename(self):
        with self.assertRaises(SyntaxError) as error:
            run_code("もし しん ならば：", filename="invalid.pai")
        self.assertEqual(error.exception.filename, "invalid.pai")

    def test_utf8_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.pai"
            path.write_text("しゅつりょく（“こんにちは”）", encoding="utf-8")
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
                    result = main([flag, "しゅつりょく（“こんにちは”）"])
                self.assertEqual(result, 0)
                self.assertEqual(output.getvalue(), "こんにちは\n")

    def test_empty_command(self):
        self.assertEqual(main(["-c", ""]), 0)

    def test_file(self):
        with patch("paison.cli.run_file") as execute_file:
            self.assertEqual(main(["sample.pai"]), 0)
        execute_file.assert_called_once_with("sample.pai")

    def test_invalid_arguments(self):
        for argv in ([], ["sample.pai", "-c", "しゅつりょく（1）"], ["-c"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(argv)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
