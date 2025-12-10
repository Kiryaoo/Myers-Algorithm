import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from algorithms.utils import OpType, EditAction
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
