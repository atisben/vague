"""vague ui command: serve the usage graph on localhost."""

from __future__ import annotations

import webbrowser

import typer

from vague.sdk.core.ui_server import make_server


def cmd_ui(port: int = 8765, open_browser: bool = True) -> None:
    try:
        httpd = make_server(port=port)
    except OSError as e:
        typer.echo(f"Cannot bind 127.0.0.1:{port}: {e}. Try --port.", err=True)
        raise typer.Exit(1) from e
    url = f"http://127.0.0.1:{httpd.server_port}"
    typer.echo(f"vague ui on {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        typer.echo("stopped")
    finally:
        httpd.server_close()
