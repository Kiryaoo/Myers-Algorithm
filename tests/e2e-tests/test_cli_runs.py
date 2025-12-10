import subprocess
import sys
import os
import tempfile
import shutil
import time
from typing import Tuple

CLI_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'src', 'cli.py')
PYTHON = sys.executable


def run_cli(*args, timeout: int = 30) -> Tuple[int, str, str]:
    try:
        r = subprocess.run([PYTHON, CLI_PATH] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'


class TempFileManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def create_file(self, name: str, content: str) -> str:
        path = os.path.join(self.temp_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def cleanup(self):
        shutil.rmtree(self.temp_dir)


class TestCLIBasic:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_version_flag(self):
        code, out, _ = run_cli('--version')
        assert code == 0 and '1.0.0' in out or '1.0.0' in _

    def test_version_short(self):
        assert run_cli('-v')[0] == 0

    def test_help_flag(self):
        code, out, _ = run_cli('--help')
        assert code == 0 and 'usage' in out.lower()

    def test_help_shows_options(self):
        _, out, _ = run_cli('--help')
        assert '--unified' in out and '--html' in out

    def test_missing_file_error(self):
        f = self.temp.create_file('exists.txt', 'x')
        assert run_cli('nonexistent.txt', f)[0] == 2
        assert run_cli(f, 'nonexistent.txt')[0] == 2

    def test_missing_both_files(self):
        code, _, err = run_cli('a.txt', 'b.txt')
        assert code == 2 and ('not found' in err.lower() or 'error' in err.lower())


class TestCLICompare:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_identical_files(self):
        c = "line1\nline2\n"
        f1, f2 = self.temp.create_file('a.txt', c), self.temp.create_file('b.txt', c)
        assert run_cli(f1, f2)[0] == 0

    def test_identical_empty(self):
        f1, f2 = self.temp.create_file('a.txt', ''), self.temp.create_file('b.txt', '')
        assert run_cli(f1, f2)[0] == 0

    def test_identical_large(self):
        c = '\n'.join(f"line_{i}" for i in range(500))
        f1, f2 = self.temp.create_file('a.txt', c), self.temp.create_file('b.txt', c)
        assert run_cli(f1, f2)[0] == 0

    def test_different_files(self):
        f1 = self.temp.create_file('a.txt', 'old\n')
        f2 = self.temp.create_file('b.txt', 'new\n')
        assert run_cli(f1, f2)[0] == 1

    def test_added_line(self):
        f1 = self.temp.create_file('a.txt', 'a\n')
        f2 = self.temp.create_file('b.txt', 'a\nb\n')
        assert run_cli(f1, f2)[0] == 1

    def test_removed_line(self):
        f1 = self.temp.create_file('a.txt', 'a\nb\n')
        f2 = self.temp.create_file('b.txt', 'a\n')
        assert run_cli(f1, f2)[0] == 1

    def test_empty_vs_nonempty(self):
        f1 = self.temp.create_file('a.txt', '')
        f2 = self.temp.create_file('b.txt', 'x\n')
        assert run_cli(f1, f2)[0] == 1


class TestCLIFormats:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def _files(self):
        return (self.temp.create_file('a.txt', 'old\n'),
                self.temp.create_file('b.txt', 'new\n'))

    def test_quiet_mode(self):
        f1, f2 = self._files()
        code, out, _ = run_cli(f1, f2, '--quiet')
        assert code == 1

    def test_quiet_short(self):
        f1, f2 = self._files()
        assert run_cli(f1, f2, '-q')[0] == 1

    def test_unified_format(self):
        f1, f2 = self._files()
        _, out, _ = run_cli(f1, f2, '--unified')
        assert '---' in out and '+++' in out and '@@' in out

    def test_side_by_side(self):
        f1, f2 = self._files()
        code, out, _ = run_cli(f1, f2, '-y', '--no-color')
        assert code == 1

    def test_html_format(self):
        f1, f2 = self._files()
        _, out, _ = run_cli(f1, f2, '--html')
        assert '<!DOCTYPE html>' in out and '<table' in out

    def test_simple_format(self):
        f1, f2 = self._files()
        assert run_cli(f1, f2, '-s', '--no-color')[0] == 1


class TestCLIOutput:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_output_to_file(self):
        f1 = self.temp.create_file('a.txt', 'old\n')
        f2 = self.temp.create_file('b.txt', 'new\n')
        out = os.path.join(self.temp.temp_dir, 'out.diff')
        run_cli(f1, f2, '-o', out)
        assert os.path.exists(out) and os.path.getsize(out) > 0

    def test_html_to_file(self):
        f1 = self.temp.create_file('a.txt', 'old\n')
        f2 = self.temp.create_file('b.txt', 'new\n')
        out = os.path.join(self.temp.temp_dir, 'out.html')
        run_cli(f1, f2, '--html', '-o', out)
        with open(out) as f:
            assert '<!DOCTYPE html>' in f.read()

    def test_context_flag(self):
        f1 = self.temp.create_file('a.txt', 'a\nb\nc\n')
        f2 = self.temp.create_file('b.txt', 'a\nX\nc\n')
        assert run_cli(f1, f2, '-c', '2')[0] == 1


class TestCLISpecial:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_binary_file_error(self):
        f = self.temp.create_file('a.txt', 'text\n')
        bp = os.path.join(self.temp.temp_dir, 'b.bin')
        with open(bp, 'wb') as b:
            b.write(b'\x89PNG\r\n\x1a\n')
        code, _, err = run_cli(f, bp)
        assert code == 2

    def test_unicode_files(self):
        f1 = self.temp.create_file('a.txt', 'Hello\n')
        f2 = self.temp.create_file('b.txt', 'Changed\n')
        assert run_cli(f1, f2, '--no-color')[0] == 1

    def test_ignore_whitespace(self):
        f1 = self.temp.create_file('a.txt', 'hello world\n')
        f2 = self.temp.create_file('b.txt', '  hello world  \n')
        assert run_cli(f1, f2, '--ignore-whitespace')[0] == 0

    def test_ignore_case(self):
        f1 = self.temp.create_file('a.txt', 'Hello\n')
        f2 = self.temp.create_file('b.txt', 'hello\n')
        assert run_cli(f1, f2, '--ignore-case')[0] == 0


class TestCLIPerformance:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_medium_files_fast(self):
        lines = [f"line_{i}" for i in range(500)]
        c1 = '\n'.join(lines)
        lines[::10] = [f"MOD_{i}" for i in range(50)]
        c2 = '\n'.join(lines)
        f1 = self.temp.create_file('a.txt', c1)
        f2 = self.temp.create_file('b.txt', c2)
        start = time.time()
        assert run_cli(f1, f2, '-q')[0] == 1
        assert time.time() - start < 10

    def test_large_identical_fast(self):
        c = '\n'.join(f"line_{i}" for i in range(2000))
        f1 = self.temp.create_file('a.txt', c)
        f2 = self.temp.create_file('b.txt', c)
        start = time.time()
        assert run_cli(f1, f2, '-q')[0] == 0
        assert time.time() - start < 5


class TestCLIEdgeCases:
    def setup_method(self):
        self.temp = TempFileManager()

    def teardown_method(self):
        self.temp.cleanup()

    def test_single_newline(self):
        f1 = self.temp.create_file('a.txt', '\n')
        f2 = self.temp.create_file('b.txt', '\n')
        assert run_cli(f1, f2)[0] == 0

    def test_no_trailing_newline(self):
        f1 = self.temp.create_file('a.txt', 'no nl')
        f2 = self.temp.create_file('b.txt', 'no nl')
        assert run_cli(f1, f2)[0] == 0

    def test_whitespace_diff(self):
        f1 = self.temp.create_file('a.txt', 'line\n')
        f2 = self.temp.create_file('b.txt', 'line \n')
        assert run_cli(f1, f2)[0] == 1

    def test_change_semantics(self):
        f1 = self.temp.create_file('a.txt', 'a\nb\nc\n')
        f2 = self.temp.create_file('b.txt', 'a\nX\nc\n')
        code, out, _ = run_cli(f1, f2, '--unified', '--no-color')
        assert code == 1


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])

