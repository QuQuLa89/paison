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
            r"「.*?」",
            r"『.*?』",
            r"\#[^\r\n]*",
        )
    ),
    re.DOTALL,
)
_SYMBOLS = str.maketrans("＝：＞＜＋－＊／（）［］", "=:><+-*/()[]")
_BUILTINS = {
    "かず": "int",
    "もじ": "str",
    "ながさ": "len",
    "はいれつ": "list",
    "にゅうりょく": "input",
}
_BUILTIN_CALLS = re.compile(r"(?<!\w)(" + "|".join(_BUILTINS) + r")(?=\s*\()")
_STATEMENTS = (
    (r"しゅつりょく\s+(.+)", r"print(\1)"),
    (r"もし\s+(.+?)\s*ならば\s*:", r"if \1:"),
    (r"それとも\s+(.+?)\s*ならば\s*:", r"elif \1:"),
    (r"ちがうなら\s*:", "else:"),
    (r"(\w+)\s*を\s*(.+?)\s*で\s*くりかえす\s*:", r"for \1 in \2:"),
    (r"(.+?)\s*のあいだ\s*くりかえす\s*:", r"while \1:"),
    (
        r"かんすう\s+(?P<name>\w+)\s*\((?P<args>.*?)\)\s*:",
        r"def \g<name>(\g<args>):",
    ),
    (r"かえす\s+(?P<val>.*)", r"return \g<val>"),
    (r"こころみる\s*:", "try:"),
    (r"しっぱいしたとき\s*:", "except Exception:"),
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
        if literal.startswith("「"):
            content = literal[1:-1]
            content = content.replace("\\", "\\\\").replace('"', '\\"')
            content = content.replace("\r", "\\r").replace("\n", "\\n")
            literal = '"' + content + '"'
        elif literal.startswith("『"):
            content = literal[1:-1]
            content = content.replace("\\", "\\\\").replace("'", "\\'")
            literal = "'''" + content + "'''"
        elif literal.startswith(("“", "‘")):
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
        code = code.rstrip().replace("！＝", "!=").translate(_SYMBOLS)
        code = re.sub(r"(?<=\s)かつ(?=\s)", "and", code)
        code = re.sub(r"(?<=\s)または(?=\s)", "or", code)
        code = re.sub(
            r"(?<!\w)(しん|ぎ)(?!\w)",
            lambda match: "True" if match.group() == "しん" else "False",
            code,
        )
        code = _BUILTIN_CALLS.sub(lambda match: _BUILTINS[match.group()], code)
        for pattern, replacement in _STATEMENTS:
            match = re.fullmatch(pattern, code)
            if match:
                code = match.expand(replacement)
                break
        lines.append(
            indent.replace("\u3000", "    ") + code + trailing_space + marker + comment
        )

    result = "\n".join(lines)
    return re.sub(
        re.escape(prefix) + r"(\d+)__",
        lambda match: literals[int(match.group(1))],
        result,
    )
