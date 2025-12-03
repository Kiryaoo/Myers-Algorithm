import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from algorithms.utils import OpType, EditAction
from formatters.base import (
    FormatterConfig,
    FormatterFactory,
    ColorScheme,
    OutputWriter,
    OutputTarget,
    DiffHunk,
    HunkGenerator,
    SimpleFormatter,
    BaseFormatter
)
from formatters.unified import (
    UnifiedFormatter,
    UnifiedDiffHeader,
    UnifiedDiffStats,
    UnifiedLineFormatter,
    HunkHeader,
    ContextDiffFormatter,
    NormalDiffFormatter,
    EDDiffFormatter,
    RCSDiffFormatter
)
from formatters.side_by_side import (
    SideBySideFormatter,
    SideBySideRow,
    SideBySideGenerator,
    ColumnConfig,
    TextTruncator,
    LineNumberFormatter,
    GutterFormatter,
    CompactSideBySideFormatter,
    WordDiffFormatter,
    InlineDiffFormatter
)
from formatters.html import (
    HTMLFormatter,
    HTMLDocument,
    HTMLElement,
    DiffStylesheet,
    CSSStylesheet,
    DiffTableBuilder,
    SideBySideHTMLFormatter,
    GitHubStyleFormatter,
    JSONFormatter,
    XMLFormatter
)


class TestFormatterConfig(unittest.TestCase):
    def test_default_config(self):
        config = FormatterConfig()
        self.assertEqual(config.context_lines, 3)
        self.assertEqual(config.width, 130)
        self.assertTrue(config.use_color)
        self.assertEqual(config.tab_size, 4)
        self.assertTrue(config.show_line_numbers)
        self.assertFalse(config.ignore_whitespace)
        self.assertFalse(config.ignore_case)
        self.assertEqual(config.encoding, "utf-8")

    def test_custom_config(self):
        config = FormatterConfig(
            context_lines=5,
            width=80,
            use_color=False,
            tab_size=2
        )
        self.assertEqual(config.context_lines, 5)
        self.assertEqual(config.width, 80)
        self.assertFalse(config.use_color)
        self.assertEqual(config.tab_size, 2)

    def test_config_copy(self):
        config = FormatterConfig(context_lines=10, width=100)
        copy = config.copy()
        self.assertEqual(copy.context_lines, 10)
        self.assertEqual(copy.width, 100)
        copy.context_lines = 5
        self.assertEqual(config.context_lines, 10)

    def test_with_context_lines(self):
        config = FormatterConfig()
        new_config = config.with_context_lines(7)
        self.assertEqual(new_config.context_lines, 7)
        self.assertEqual(config.context_lines, 3)

    def test_with_width(self):
        config = FormatterConfig()
        new_config = config.with_width(200)
        self.assertEqual(new_config.width, 200)
        self.assertEqual(config.width, 130)

    def test_with_color(self):
        config = FormatterConfig(use_color=True)
        new_config = config.with_color(False)
        self.assertFalse(new_config.use_color)
        self.assertTrue(config.use_color)


class TestColorScheme(unittest.TestCase):
    def test_default_colors(self):
        scheme = ColorScheme()
        self.assertEqual(scheme.reset, '\033[0m')
        self.assertEqual(scheme.red, '\033[31m')
        self.assertEqual(scheme.green, '\033[32m')
        self.assertEqual(scheme.cyan, '\033[36m')

    def test_disable_colors(self):
        scheme = ColorScheme()
        scheme.disable_colors()
        self.assertEqual(scheme.reset, '')
        self.assertEqual(scheme.red, '')
        self.assertEqual(scheme.green, '')

    def test_no_color_factory(self):
        scheme = ColorScheme.no_color()
        self.assertEqual(scheme.reset, '')
        self.assertEqual(scheme.bold, '')
        self.assertEqual(scheme.red, '')


class TestOutputWriter(unittest.TestCase):
    def test_string_output(self):
        writer = OutputWriter(OutputTarget.STRING)
        writer.write("hello")
        writer.write(" world")
        self.assertEqual(writer.get_output(), "hello world")

    def test_writeln(self):
        writer = OutputWriter(OutputTarget.STRING)
        writer.writeln("line1")
        writer.writeln("line2")
        self.assertEqual(writer.get_output(), "line1\nline2\n")

    def test_empty_writeln(self):
        writer = OutputWriter(OutputTarget.STRING)
        writer.writeln()
        self.assertEqual(writer.get_output(), "\n")


class TestDiffHunk(unittest.TestCase):
    def test_hunk_creation(self):
        actions = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.DELETE, "line2"),
            EditAction(OpType.INSERT, "line3")
        ]
        hunk = DiffHunk(0, 2, 0, 2, actions)
        self.assertEqual(hunk.orig_start, 0)
        self.assertEqual(hunk.orig_count, 2)
        self.assertEqual(hunk.mod_start, 0)
        self.assertEqual(hunk.mod_count, 2)
        self.assertEqual(len(hunk.actions), 3)

    def test_hunk_is_empty(self):
        hunk = DiffHunk(0, 0, 0, 0, [])
        self.assertTrue(hunk.is_empty())
        
    def test_hunk_not_empty(self):
        actions = [EditAction(OpType.EQUAL, "line")]
        hunk = DiffHunk(0, 1, 0, 1, actions)
        self.assertFalse(hunk.is_empty())

    def test_hunk_has_changes(self):
        actions = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.DELETE, "line2")
        ]
        hunk = DiffHunk(0, 2, 0, 1, actions)
        self.assertTrue(hunk.has_changes())

    def test_hunk_no_changes(self):
        actions = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2")
        ]
        hunk = DiffHunk(0, 2, 0, 2, actions)
        self.assertFalse(hunk.has_changes())

    def test_hunk_repr(self):
        hunk = DiffHunk(5, 10, 7, 12, [])
        repr_str = repr(hunk)
        self.assertIn("-5,10", repr_str)
        self.assertIn("+7,12", repr_str)


class TestHunkGenerator(unittest.TestCase):
    def test_empty_script(self):
        generator = HunkGenerator()
        hunks = generator.generate([])
        self.assertEqual(len(hunks), 0)

    def test_no_changes(self):
        generator = HunkGenerator()
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2")
        ]
        hunks = generator.generate(script)
        self.assertEqual(len(hunks), 0)

    def test_single_change(self):
        generator = HunkGenerator(context_lines=1)
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2"),
            EditAction(OpType.DELETE, "line3"),
            EditAction(OpType.EQUAL, "line4"),
            EditAction(OpType.EQUAL, "line5")
        ]
        hunks = generator.generate(script)
        self.assertEqual(len(hunks), 1)

    def test_merged_hunks(self):
        generator = HunkGenerator(context_lines=2)
        script = [
            EditAction(OpType.DELETE, "line1"),
            EditAction(OpType.EQUAL, "line2"),
            EditAction(OpType.EQUAL, "line3"),
            EditAction(OpType.INSERT, "line4")
        ]
        hunks = generator.generate(script)
        self.assertEqual(len(hunks), 1)

    def test_separate_hunks(self):
        generator = HunkGenerator(context_lines=1)
        script = [
            EditAction(OpType.DELETE, "line1"),
            EditAction(OpType.EQUAL, "line2"),
            EditAction(OpType.EQUAL, "line3"),
            EditAction(OpType.EQUAL, "line4"),
            EditAction(OpType.EQUAL, "line5"),
            EditAction(OpType.EQUAL, "line6"),
            EditAction(OpType.INSERT, "line7")
        ]
        hunks = generator.generate(script)
        self.assertEqual(len(hunks), 2)


class TestSimpleFormatter(unittest.TestCase):
    def test_format_equal(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [EditAction(OpType.EQUAL, "same line")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("same line", output)

    def test_format_delete(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [EditAction(OpType.DELETE, "deleted")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("-deleted", output)

    def test_format_insert(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [EditAction(OpType.INSERT, "inserted")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("+inserted", output)

    def test_format_mixed(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "context"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("context", output)
        self.assertIn("-old", output)
        self.assertIn("+new", output)


class TestFormatterFactory(unittest.TestCase):
    def test_create_simple(self):
        formatter = FormatterFactory.create("simple")
        self.assertIsInstance(formatter, SimpleFormatter)

    def test_create_unified(self):
        formatter = FormatterFactory.create("unified")
        self.assertIsInstance(formatter, UnifiedFormatter)

    def test_create_side_by_side(self):
        formatter = FormatterFactory.create("side-by-side")
        self.assertIsInstance(formatter, SideBySideFormatter)

    def test_create_html(self):
        formatter = FormatterFactory.create("html")
        self.assertIsInstance(formatter, HTMLFormatter)

    def test_create_with_config(self):
        config = FormatterConfig(context_lines=5)
        formatter = FormatterFactory.create("unified", config)
        self.assertEqual(formatter.config.context_lines, 5)

    def test_unknown_formatter(self):
        with self.assertRaises(ValueError):
            FormatterFactory.create("unknown_format")

    def test_available_formatters(self):
        available = FormatterFactory.available()
        self.assertIn("simple", available)
        self.assertIn("unified", available)
        self.assertIn("html", available)


class TestUnifiedDiffHeader(unittest.TestCase):
    def test_basic_header(self):
        header = UnifiedDiffHeader("file1.txt", "file2.txt")
        self.assertEqual(header.format_old_header(), "--- file1.txt")
        self.assertEqual(header.format_new_header(), "+++ file2.txt")

    def test_header_with_timestamp(self):
        header = UnifiedDiffHeader("file1.txt", "file2.txt", "2024-01-01", "2024-01-02")
        self.assertIn("2024-01-01", header.format_old_header())
        self.assertIn("2024-01-02", header.format_new_header())


class TestUnifiedDiffStats(unittest.TestCase):
    def test_empty_stats(self):
        stats = UnifiedDiffStats()
        self.assertEqual(stats.insertions, 0)
        self.assertEqual(stats.deletions, 0)
        self.assertEqual(stats.unchanged, 0)

    def test_add_action(self):
        stats = UnifiedDiffStats()
        stats.add_action(EditAction(OpType.INSERT, "line"))
        stats.add_action(EditAction(OpType.DELETE, "line"))
        stats.add_action(EditAction(OpType.EQUAL, "line"))
        self.assertEqual(stats.insertions, 1)
        self.assertEqual(stats.deletions, 1)
        self.assertEqual(stats.unchanged, 1)

    def test_add_script(self):
        stats = UnifiedDiffStats()
        script = [
            EditAction(OpType.INSERT, "a"),
            EditAction(OpType.INSERT, "b"),
            EditAction(OpType.DELETE, "c")
        ]
        stats.add_script(script)
        self.assertEqual(stats.insertions, 2)
        self.assertEqual(stats.deletions, 1)

    def test_total_changes(self):
        stats = UnifiedDiffStats()
        stats.insertions = 5
        stats.deletions = 3
        self.assertEqual(stats.total_changes(), 8)

    def test_format_summary(self):
        stats = UnifiedDiffStats()
        stats.insertions = 10
        stats.deletions = 5
        summary = stats.format_summary()
        self.assertIn("+10", summary)
        self.assertIn("-5", summary)

    def test_format_summary_no_changes(self):
        stats = UnifiedDiffStats()
        summary = stats.format_summary()
        self.assertEqual(summary, "no changes")


class TestUnifiedLineFormatter(unittest.TestCase):
    def test_format_context(self):
        colors = ColorScheme.no_color()
        formatter = UnifiedLineFormatter(colors, use_color=False)
        self.assertEqual(formatter.format_context("line"), " line")

    def test_format_deletion(self):
        colors = ColorScheme.no_color()
        formatter = UnifiedLineFormatter(colors, use_color=False)
        self.assertEqual(formatter.format_deletion("line"), "-line")

    def test_format_insertion(self):
        colors = ColorScheme.no_color()
        formatter = UnifiedLineFormatter(colors, use_color=False)
        self.assertEqual(formatter.format_insertion("line"), "+line")


class TestHunkHeader(unittest.TestCase):
    def test_basic_header(self):
        hunk = DiffHunk(0, 5, 0, 7, [])
        header = HunkHeader(hunk)
        result = header.format()
        self.assertIn("-1,5", result)
        self.assertIn("+1,7", result)
        self.assertIn("@@", result)

    def test_header_with_section(self):
        hunk = DiffHunk(10, 3, 12, 5, [])
        header = HunkHeader(hunk, "function_name")
        result = header.format()
        self.assertIn("function_name", result)


class TestUnifiedFormatter(unittest.TestCase):
    def test_no_changes(self):
        config = FormatterConfig(use_color=False)
        formatter = UnifiedFormatter(config)
        script = [EditAction(OpType.EQUAL, "same")]
        output = formatter.format(script, "file1", "file2")
        self.assertEqual(output, "")

    def test_with_changes(self):
        config = FormatterConfig(use_color=False)
        formatter = UnifiedFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "context"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1.txt", "file2.txt")
        self.assertIn("--- file1.txt", output)
        self.assertIn("+++ file2.txt", output)
        self.assertIn("@@", output)
        self.assertIn("-old", output)
        self.assertIn("+new", output)


class TestContextDiffFormatter(unittest.TestCase):
    def test_no_changes(self):
        config = FormatterConfig(use_color=False)
        formatter = ContextDiffFormatter(config)
        script = [EditAction(OpType.EQUAL, "same")]
        output = formatter.format(script, "file1", "file2")
        self.assertEqual(output, "")

    def test_with_changes(self):
        config = FormatterConfig(use_color=False)
        formatter = ContextDiffFormatter(config)
        script = [
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("***", output)
        self.assertIn("---", output)


class TestNormalDiffFormatter(unittest.TestCase):
    def test_delete(self):
        config = FormatterConfig(use_color=False)
        formatter = NormalDiffFormatter(config)
        script = [EditAction(OpType.DELETE, "deleted")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("d", output)
        self.assertIn("< deleted", output)

    def test_insert(self):
        config = FormatterConfig(use_color=False)
        formatter = NormalDiffFormatter(config)
        script = [EditAction(OpType.INSERT, "inserted")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("a", output)
        self.assertIn("> inserted", output)

    def test_change(self):
        config = FormatterConfig(use_color=False)
        formatter = NormalDiffFormatter(config)
        script = [
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("c", output)
        self.assertIn("< old", output)
        self.assertIn("> new", output)


class TestColumnConfig(unittest.TestCase):
    def test_default_config(self):
        config = ColumnConfig()
        self.assertEqual(config.total_width, 130)
        self.assertEqual(config.gutter_width, 3)
        self.assertEqual(config.line_num_width, 4)

    def test_custom_width(self):
        config = ColumnConfig(total_width=80)
        self.assertEqual(config.total_width, 80)
        self.assertGreater(config.content_width, 0)


class TestTextTruncator(unittest.TestCase):
    def test_no_truncation_needed(self):
        truncator = TextTruncator(20)
        self.assertEqual(truncator.truncate("short"), "short")

    def test_truncation(self):
        truncator = TextTruncator(10)
        result = truncator.truncate("this is a very long string")
        self.assertEqual(len(result), 10)
        self.assertTrue(result.endswith("..."))

    def test_pad(self):
        truncator = TextTruncator(10)
        result = truncator.pad("hi", 10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.startswith("hi"))

    def test_truncate_and_pad(self):
        truncator = TextTruncator(10)
        result = truncator.truncate_and_pad("hi")
        self.assertEqual(len(result), 10)


class TestLineNumberFormatter(unittest.TestCase):
    def test_format_number(self):
        formatter = LineNumberFormatter(width=4)
        self.assertEqual(formatter.format(1), "   1")
        self.assertEqual(formatter.format(100), " 100")
        self.assertEqual(formatter.format(9999), "9999")

    def test_format_none(self):
        formatter = LineNumberFormatter(width=4)
        self.assertEqual(formatter.format(None), "    ")

    def test_overflow(self):
        formatter = LineNumberFormatter(width=3)
        result = formatter.format(12345)
        self.assertEqual(len(result), 3)


class TestSideBySideRow(unittest.TestCase):
    def test_equal_row(self):
        row = SideBySideRow(1, "content", 1, "content", OpType.EQUAL)
        self.assertEqual(row.left_num, 1)
        self.assertEqual(row.right_num, 1)
        self.assertEqual(row.change_type, OpType.EQUAL)

    def test_delete_row(self):
        row = SideBySideRow(5, "deleted", None, "", OpType.DELETE)
        self.assertEqual(row.left_num, 5)
        self.assertIsNone(row.right_num)
        self.assertEqual(row.change_type, OpType.DELETE)


class TestSideBySideGenerator(unittest.TestCase):
    def test_equal_lines(self):
        generator = SideBySideGenerator()
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.EQUAL, "line2")
        ]
        rows = generator.generate(script)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].change_type, OpType.EQUAL)

    def test_delete_insert_pair(self):
        generator = SideBySideGenerator()
        script = [
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        rows = generator.generate(script)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].change_type, OpType.REPLACE)

    def test_delete_only(self):
        generator = SideBySideGenerator()
        script = [EditAction(OpType.DELETE, "deleted")]
        rows = generator.generate(script)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].change_type, OpType.DELETE)

    def test_insert_only(self):
        generator = SideBySideGenerator()
        script = [EditAction(OpType.INSERT, "inserted")]
        rows = generator.generate(script)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].change_type, OpType.INSERT)


class TestSideBySideFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False, width=80)
        formatter = SideBySideFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("file1", output)
        self.assertIn("file2", output)
        self.assertIn("=", output)


class TestCSSStylesheet(unittest.TestCase):
    def test_add_rule(self):
        css = CSSStylesheet()
        css.add_rule("body", {"color": "red", "margin": "0"})
        rendered = css.render()
        self.assertIn("body", rendered)
        self.assertIn("color: red", rendered)

    def test_multiple_rules(self):
        css = CSSStylesheet()
        css.add_rule(".class1", {"color": "blue"})
        css.add_rule(".class2", {"color": "green"})
        rendered = css.render()
        self.assertIn(".class1", rendered)
        self.assertIn(".class2", rendered)


class TestDiffStylesheet(unittest.TestCase):
    def test_has_default_styles(self):
        css = DiffStylesheet()
        rendered = css.render()
        self.assertIn("body", rendered)
        self.assertIn(".diff-container", rendered)
        self.assertIn(".delete", rendered)
        self.assertIn(".insert", rendered)


class TestHTMLElement(unittest.TestCase):
    def test_simple_element(self):
        elem = HTMLElement("div")
        self.assertIn("<div>", elem.render())
        self.assertIn("</div>", elem.render())

    def test_element_with_attrs(self):
        elem = HTMLElement("div", {"class": "container", "id": "main"})
        rendered = elem.render()
        self.assertIn('class="container"', rendered)
        self.assertIn('id="main"', rendered)

    def test_element_with_content(self):
        elem = HTMLElement("span", content="hello")
        rendered = elem.render()
        self.assertIn("hello", rendered)

    def test_add_child(self):
        parent = HTMLElement("div")
        child = parent.add_child(HTMLElement("span", content="child"))
        rendered = parent.render()
        self.assertIn("<span>", rendered)
        self.assertIn("child", rendered)


class TestHTMLDocument(unittest.TestCase):
    def test_basic_document(self):
        doc = HTMLDocument("Test Title")
        rendered = doc.render()
        self.assertIn("<!DOCTYPE html>", rendered)
        self.assertIn("<html>", rendered)
        self.assertIn("Test Title", rendered)
        self.assertIn("</html>", rendered)

    def test_add_content(self):
        doc = HTMLDocument()
        doc.add_content("<p>Hello</p>")
        rendered = doc.render()
        self.assertIn("<p>Hello</p>", rendered)


class TestDiffTableBuilder(unittest.TestCase):
    def test_add_equal_row(self):
        builder = DiffTableBuilder()
        builder.add_equal_row(1, 1, "content")
        rendered = builder.render()
        self.assertIn("class=\"equal\"", rendered)
        self.assertIn("content", rendered)

    def test_add_delete_row(self):
        builder = DiffTableBuilder()
        builder.add_delete_row(5, "deleted line")
        rendered = builder.render()
        self.assertIn("class=\"delete\"", rendered)
        self.assertIn("deleted line", rendered)
        self.assertEqual(builder.deletions, 1)

    def test_add_insert_row(self):
        builder = DiffTableBuilder()
        builder.add_insert_row(3, "inserted line")
        rendered = builder.render()
        self.assertIn("class=\"insert\"", rendered)
        self.assertIn("inserted line", rendered)
        self.assertEqual(builder.insertions, 1)

    def test_get_stats(self):
        builder = DiffTableBuilder()
        builder.add_delete_row(1, "del")
        builder.add_insert_row(1, "ins1")
        builder.add_insert_row(2, "ins2")
        stats = builder.get_stats()
        self.assertEqual(stats["deletions"], 1)
        self.assertEqual(stats["insertions"], 2)

    def test_html_escaping(self):
        builder = DiffTableBuilder()
        builder.add_equal_row(1, 1, "<script>alert('xss')</script>")
        rendered = builder.render()
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)


class TestHTMLFormatter(unittest.TestCase):
    def test_basic_format(self):
        config = FormatterConfig(use_color=False)
        formatter = HTMLFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1.txt", "file2.txt")
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertIn("class=\"delete\"", output)
        self.assertIn("class=\"insert\"", output)

    def test_stats_in_output(self):
        config = FormatterConfig(use_color=False)
        formatter = HTMLFormatter(config)
        script = [
            EditAction(OpType.INSERT, "new1"),
            EditAction(OpType.INSERT, "new2"),
            EditAction(OpType.DELETE, "old")
        ]
        output = formatter.format(script, "a", "b")
        self.assertIn("2 additions", output)
        self.assertIn("1 deletions", output)


class TestSideBySideHTMLFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = SideBySideHTMLFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same"),
            EditAction(OpType.DELETE, "left"),
            EditAction(OpType.INSERT, "right")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("file1", output)
        self.assertIn("file2", output)


class TestGitHubStyleFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = GitHubStyleFormatter(config)
        script = [
            EditAction(OpType.DELETE, "removed"),
            EditAction(OpType.INSERT, "added")
        ]
        output = formatter.format(script, "old.py", "new.py")
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("blob-code-deletion", output)
        self.assertIn("blob-code-addition", output)


class TestJSONFormatter(unittest.TestCase):
    def test_valid_json(self):
        import json
        config = FormatterConfig(use_color=False)
        formatter = JSONFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        data = json.loads(output)
        self.assertEqual(data["file1"], "file1")
        self.assertEqual(data["file2"], "file2")
        self.assertIn("changes", data)
        self.assertIn("stats", data)

    def test_stats(self):
        import json
        config = FormatterConfig(use_color=False)
        formatter = JSONFormatter(config)
        script = [
            EditAction(OpType.DELETE, "d1"),
            EditAction(OpType.DELETE, "d2"),
            EditAction(OpType.INSERT, "i1")
        ]
        output = formatter.format(script, "a", "b")
        data = json.loads(output)
        self.assertEqual(data["stats"]["deletions"], 2)
        self.assertEqual(data["stats"]["insertions"], 1)


class TestXMLFormatter(unittest.TestCase):
    def test_valid_xml_structure(self):
        config = FormatterConfig(use_color=False)
        formatter = XMLFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn('<?xml version="1.0"', output)
        self.assertIn("<diff>", output)
        self.assertIn("</diff>", output)
        self.assertIn("<file1>file1</file1>", output)
        self.assertIn("<equal", output)
        self.assertIn("<delete", output)
        self.assertIn("<insert", output)

    def test_xml_escaping(self):
        config = FormatterConfig(use_color=False)
        formatter = XMLFormatter(config)
        script = [EditAction(OpType.EQUAL, "<tag>&value</tag>")]
        output = formatter.format(script, "f1", "f2")
        self.assertIn("&lt;tag&gt;", output)
        self.assertIn("&amp;value", output)


class TestWordDiffFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = WordDiffFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "context"),
            EditAction(OpType.DELETE, "removed"),
            EditAction(OpType.INSERT, "added")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("context", output)
        self.assertIn("[-removed-]", output)
        self.assertIn("{+added+}", output)


class TestInlineDiffFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = InlineDiffFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "line1"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("--- file1", output)
        self.assertIn("+++ file2", output)
        self.assertIn("- old", output)
        self.assertIn("+ new", output)


class TestCompactSideBySideFormatter(unittest.TestCase):
    def test_identical_files(self):
        config = FormatterConfig(use_color=False)
        formatter = CompactSideBySideFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "same1"),
            EditAction(OpType.EQUAL, "same2")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("identical", output)

    def test_with_changes(self):
        config = FormatterConfig(use_color=False, width=80)
        formatter = CompactSideBySideFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "context"),
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("file1", output)
        self.assertIn("file2", output)


class TestEDDiffFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = EDDiffFormatter(config)
        script = [
            EditAction(OpType.DELETE, "old"),
            EditAction(OpType.INSERT, "new")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("c", output)
        self.assertIn(".", output)


class TestRCSDiffFormatter(unittest.TestCase):
    def test_format_output(self):
        config = FormatterConfig(use_color=False)
        formatter = RCSDiffFormatter(config)
        script = [
            EditAction(OpType.DELETE, "deleted"),
            EditAction(OpType.INSERT, "added")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("d", output)
        self.assertIn("a", output)


class TestGutterFormatter(unittest.TestCase):
    def test_format_equal(self):
        colors = ColorScheme.no_color()
        gutter = GutterFormatter(colors)
        self.assertEqual(gutter.format_equal(), " | ")

    def test_format_markers(self):
        colors = ColorScheme.no_color()
        gutter = GutterFormatter(colors)
        self.assertIn("<", gutter.format_delete())
        self.assertIn(">", gutter.format_insert())


class TestEdgeCases(unittest.TestCase):
    def test_empty_script(self):
        config = FormatterConfig(use_color=False)
        for name in ["simple", "unified", "html", "json", "xml"]:
            formatter = FormatterFactory.create(name, config)
            output = formatter.format([], "file1", "file2")
            self.assertIsInstance(output, str)

    def test_unicode_content(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [
            EditAction(OpType.EQUAL, "привіт"),
            EditAction(OpType.DELETE, "こんにちは"),
            EditAction(OpType.INSERT, "مرحبا")
        ]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("привіт", output)

    def test_special_characters(self):
        config = FormatterConfig(use_color=False)
        formatter = HTMLFormatter(config)
        script = [EditAction(OpType.EQUAL, "<>&\"'")]
        output = formatter.format(script, "file1", "file2")
        self.assertNotIn("<>&", output)

    def test_very_long_lines(self):
        config = FormatterConfig(use_color=False, width=80)
        formatter = SideBySideFormatter(config)
        long_line = "x" * 500
        script = [EditAction(OpType.EQUAL, long_line)]
        output = formatter.format(script, "file1", "file2")
        self.assertIsInstance(output, str)

    def test_multiline_values(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script = [EditAction(OpType.EQUAL, "line with\ttab")]
        output = formatter.format(script, "file1", "file2")
        self.assertIn("\t", output)


class TestFormatterIntegration(unittest.TestCase):
    def test_all_formatters_produce_output(self):
        config = FormatterConfig(use_color=False)
        script = [
            EditAction(OpType.EQUAL, "context1"),
            EditAction(OpType.DELETE, "old_line"),
            EditAction(OpType.INSERT, "new_line"),
            EditAction(OpType.EQUAL, "context2")
        ]
        for name in FormatterFactory.available():
            formatter = FormatterFactory.create(name, config)
            output = formatter.format(script, "test1.txt", "test2.txt")
            self.assertIsInstance(output, str, f"Formatter {name} failed")

    def test_has_changes_method(self):
        config = FormatterConfig(use_color=False)
        formatter = SimpleFormatter(config)
        script_with_changes = [EditAction(OpType.DELETE, "x")]
        script_without_changes = [EditAction(OpType.EQUAL, "x")]
        self.assertTrue(formatter.has_changes(script_with_changes))
        self.assertFalse(formatter.has_changes(script_without_changes))


if __name__ == '__main__':
    unittest.main(verbosity=2)
