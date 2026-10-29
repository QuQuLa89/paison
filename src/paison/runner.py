"""Runner for executing Paison code."""

from pathlib import Path

from paison.transpiler import transpile


def run_code(source: str, filename: str = "<paison>") -> None:
    """Transpile and execute a script in its own global namespace."""
    compiled = compile(transpile(source), filename, "exec")
    namespace = {
        "__name__": "__main__",
        "しゅつりょく": print,
        "ぷりんと": print,
        "プリント": print,
        "にゅうりょく": input,
        "いんぷっと": input,
        "インプット": input,
        "かず": int,
        "いんと": int,
        "イント": int,
        "もじ": str,
        "すとりんぐ": str,
        "ストリング": str,
        "ながさ": len,
        "れん": len,
        "レン": len,
        "はいれつ": list,
        "りすと": list,
        "リスト": list,
    }
    exec(compiled, namespace)


def run_file(file_path: str) -> None:
    """Read and execute a UTF-8 Paison file."""
    source = Path(file_path).read_text(encoding="utf-8")
    run_code(source, filename=str(file_path))
