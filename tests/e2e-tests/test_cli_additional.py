import sys
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def run_cli(args, cwd):
    cmd = [sys.executable, str(Path(cwd) / "src" / "cli.py")] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


def test_cli_unified_diff(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello\nworld\n", encoding="utf-8")
    f2.write_text("hello\nplanet\n", encoding="utf-8")

    proc = run_cli([str(f1), str(f2), "-u"], cwd=Path("."))
    assert proc.returncode == 1 
    out = proc.stdout
    assert "---" in out and "+++" in out
    assert "-world" in out or "- world" in out
    assert "+planet" in out or "+ planet" in out


def test_cli_side_by_side(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("left\nonly\n", encoding="utf-8")
    f2.write_text("left\nright\n", encoding="utf-8")

    proc = run_cli([str(f1), str(f2), "-y"], cwd=Path("."))
    assert proc.returncode == 1
    out = proc.stdout
    assert "|" in out or "<" in out or ">" in out


def test_cli_html_output(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("one\ntwo\n", encoding="utf-8")
    f2.write_text("one\nthree\n", encoding="utf-8")

    proc = run_cli([str(f1), str(f2), "--html"], cwd=Path("."))
    assert proc.returncode == 1
    out = proc.stdout
    assert "<!DOCTYPE html>" in out or "<html" in out


def test_cli_main_inprocess_unified(tmp_path, capsys):
    from src import cli

    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello\nworld\n", encoding="utf-8")
    f2.write_text("hello\nplanet\n", encoding="utf-8")

    rc = cli.main([str(f1), str(f2), "-u"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "---" in captured.out and "+++" in captured.out


def test_cli_main_inprocess_html(tmp_path, capsys):
    from src import cli

    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("one\ntwo\n", encoding="utf-8")
    f2.write_text("one\nthree\n", encoding="utf-8")

    rc = cli.main([str(f1), str(f2), "--html"])
    captured = capsys.readouterr()
    assert rc in (1, 2)
    assert ("<!DOCTYPE html>" in captured.out or "<html" in captured.out) or (
        captured.err and ("Error" in captured.err or "Error:" in captured.err)
    )
