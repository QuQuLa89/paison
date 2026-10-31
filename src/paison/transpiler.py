"""Transpiler for Paison Phase 1."""

import re


_LITERALS = re.compile(
    "|".join(
        (
            r'"""(?:\\.|(?!""").)*"""',
            r"'''(?:\\.|(?!''').)*'''",
            r'"(?:\\.|[^"\\\r\n])*"',
            r"'(?:\\.|[^'\\\r\n])*'",
            r"“(?:\\.|[^”\\\r\n])*”",
            r"‘(?:\\.|[^’\\\r\n])*’",
            r"\#[^\r\n]*",
        )
    ),
    re.DOTALL,
)
_SYMBOLS = str.maketrans(
    "＝：＞＜＋－＊／（）［］｛｝０１２３４５６７８９．", "=:><+-*/()[]{}0123456789."
)
_BUILTINS = {
    "しゅつりょく": "print",
    "ぷりんと": "print",
    "プリント": "print",
    "かず": "int",
    "いんと": "int",
    "イント": "int",
    "もじ": "str",
    "すとりんぐ": "str",
    "ストリング": "str",
    "ながさ": "len",
    "れん": "len",
    "レン": "len",
    "はいれつ": "list",
    "りすと": "list",
    "リスト": "list",
    "にゅうりょく": "input",
    "いんぷっと": "input",
    "インプット": "input",
    "はんい": "range",
    "れんじ": "range",
    "レンジ": "range",
    "しょうすう": "float",
    "ふろーと": "float",
    "フロート": "float",
    "しんぎ": "bool",
    "ぶーる": "bool",
    "ブール": "bool",
    "ごうけい": "sum",
    "さむ": "sum",
    "サム": "sum",
    "さいだい": "max",
    "まっくす": "max",
    "マックス": "max",
    "さいしょう": "min",
    "みん": "min",
    "ミン": "min",
    "ぜったいち": "abs",
    "あぶす": "abs",
    "アブス": "abs",
    "じしょ": "dict",
    "でぃくと": "dict",
    "ディクト": "dict",
}
_BUILTIN_CALLS = re.compile(r"(?<!\w)(" + "|".join(_BUILTINS) + r")(?=\s*\()")
_STATEMENTS = (
    (r"(?:もし|いふ|イフ)\s+(.+?)(?:\s*ならば)?\s*:", r"if \1:"),
    (r"(?:それとも|えりふ|エリフ)\s+(.+?)(?:\s*ならば)?\s*:", r"elif \1:"),
    (r"(?:ちがうなら|えるす|エルス)\s*:", "else:"),
    (
        r"(?:ふぉー|フォー)\s+(\w+)\s+(?:いん|イン)\s+(.+?)\s*:",
        r"for \1 in \2:",
    ),
    (
        r"くりかえす\s+(\w+)\s+(?:のなかの|のなか|で)\s+(.+?)\s*:",
        r"for \1 in \2:",
    ),
    (r"(?:ほわいる|ホワイル|あいだ|つづける)\s+(.+?)\s*:", r"while \1:"),
    (
        r"(\w+)\s*を\s*(.+?)\s*で\s*(?:くりかえす|ふぉー|フォー)\s*:",
        r"for \1 in \2:",
    ),
    (r"(.+?)\s*のあいだ\s*(?:くりかえす|ほわいる|ホワイル)\s*:", r"while \1:"),
    (
        r"(?:かんすう|でふ|デフ)\s+(?P<name>\w+)\s*\((?P<args>.*?)\)\s*:",
        r"def \g<name>(\g<args>):",
    ),
    (r"(?:かえす|りたーん|リターン)\s+(?P<val>.*)", r"return \g<val>"),
    (r"(?:こころみる|とらい|トライ)\s*:", "try:"),
    (r"(?:しっぱいしたとき|えくせぷと|エクセプト)\s*:", "except Exception:"),
    (r"(?:ぬける|やめる|ぶれーく|ブレーク)", "break"),
    (r"(?:つぎへ|とばす|こんてぃにゅー|コンティニュー)", "continue"),
    (r"(?:なにもしない|ぱす|パス)", "pass"),
    (
        r"(?P<target>\w+)\s*に\s*(?P<val>.+?)\s*を\s*ついか",
        r"\g<target>.append(\g<val>)",
    ),
)


def transpile(source: str) -> str:
    """Convert Paison syntax to Python while preserving literals and comments."""
    literals = []
    prefix = "__paison_literal_"
    while prefix in source:
        prefix = "_" + prefix

    def protect(match: re.Match) -> str:
        literal = match.group()
        if literal.startswith("#"):
            return literal
        if literal.startswith(("“", "‘")):
            quote = '"' if literal.startswith("“") else "'"
            content = re.sub(
                r"\\.|" + re.escape(quote),
                lambda match: "\\" + quote if match.group() == quote else match.group(),
                literal[1:-1],
            )
            literal = quote + content + quote
        token = f"{prefix}{len(literals)}__"
        literals.append(literal)
        return token

    protected = _LITERALS.sub(protect, source)
    lines = []
    for line in protected.split("\n"):
        line = line.rstrip("\r")
        indent_match = re.match(r"[ \t\u3000]*", line)
        indent = indent_match.group()
        code, marker, comment = line[len(indent) :].partition("#")
        trailing_space = code[len(code.rstrip()) :]
        trailing_space = trailing_space.replace("\u3000", " ")
        code = code.rstrip().replace("！＝", "!=").translate(_SYMBOLS)
        code = code.replace("\u3000", " ")
        code = re.sub(r"(?<=\s)(?:かつ|あんど|アンド)(?=\s)", "and", code)
        code = re.sub(r"(?<=\s)(?:または|おあ|オア)(?=\s)", "or", code)
        code = re.sub(
            r"(?<!\w)(?:しん|とぅるー|トゥルー)(?!\w)",
            "True",
            code,
        )
        code = re.sub(
            r"(?<!\w)(?:ぎ|ふぉるす|フォルス)(?!\w)",
            "False",
            code,
        )
        code = re.sub(r"(?<!\w)(?:なし|のん|ノン)(?!\w)", "None", code)
        code = re.sub(r"(?<=\s)(?:でない|のっと|ノット)(?=\s)", "not", code)
        code = re.sub(r"(?<!\w)(?:のっと|ノット)(?=\s)", "not", code)
        code = _BUILTIN_CALLS.sub(lambda match: _BUILTINS[match.group()], code)
        for pattern, replacement in _STATEMENTS:
            match = re.fullmatch(pattern, code)
            if match:
                code = match.expand(replacement)
                break
        code = re.sub(r"(?<=\s)(?:のなかに|ふくまれる|いん|イン)(?=\s)", "in", code)
        lines.append(
            indent.replace("\u3000", "    ") + code + trailing_space + marker + comment
        )

    result = "\n".join(lines)
    return re.sub(
        re.escape(prefix) + r"(\d+)__",
        lambda match: literals[int(match.group(1))],
        result,
    )
