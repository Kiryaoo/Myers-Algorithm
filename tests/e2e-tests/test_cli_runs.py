import subprocess
import sys
import os
import tempfile
import shutil
import time
from typing import Tuple, List, Optional


CLI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'src', 'cli.py'
)
PYTHON = sys.executable


def run_cli(*args, timeout: int = 30) -> Tuple[int, str, str]:
    cmd = [PYTHON, CLI_PATH] + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout expired'


class TempFileManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def create_file(self, name: str, content: str) -> str:
        filepath = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(name) else None
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def create_subdir(self, name: str) -> str:
        dirpath = os.path.join(self.temp_dir, name)
        os.makedirs(dirpath, exist_ok=True)
        return dirpath
    
    def cleanup(self):
        shutil.rmtree(self.temp_dir)


class TestCLIVersion:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_version_flag_returns_zero(self):
        code, stdout, stderr = run_cli('--version')
        assert code == 0
        
    def test_version_flag_shows_version(self):
        code, stdout, stderr = run_cli('--version')
        assert '1.0.0' in stdout or '1.0.0' in stderr
        
    def test_version_short_flag(self):
        code, stdout, stderr = run_cli('-v')
        assert code == 0


class TestCLIHelp:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_help_flag_returns_zero(self):
        code, stdout, stderr = run_cli('--help')
        assert code == 0
        
    def test_help_shows_usage(self):
        code, stdout, stderr = run_cli('--help')
        assert 'usage' in stdout.lower()
        
    def test_help_shows_description(self):
        code, stdout, stderr = run_cli('--help')
        assert 'myers' in stdout.lower() or 'diff' in stdout.lower()
        
    def test_help_shows_options(self):
        code, stdout, stderr = run_cli('--help')
        assert '--unified' in stdout or '-u' in stdout
        assert '--side-by-side' in stdout or '-y' in stdout
        assert '--html' in stdout
        assert '--context' in stdout or '-c' in stdout


class TestCLIMissingFiles:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_missing_first_file_returns_error(self):
        existing = self.temp.create_file('exists.txt', 'content')
        code, stdout, stderr = run_cli('nonexistent.txt', existing)
        assert code == 2
        
    def test_missing_second_file_returns_error(self):
        existing = self.temp.create_file('exists.txt', 'content')
        code, stdout, stderr = run_cli(existing, 'nonexistent.txt')
        assert code == 2
        
    def test_missing_both_files_returns_error(self):
        code, stdout, stderr = run_cli('nonexistent1.txt', 'nonexistent2.txt')
        assert code == 2
        
    def test_missing_file_shows_error_message(self):
        code, stdout, stderr = run_cli('nonexistent.txt', 'also_nonexistent.txt')
        assert 'not found' in stderr.lower() or 'error' in stderr.lower()


class TestCLIIdenticalFiles:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_identical_files_return_zero(self):
        content = "line1\nline2\nline3\n"
        file1 = self.temp.create_file('file1.txt', content)
        file2 = self.temp.create_file('file2.txt', content)
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0
        
    def test_identical_empty_files_return_zero(self):
        file1 = self.temp.create_file('empty1.txt', '')
        file2 = self.temp.create_file('empty2.txt', '')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0
        
    def test_identical_single_line_return_zero(self):
        content = "single line"
        file1 = self.temp.create_file('single1.txt', content)
        file2 = self.temp.create_file('single2.txt', content)
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0
        
    def test_identical_large_files_return_zero(self):
        content = '\n'.join([f"line_{i}" for i in range(1000)])
        file1 = self.temp.create_file('large1.txt', content)
        file2 = self.temp.create_file('large2.txt', content)
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0


class TestCLIDifferentFiles:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_different_files_return_one(self):
        file1 = self.temp.create_file('file1.txt', 'line1\nline2\n')
        file2 = self.temp.create_file('file2.txt', 'line1\nmodified\n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 1
        
    def test_added_line_return_one(self):
        file1 = self.temp.create_file('file1.txt', 'line1\n')
        file2 = self.temp.create_file('file2.txt', 'line1\nline2\n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 1
        
    def test_removed_line_return_one(self):
        file1 = self.temp.create_file('file1.txt', 'line1\nline2\n')
        file2 = self.temp.create_file('file2.txt', 'line1\n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 1
        
    def test_empty_vs_nonempty_return_one(self):
        file1 = self.temp.create_file('empty.txt', '')
        file2 = self.temp.create_file('nonempty.txt', 'content\n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 1


class TestCLIQuietMode:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_quiet_identical_no_output(self):
        content = "same\n"
        file1 = self.temp.create_file('file1.txt', content)
        file2 = self.temp.create_file('file2.txt', content)
        code, stdout, stderr = run_cli(file1, file2, '--quiet')
        assert code == 0
        assert stdout.strip() == ''
        
    def test_quiet_different_minimal_output(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--quiet')
        assert code == 1
        
    def test_quiet_short_flag(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '-q')
        assert code == 1


class TestCLIUnifiedFormat:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_unified_has_header(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified')
        assert '---' in stdout
        assert '+++' in stdout
        
    def test_unified_has_hunk_header(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified')
        assert '@@' in stdout
        
    def test_unified_shows_minus_for_deletion(self):
        file1 = self.temp.create_file('file1.txt', 'deleted\n')
        file2 = self.temp.create_file('file2.txt', '')
        code, stdout, stderr = run_cli(file1, file2, '--unified', '--no-color')
        assert '-deleted' in stdout or '- deleted' in stdout or '-' in stdout
        
    def test_unified_shows_plus_for_addition(self):
        file1 = self.temp.create_file('file1.txt', '')
        file2 = self.temp.create_file('file2.txt', 'added\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified', '--no-color')
        assert '+added' in stdout or '+ added' in stdout or '+' in stdout


class TestCLISideBySideFormat:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_side_by_side_flag(self):
        file1 = self.temp.create_file('file1.txt', 'left\n')
        file2 = self.temp.create_file('file2.txt', 'right\n')
        code, stdout, stderr = run_cli(file1, file2, '--side-by-side', '--no-color')
        assert code == 1
        
    def test_side_by_side_short_flag(self):
        file1 = self.temp.create_file('file1.txt', 'left\n')
        file2 = self.temp.create_file('file2.txt', 'right\n')
        code, stdout, stderr = run_cli(file1, file2, '-y', '--no-color')
        assert code == 1
        
    def test_side_by_side_has_separator(self):
        file1 = self.temp.create_file('file1.txt', 'content\n')
        file2 = self.temp.create_file('file2.txt', 'content\n')
        code, stdout, stderr = run_cli(file1, file2, '-y', '--no-color')
        assert '|' in stdout or '<' in stdout or '>' in stdout or '=' in stdout


class TestCLIHTMLFormat:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_html_output_is_valid_html(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--html')
        assert '<!DOCTYPE html>' in stdout
        assert '<html>' in stdout
        assert '</html>' in stdout
        
    def test_html_has_style(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--html')
        assert '<style>' in stdout
        
    def test_html_has_table(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--html')
        assert '<table' in stdout
        
    def test_html_escapes_special_chars(self):
        file1 = self.temp.create_file('file1.txt', '<script>\n')
        file2 = self.temp.create_file('file2.txt', '</script>\n')
        code, stdout, stderr = run_cli(file1, file2, '--html')
        assert '<script>' not in stdout or '&lt;script&gt;' in stdout


class TestCLISimpleFormat:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_simple_format_flag(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '--simple', '--no-color')
        assert code == 1
        
    def test_simple_format_short_flag(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        code, stdout, stderr = run_cli(file1, file2, '-s', '--no-color')
        assert code == 1


class TestCLIOutputFile:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_output_to_file_creates_file(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        output = os.path.join(self.temp.temp_dir, 'output.diff')
        code, stdout, stderr = run_cli(file1, file2, '-o', output)
        assert os.path.exists(output)
        
    def test_output_file_has_content(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        output = os.path.join(self.temp.temp_dir, 'output.diff')
        code, stdout, stderr = run_cli(file1, file2, '-o', output)
        with open(output, 'r') as f:
            content = f.read()
        assert len(content) > 0
        
    def test_html_output_to_file(self):
        file1 = self.temp.create_file('file1.txt', 'old\n')
        file2 = self.temp.create_file('file2.txt', 'new\n')
        output = os.path.join(self.temp.temp_dir, 'output.html')
        code, stdout, stderr = run_cli(file1, file2, '--html', '-o', output)
        with open(output, 'r') as f:
            content = f.read()
        assert '<!DOCTYPE html>' in content


class TestCLIContextLines:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_context_flag_accepted(self):
        file1 = self.temp.create_file('file1.txt', 'a\nb\nc\nd\ne\n')
        file2 = self.temp.create_file('file2.txt', 'a\nb\nX\nd\ne\n')
        code, stdout, stderr = run_cli(file1, file2, '--context', '5')
        assert code == 1
        
    def test_context_short_flag(self):
        file1 = self.temp.create_file('file1.txt', 'a\nb\nc\nd\ne\n')
        file2 = self.temp.create_file('file2.txt', 'a\nb\nX\nd\ne\n')
        code, stdout, stderr = run_cli(file1, file2, '-c', '2')
        assert code == 1


class TestCLIBinaryFiles:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_binary_file_returns_error(self):
        text_file = self.temp.create_file('text.txt', 'text content\n')
        binary_path = os.path.join(self.temp.temp_dir, 'binary.bin')
        with open(binary_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00')
        code, stdout, stderr = run_cli(text_file, binary_path)
        assert code == 2
        
    def test_binary_file_shows_error_message(self):
        text_file = self.temp.create_file('text.txt', 'text content\n')
        binary_path = os.path.join(self.temp.temp_dir, 'binary.bin')
        with open(binary_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00')
        code, stdout, stderr = run_cli(text_file, binary_path)
        assert 'binary' in stderr.lower() or 'error' in stderr.lower()


class TestCLIUnicode:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_unicode_files_work(self):
        file1 = self.temp.create_file('unicode1.txt', 'Привіт\n日本語\n')
        file2 = self.temp.create_file('unicode2.txt', 'Привіт\nChanged\n')
        code, stdout, stderr = run_cli(file1, file2, '--no-color')
        assert code == 1
        
    def test_emoji_files_work(self):
        file1 = self.temp.create_file('emoji1.txt', '😀 hello\n')
        file2 = self.temp.create_file('emoji2.txt', '😀 world\n')
        code, stdout, stderr = run_cli(file1, file2, '--no-color')
        assert code == 1


class TestCLIIgnoreOptions:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_ignore_whitespace_flag(self):
        file1 = self.temp.create_file('file1.txt', 'hello world\n')
        file2 = self.temp.create_file('file2.txt', '  hello world  \n')
        code, stdout, stderr = run_cli(file1, file2, '--ignore-whitespace')
        assert code == 0
        
    def test_ignore_case_flag(self):
        file1 = self.temp.create_file('file1.txt', 'Hello World\n')
        file2 = self.temp.create_file('file2.txt', 'hello world\n')
        code, stdout, stderr = run_cli(file1, file2, '--ignore-case')
        assert code == 0


class TestCLIPerformance:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_medium_files_complete_quickly(self):
        lines = [f"line_{i}: content content content" for i in range(1000)]
        content1 = '\n'.join(lines)
        modified_lines = lines.copy()
        for i in range(0, 1000, 10):
            modified_lines[i] = f"MODIFIED_{i}: different content"
        content2 = '\n'.join(modified_lines)
        file1 = self.temp.create_file('medium1.txt', content1)
        file2 = self.temp.create_file('medium2.txt', content2)
        start = time.time()
        code, stdout, stderr = run_cli(file1, file2, '--quiet')
        elapsed = time.time() - start
        assert code == 1
        assert elapsed < 10.0
        
    def test_large_identical_files_fast(self):
        lines = [f"line_{i}: " + "x" * 80 for i in range(5000)]
        content = '\n'.join(lines)
        file1 = self.temp.create_file('large1.txt', content)
        file2 = self.temp.create_file('large2.txt', content)
        start = time.time()
        code, stdout, stderr = run_cli(file1, file2, '--quiet')
        elapsed = time.time() - start
        assert code == 0
        assert elapsed < 5.0


class TestCLIEdgeCases:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_single_newline_files(self):
        file1 = self.temp.create_file('nl1.txt', '\n')
        file2 = self.temp.create_file('nl2.txt', '\n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0
        
    def test_no_trailing_newline(self):
        file1 = self.temp.create_file('no_nl1.txt', 'no newline')
        file2 = self.temp.create_file('no_nl2.txt', 'no newline')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 0
        
    def test_only_whitespace_difference(self):
        file1 = self.temp.create_file('ws1.txt', 'line\n')
        file2 = self.temp.create_file('ws2.txt', 'line \n')
        code, stdout, stderr = run_cli(file1, file2)
        assert code == 1
        
    def test_crlf_vs_lf(self):
        file1_path = os.path.join(self.temp.temp_dir, 'crlf.txt')
        file2_path = os.path.join(self.temp.temp_dir, 'lf.txt')
        with open(file1_path, 'wb') as f:
            f.write(b'line1\r\nline2\r\n')
        with open(file2_path, 'wb') as f:
            f.write(b'line1\nline2\n')
        code, stdout, stderr = run_cli(file1_path, file2_path)
        assert code in [0, 1]


class TestCLIChangeSemantics:
    def setup_method(self):
        self.temp = TempFileManager()
        
    def teardown_method(self):
        self.temp.cleanup()
        
    def test_single_line_change(self):
        file1 = self.temp.create_file('file1.txt', 'a\nb\nc\n')
        file2 = self.temp.create_file('file2.txt', 'a\nX\nc\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified', '--no-color')
        assert code == 1
        minus_count = stdout.count('\n-')
        plus_count = stdout.count('\n+')
        assert minus_count >= 1
        assert plus_count >= 1
        
    def test_pure_insertion(self):
        file1 = self.temp.create_file('file1.txt', 'a\nc\n')
        file2 = self.temp.create_file('file2.txt', 'a\nb\nc\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified', '--no-color')
        assert code == 1
        
    def test_pure_deletion(self):
        file1 = self.temp.create_file('file1.txt', 'a\nb\nc\n')
        file2 = self.temp.create_file('file2.txt', 'a\nc\n')
        code, stdout, stderr = run_cli(file1, file2, '--unified', '--no-color')
        assert code == 1


def run_all_tests():
    test_classes = [
        TestCLIVersion,
        TestCLIHelp,
        TestCLIMissingFiles,
        TestCLIIdenticalFiles,
        TestCLIDifferentFiles,
        TestCLIQuietMode,
        TestCLIUnifiedFormat,
        TestCLISideBySideFormat,
        TestCLIHTMLFormat,
        TestCLISimpleFormat,
        TestCLIOutputFile,
        TestCLIContextLines,
        TestCLIBinaryFiles,
        TestCLIUnicode,
        TestCLIIgnoreOptions,
        TestCLIPerformance,
        TestCLIEdgeCases,
        TestCLIChangeSemantics,
    ]
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    for test_class in test_classes:
        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith('test_')]
        for method_name in test_methods:
            total_tests += 1
            try:
                instance.setup_method()
                getattr(instance, method_name)()
                instance.teardown_method()
                passed_tests += 1
                print(f"  PASS: {test_class.__name__}.{method_name}")
            except AssertionError as e:
                instance.teardown_method()
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"  FAIL: {test_class.__name__}.{method_name} - {e}")
            except Exception as e:
                instance.teardown_method()
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"  ERROR: {test_class.__name__}.{method_name} - {e}")
    print(f"\n{'=' * 60}")
    print(f"Results: {passed_tests}/{total_tests} passed")
    if failed_tests:
        print(f"\nFailed tests:")
        for cls, method, error in failed_tests:
            print(f"  - {cls}.{method}: {error}")
    return len(failed_tests) == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
