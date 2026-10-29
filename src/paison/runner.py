"""Runner for executing Paison code."""

from pathlib import Path

from paison.transpiler import transpile


def run_code(source: str, filename: str = "<paison>") -> None:
    """Transpile and execute a script in its own global namespace."""
    compiled = compile(transpile(source), filename, "exec")
    namespace = {
        "__name__": "__main__",
        "しゅつりょく": print,
        "にゅうりょく": input,
        "かず": int,
        "もじ": str,
        "ながさ": len,
        "はいれつ": list,
    }
    exec(compiled, namespace)


def run_file(file_path: str) -> None:
    """Read and execute a UTF-8 Paison file."""
    source = Path(file_path).read_text(encoding="utf-8")
    run_code(source, filename=str(file_path))
