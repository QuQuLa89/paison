"""CLI for Paison."""

import argparse

from paison.runner import run_code, run_file


def main(argv=None) -> int:
    """Execute a Paison file or an inline command."""
    parser = argparse.ArgumentParser(description="Paisonスクリプトを実行します。")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("file", nargs="?", help="実行する.paiファイルを指定します。")
    inputs.add_argument(
        "-c", "--command", help="直接実行するPaisonコードを指定します。"
    )
    args = parser.parse_args(argv)

    if args.command is not None:
        run_code(args.command)
    else:
        run_file(args.file)
    return 0
