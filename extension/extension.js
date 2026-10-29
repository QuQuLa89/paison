const vscode = require("vscode");

function activate(context) {
  const runFile = vscode.commands.registerCommand("paison.runFile", async () => {
    const editor = vscode.window.activeTextEditor;

    if (!editor || !editor.document.fileName.toLowerCase().endsWith(".pai")) {
      vscode.window.showWarningMessage("実行する.paiファイルを開いてください。");
      return;
    }

    const document = editor.document;

    if (document.uri.scheme !== "file") {
      vscode.window.showWarningMessage(
        "実行するファイルをローカルに保存してください。",
      );
      return;
    }

    try {
      if (!(await document.save())) {
        vscode.window.showWarningMessage(
          "ファイルを保存できなかったため、実行を中止しました。",
        );
        return;
      }

      const terminal = vscode.window.createTerminal({
        name: "Paison",
        shellPath: "paison",
        shellArgs: [document.uri.fsPath],
      });
      context.subscriptions.push(terminal);
      terminal.show();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      vscode.window.showErrorMessage(`Paisonの実行に失敗しました: ${message}`);
    }
  });

  context.subscriptions.push(runFile);
}

module.exports = { activate };
