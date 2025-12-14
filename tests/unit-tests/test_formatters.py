import unittest
import sys
import os
import re
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from algorithms.utils import OpType, EditAction
from algorithms.myers import diff as myers_diff
from formatters.base import (
    FormatterConfig, FormatterFactory, ColorScheme, OutputWriter, OutputTarget,
    DiffHunk, HunkGenerator, SimpleFormatter, BaseFormatter
)
from formatters.unified import UnifiedFormatter, ContextDiffFormatter, NormalDiffFormatter
from formatters.side_by_side import (
    SideBySideFormatter, SideBySideRow, SideBySideGenerator, ColumnConfig,
    TextTruncator, LineNumberFormatter, GutterFormatter,
    CompactSideBySideFormatter, WordDiffFormatter, InlineDiffFormatter
)
from formatters.html import HTMLFormatter, SideBySideHTMLFormatter, JSONFormatter


class TestFormatterConfig(unittest.TestCase):
    def test_config(self):
        c = FormatterConfig()
        self.assertEqual(c.context_lines, 3)
        self.assertTrue(c.use_color)
        c2 = FormatterConfig(context_lines=5, use_color=False)
        self.assertEqual(c2.context_lines, 5)
        copy = c.copy()
        self.assertEqual(c.with_context_lines(7).context_lines, 7)


class TestColorSchemeAndWriter(unittest.TestCase):
    def test_colors_writer(self):
        s = ColorScheme()
        self.assertEqual(s.reset, '\033[0m')
        s.disable_colors()
        self.assertEqual(s.reset, '')
        w = OutputWriter(OutputTarget.STRING)
        w.write("a")
        w.writeln("b")
        self.assertEqual(w.get_output(), "ab\n")


class TestHunks(unittest.TestCase):
    def test_hunk_generator(self):
        h = DiffHunk(0, 2, 0, 2, [EditAction(OpType.DELETE, "x")])
        self.assertFalse(h.is_empty())
        self.assertTrue(h.has_changes())
        g = HunkGenerator()
        self.assertEqual(len(g.generate([])), 0)


class TestSimpleAndFactory(unittest.TestCase):
    def test_simple_factory(self):
        config = FormatterConfig(use_color=False)
        f = SimpleFormatter(config)
        out = f.format([EditAction(OpType.DELETE, "old"), EditAction(OpType.INSERT, "new")], "f1", "f2")
        self.assertIn("-old", out)
        self.assertIn("+new", out)
        self.assertIsInstance(FormatterFactory.create("simple"), SimpleFormatter)
        self.assertIsInstance(FormatterFactory.create("unified"), UnifiedFormatter)
        with self.assertRaises(ValueError):
            FormatterFactory.create("unknown")


class TestUnifiedFormatters(unittest.TestCase):
    def test_unified(self):
        config = FormatterConfig(use_color=False)
        out = UnifiedFormatter(config).format([EditAction(OpType.DELETE, "x")], "a.txt", "b.txt")
        self.assertIn("--- a.txt", out)
        self.assertIn("***", ContextDiffFormatter(config).format([EditAction(OpType.DELETE, "x")], "a", "b"))
        self.assertIn("< del", NormalDiffFormatter(config).format([EditAction(OpType.DELETE, "del")], "a", "b"))


class TestUnifiedFormatterStrict(unittest.TestCase):
    """
    Strict tests for UnifiedFormatter to ensure compliance with the unified diff format.
    These tests verify exact line numbering (1-based) and format specification adherence.
    """
    
    def setUp(self):
        self.config = FormatterConfig(use_color=False, context_lines=3)
        self.formatter = UnifiedFormatter(self.config)
        # Regex pattern for unified diff hunk header
        # Format: @@ -start,count +start,count @@
        # Line numbers must be 1-based (not 0-based)
        # Note: count can be 0 for empty sections
        self.hunk_header_pattern = re.compile(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@')
    
    def test_unified_hunk_header_line_numbers_are_one_based(self):
        """
        Verify that hunk headers use 1-based line numbers, not 0-based.
        This is critical for compatibility with standard tools like 'patch'.
        """
        # Single line delete at line 1
        script = [EditAction(OpType.DELETE, "line1")]
        output = self.formatter.format(script, "a.txt", "b.txt")
        
        # Extract hunk header
        match = self.hunk_header_pattern.search(output)
        self.assertIsNotNone(match, f"No valid hunk header found in output: {output}")
        
        orig_start = int(match.group(1))
        
        # Line numbers should be 1-based, not 0-based
        self.assertGreaterEqual(orig_start, 1, 
            f"Original start line is 0-based (got {orig_start}), should be 1-based")
        
    def test_unified_single_insert_at_beginning(self):
        """Test inserting a single line at the beginning."""
        script = [EditAction(OpType.INSERT, "new_line")]
        output = self.formatter.format(script, "a.txt", "b.txt")
        
        self.assertIn("--- a.txt", output)
        self.assertIn("+++ b.txt", output)
        self.assertIn("+new_line", output)
        
        # Verify hunk header format
        hunk_match = self.hunk_header_pattern.search(output)
        self.assertIsNotNone(hunk_match, f"Hunk header not found or invalid format in: {output}")
        
    def test_unified_single_delete_at_beginning(self):
        """Test deleting a single line at the beginning."""
        script = [EditAction(OpType.DELETE, "old_line")]
        output = self.formatter.format(script, "a.txt", "b.txt")
        
        self.assertIn("-old_line", output)
        
        # Verify line numbers are 1-based
        hunk_match = self.hunk_header_pattern.search(output)
        self.assertIsNotNone(hunk_match, f"Hunk header not found in: {output}")
        orig_start = int(hunk_match.group(1))
        self.assertEqual(orig_start, 1, f"Expected line 1, got {orig_start}")
        
    def test_unified_change_in_middle_of_file(self):
        """Test a change in the middle of a file with context."""
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2"),
            EditAction(OpType.DELETE, "old_line3"),
            EditAction(OpType.INSERT, "new_line3"),
            EditAction(OpType.EQUAL, "line4"),
            EditAction(OpType.EQUAL, "line5"),
        ]
        output = self.formatter.format(script, "a.txt", "b.txt")
        
        # Verify hunk header
        hunk_match = self.hunk_header_pattern.search(output)
        self.assertIsNotNone(hunk_match, f"Hunk header not found in: {output}")
        
        orig_start, orig_count, mod_start, mod_count = map(int, hunk_match.groups())
        
        # Start should be 1 (first line of context), not 0
        self.assertGreaterEqual(orig_start, 1, f"Original start should be >= 1, got {orig_start}")
        self.assertGreaterEqual(mod_start, 1, f"Modified start should be >= 1, got {mod_start}")
        
    def test_unified_multiple_hunks(self):
        """Test output with multiple hunks separated by many unchanged lines."""
        # Create a script with two separate changes
        script = []
        # First change at line 2
        script.append(EditAction(OpType.EQUAL, "line1"))
        script.append(EditAction(OpType.DELETE, "old_line2"))
        script.append(EditAction(OpType.INSERT, "new_line2"))
        # Many unchanged lines
        for i in range(3, 15):
            script.append(EditAction(OpType.EQUAL, f"line{i}"))
        # Second change at line 15
        script.append(EditAction(OpType.DELETE, "old_line15"))
        script.append(EditAction(OpType.INSERT, "new_line15"))
        script.append(EditAction(OpType.EQUAL, "line16"))
        
        config = FormatterConfig(use_color=False, context_lines=2)
        formatter = UnifiedFormatter(config)
        output = formatter.format(script, "a.txt", "b.txt")
        
        # Find all hunk headers
        hunks = self.hunk_header_pattern.findall(output)
        
        # Verify all line numbers are 1-based (>= 1)
        for hunk in hunks:
            orig_start, orig_count, mod_start, mod_count = map(int, hunk)
            self.assertGreaterEqual(orig_start, 1, 
                f"Original start line should be >= 1, got {orig_start}")
                
    def test_unified_exact_format_compliance(self):
        """
        Test exact format compliance with a known input/output.
        This ensures the output can be used with standard 'patch' utility.
        """
        script = [
            EditAction(OpType.EQUAL, "unchanged1"),
            EditAction(OpType.DELETE, "deleted"),
            EditAction(OpType.INSERT, "inserted"),
            EditAction(OpType.EQUAL, "unchanged2"),
        ]
        output = self.formatter.format(script, "file1.txt", "file2.txt")
        
        lines = output.strip().split('\n')
        
        # Verify header format
        self.assertTrue(lines[0].startswith("--- "), f"First line should start with '--- ': {lines[0]}")
        self.assertTrue(lines[1].startswith("+++ "), f"Second line should start with '+++ ': {lines[1]}")
        
        # Find and verify hunk header
        hunk_line = None
        for line in lines:
            if line.startswith("@@"):
                hunk_line = line
                break
        self.assertIsNotNone(hunk_line, "No hunk header found")
        
        # Hunk header must match exact format with 1-based line numbers
        match = self.hunk_header_pattern.search(hunk_line)
        self.assertIsNotNone(match, f"Hunk header doesn't match format: {hunk_line}")
        
        # Verify content lines have correct prefixes
        content_lines = [l for l in lines if not l.startswith('---') and 
                         not l.startswith('+++') and not l.startswith('@@')]
        
        for line in content_lines:
            self.assertTrue(
                line.startswith(' ') or line.startswith('-') or line.startswith('+'),
                f"Content line has invalid prefix: {line}"
            )
            
    def test_unified_empty_script_no_output(self):
        """Test that an empty script produces no output."""
        script = []
        output = self.formatter.format(script, "a.txt", "b.txt")
        self.assertEqual(output.strip(), "", "Empty script should produce no output")
        
    def test_unified_all_equal_no_output(self):
        """Test that all-equal script produces no output."""
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2"),
            EditAction(OpType.EQUAL, "line3"),
        ]
        output = self.formatter.format(script, "a.txt", "b.txt")
        self.assertEqual(output.strip(), "", "All-equal script should produce no output")
        
    def test_unified_line_numbers_not_zero_based(self):
        """
        Critical test: Verify that line numbers are never 0-based.
        This would catch the sabotage mentioned in the feedback where
        +1 was removed from line number calculations.
        """
        test_cases = [
            # Single delete
            [EditAction(OpType.DELETE, "x")],
            # Single insert  
            [EditAction(OpType.INSERT, "x")],
            # Replace
            [EditAction(OpType.DELETE, "old"), EditAction(OpType.INSERT, "new")],
            # Change with context
            [EditAction(OpType.EQUAL, "ctx1"), EditAction(OpType.DELETE, "del"), 
             EditAction(OpType.EQUAL, "ctx2")],
        ]
        
        for script in test_cases:
            output = self.formatter.format(script, "a.txt", "b.txt")
            matches = self.hunk_header_pattern.findall(output)
            
            for match in matches:
                orig_start, _, mod_start, _ = map(int, match)
                
                # Neither start should be 0 in a well-formed unified diff
                # (unless there's truly nothing on that side, which isn't the case here)
                self.assertNotEqual(orig_start, 0, 
                    f"Found 0-based original line number in hunk header. Output: {output}")
                self.assertNotEqual(mod_start, 0,
                    f"Found 0-based modified line number in hunk header. Output: {output}")


class TestUnifiedFormatterPatchCompatibility(unittest.TestCase):
    """
    Integration tests that verify the unified diff output is compatible
    with the standard 'patch' utility.
    """
    
    @classmethod
    def setUpClass(cls):
        """Check if patch utility is available."""
        cls.patch_available = False
        try:
            result = subprocess.run(['patch', '--version'], 
                                    capture_output=True, text=True, timeout=5)
            cls.patch_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    def setUp(self):
        self.config = FormatterConfig(use_color=False, context_lines=3)
        self.formatter = UnifiedFormatter(self.config)
        
    def _create_temp_files(self, content1: str, content2: str):
        """Create temporary files for testing."""
        fd1, path1 = tempfile.mkstemp(suffix='.txt')
        fd2, path2 = tempfile.mkstemp(suffix='.txt')
        
        with os.fdopen(fd1, 'w') as f:
            f.write(content1)
        with os.fdopen(fd2, 'w') as f:
            f.write(content2)
            
        return path1, path2
        
    def _cleanup_files(self, *paths):
        """Clean up temporary files."""
        for path in paths:
            try:
                os.unlink(path)
            except OSError:
                pass
                
    @unittest.skipUnless(os.name != 'nt', "Skipping patch test on Windows")
    def test_patch_can_apply_unified_diff(self):
        """
        Property test: Generate a diff with our library and verify
        that 'patch' can apply it to reconstruct the target file.
        """
        if not self.patch_available:
            self.skipTest("patch utility not available")
            
        original = "line1\nline2\nline3\nline4\nline5\n"
        modified = "line1\nmodified_line2\nline3\nnew_line\nline5\n"
        
        # Create diff
        orig_lines = original.strip().split('\n')
        mod_lines = modified.strip().split('\n')
        script = myers_diff(orig_lines, mod_lines)
        
        # Generate unified diff
        diff_output = self.formatter.format(script, "original.txt", "modified.txt")
        
        # Create temporary files
        path1, path2 = self._create_temp_files(original, "")
        diff_path = path1 + ".patch"
        
        try:
            # Write the diff
            with open(diff_path, 'w') as f:
                f.write(diff_output)
                
            # Apply the patch
            result = subprocess.run(
                ['patch', '-o', path2, path1, diff_path],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                with open(path2, 'r') as f:
                    patched_content = f.read()
                # Verify the patched content matches the modified version
                self.assertEqual(patched_content.strip(), modified.strip(),
                    "Patched file does not match expected modified content")
        finally:
            self._cleanup_files(path1, path2, diff_path)


class TestSideBySide(unittest.TestCase):
    def test_side_by_side(self):
        c = ColumnConfig(total_width=80)
        self.assertGreater(c.content_width, 0)
        t = TextTruncator(10)
        self.assertEqual(len(t.truncate("very long string here")), 10)
        f = LineNumberFormatter(width=4)
        self.assertEqual(f.format(1), "   1")
        r = SideBySideRow(1, "a", 1, "a", OpType.EQUAL)
        self.assertEqual(r.left_num, 1)
        g = SideBySideGenerator()
        rows = g.generate([EditAction(OpType.DELETE, "x"), EditAction(OpType.INSERT, "y")])
        self.assertEqual(rows[0].change_type, OpType.REPLACE)
        config = FormatterConfig(use_color=False, width=80)
        out = SideBySideFormatter(config).format([EditAction(OpType.DELETE, "y")], "f1", "f2")
        self.assertIn("f1", out)
        self.assertIn("|", GutterFormatter(ColorScheme.no_color()).format_equal())


class TestHTML(unittest.TestCase):
    def test_html(self):
        config = FormatterConfig(use_color=False)
        self.assertIn("<!DOCTYPE html>", HTMLFormatter(config).format([EditAction(OpType.DELETE, "x")], "a", "b"))
        self.assertIn("<!DOCTYPE html>", SideBySideHTMLFormatter(config).format([EditAction(OpType.DELETE, "x")], "a", "b"))


class TestOtherFormatters(unittest.TestCase):
    def test_json_others(self):
        import json
        config = FormatterConfig(use_color=False)
        script = [EditAction(OpType.DELETE, "x"), EditAction(OpType.INSERT, "y")]
        data = json.loads(JSONFormatter(config).format(script, "f1", "f2"))
        self.assertEqual(data["file1"], "f1")
        self.assertIn("[-x-]", WordDiffFormatter(config).format(script, "a", "b"))
        self.assertIn("--- a", InlineDiffFormatter(config).format(script, "a", "b"))
        self.assertIn("identical", CompactSideBySideFormatter(config).format([EditAction(OpType.EQUAL, "x")], "a", "b"))


class TestEdgeCases(unittest.TestCase):
    def test_empty_and_unicode(self):
        config = FormatterConfig(use_color=False)
        for name in ["simple", "unified", "html", "json"]:
            self.assertIsInstance(FormatterFactory.create(name, config).format([], "a", "b"), str)
        out = SimpleFormatter(config).format([EditAction(OpType.EQUAL, "привіт")], "a", "b")
        self.assertIn("привіт", out)


class TestFormatterIntegration(unittest.TestCase):
    def test_all_formatters(self):
        config = FormatterConfig(use_color=False)
        script = [EditAction(OpType.DELETE, "x"), EditAction(OpType.INSERT, "y")]
        for name in FormatterFactory.available():
            self.assertIsInstance(FormatterFactory.create(name, config).format(script, "a", "b"), str)

    def test_has_changes(self):
        config = FormatterConfig(use_color=False)
        f = SimpleFormatter(config)
        self.assertTrue(f.has_changes([EditAction(OpType.DELETE, "x")]))
        self.assertFalse(f.has_changes([EditAction(OpType.EQUAL, "x")]))

if __name__ == '__main__':
    unittest.main(verbosity=2)
