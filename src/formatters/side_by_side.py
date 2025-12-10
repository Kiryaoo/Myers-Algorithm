from typing import List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.utils import OpType, EditAction
from formatters.base import BaseFormatter, FormatterConfig, FormatterFactory


class ColumnConfig:
    def __init__(self, total_width: int = 130, gutter_width: int = 3, line_num_width: int = 4):
        self.total_width = total_width
        self.gutter_width = gutter_width
        self.line_num_width = line_num_width
        self._calculate_content_width()
        
    def _calculate_content_width(self):
        available = self.total_width - self.gutter_width - (2 * self.line_num_width) - 4
        self.content_width = available // 2
        
    def get_left_width(self) -> int:
        return self.line_num_width + 1 + self.content_width
        
    def get_right_width(self) -> int:
        return self.line_num_width + 1 + self.content_width


class TextTruncator:
    def __init__(self, max_width: int, ellipsis: str = "..."):
        self.max_width = max_width
        self.ellipsis = ellipsis
        
    def truncate(self, text: str) -> str:
        if len(text) <= self.max_width:
            return text
        if self.max_width <= len(self.ellipsis):
            return text[:self.max_width]
        return text[:self.max_width - len(self.ellipsis)] + self.ellipsis
        
    def pad(self, text: str, width: Optional[int] = None) -> str:
        target_width = width or self.max_width
        if len(text) >= target_width:
            return text[:target_width]
        return text + " " * (target_width - len(text))
        
    def truncate_and_pad(self, text: str) -> str:
        truncated = self.truncate(text)
        return self.pad(truncated)


class LineNumberFormatter:
    def __init__(self, width: int = 4, padding_char: str = " "):
        self.width = width
        self.padding_char = padding_char
        
    def format(self, line_num: Optional[int]) -> str:
        if line_num is None:
            return self.padding_char * self.width
        num_str = str(line_num)
        if len(num_str) >= self.width:
            return num_str[:self.width]
        return self.padding_char * (self.width - len(num_str)) + num_str


class GutterFormatter:
    def __init__(self, colors, width: int = 3):
        self.colors = colors
        self.width = width
        self.equal_marker = " | "
        self.change_marker = " < "
        self.delete_marker = " < "
        self.insert_marker = " > "
        
    def format_equal(self) -> str:
        return self.equal_marker
        
    def format_change(self) -> str:
        return f"{self.colors.yellow}{self.change_marker}{self.colors.reset}"
        
    def format_delete(self) -> str:
        return f"{self.colors.red}{self.delete_marker}{self.colors.reset}"
        
    def format_insert(self) -> str:
        return f"{self.colors.green}{self.insert_marker}{self.colors.reset}"


class SideBySideRow:
    def __init__(
        self,
        left_num: Optional[int],
        left_content: str,
        right_num: Optional[int],
        right_content: str,
        change_type: OpType
    ):
        self.left_num = left_num
        self.left_content = left_content
        self.right_num = right_num
        self.right_content = right_content
        self.change_type = change_type


class SideBySideGenerator:
    def __init__(self):
        self.rows: List[SideBySideRow] = []
        
    def generate(self, script: List[EditAction]) -> List[SideBySideRow]:
        self.rows = []
        left_num = 1
        right_num = 1
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                row = SideBySideRow(
                    left_num=left_num,
                    left_content=str(action.value),
                    right_num=right_num,
                    right_content=str(action.value),
                    change_type=OpType.EQUAL
                )
                self.rows.append(row)
                left_num += 1
                right_num += 1
                i += 1
            elif action.op == OpType.DELETE:
                if i + 1 < len(script) and script[i + 1].op == OpType.INSERT:
                    row = SideBySideRow(
                        left_num=left_num,
                        left_content=str(action.value),
                        right_num=right_num,
                        right_content=str(script[i + 1].value),
                        change_type=OpType.REPLACE
                    )
                    self.rows.append(row)
                    left_num += 1
                    right_num += 1
                    i += 2
                else:
                    row = SideBySideRow(
                        left_num=left_num,
                        left_content=str(action.value),
                        right_num=None,
                        right_content="",
                        change_type=OpType.DELETE
                    )
                    self.rows.append(row)
                    left_num += 1
                    i += 1
            elif action.op == OpType.INSERT:
                row = SideBySideRow(
                    left_num=None,
                    left_content="",
                    right_num=right_num,
                    right_content=str(action.value),
                    change_type=OpType.INSERT
                )
                self.rows.append(row)
                right_num += 1
                i += 1
            else:
                i += 1
        return self.rows


class SideBySideRowFormatter:
    def __init__(self, config: ColumnConfig, colors, use_color: bool = True):
        self.config = config
        self.colors = colors
        self.use_color = use_color
        self.truncator = TextTruncator(config.content_width)
        self.line_num_fmt = LineNumberFormatter(config.line_num_width)
        self.gutter_fmt = GutterFormatter(colors, config.gutter_width)
        
    def format_row(self, row: SideBySideRow) -> str:
        left_num = self.line_num_fmt.format(row.left_num)
        left_content = self.truncator.truncate_and_pad(row.left_content)
        right_num = self.line_num_fmt.format(row.right_num)
        right_content = self.truncator.truncate(row.right_content)
        if row.change_type == OpType.EQUAL:
            gutter = self.gutter_fmt.format_equal()
            return f"{left_num} {left_content}{gutter}{right_num} {right_content}"
        elif row.change_type == OpType.DELETE:
            gutter = self.gutter_fmt.format_delete()
            if self.use_color:
                return f"{self.colors.red}{left_num} {left_content}{self.colors.reset}{gutter}{right_num} {right_content}"
            return f"{left_num} {left_content}{gutter}{right_num} {right_content}"
        elif row.change_type == OpType.INSERT:
            gutter = self.gutter_fmt.format_insert()
            if self.use_color:
                return f"{left_num} {left_content}{gutter}{self.colors.green}{right_num} {right_content}{self.colors.reset}"
            return f"{left_num} {left_content}{gutter}{right_num} {right_content}"
        elif row.change_type == OpType.REPLACE:
            gutter = self.gutter_fmt.format_change()
            if self.use_color:
                return f"{self.colors.red}{left_num} {left_content}{self.colors.reset}{gutter}{self.colors.green}{right_num} {right_content}{self.colors.reset}"
            return f"{left_num} {left_content}{gutter}{right_num} {right_content}"
        return f"{left_num} {left_content} | {right_num} {right_content}"


class SideBySideHeader:
    def __init__(self, config: ColumnConfig, colors, file1: str, file2: str):
        self.config = config
        self.colors = colors
        self.file1 = file1
        self.file2 = file2
        self.truncator = TextTruncator(config.content_width + config.line_num_width + 1)
        
    def format_separator(self) -> str:
        return "=" * self.config.total_width
        
    def format_filenames(self) -> str:
        left = self.truncator.truncate_and_pad(self.file1)
        right = self.truncator.truncate(self.file2)
        return f"{left} | {right}"
        
    def format_header_lines(self) -> List[str]:
        return [
            self.format_separator(),
            self.format_filenames(),
            self.format_separator()
        ]


class SideBySideFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.column_config = ColumnConfig(self.config.width)
        self.generator = SideBySideGenerator()
        self.row_formatter = SideBySideRowFormatter(
            self.column_config,
            self.colors,
            self.config.use_color
        )
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        header = SideBySideHeader(self.column_config, self.colors, file1, file2)
        for line in header.format_header_lines():
            self._writeln(line)
        rows = self.generator.generate(script)
        for row in rows:
            line = self.row_formatter.format_row(row)
            self._writeln(line)


class CompactSideBySideFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.column_config = ColumnConfig(self.config.width)
        self.generator = SideBySideGenerator()
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        rows = self.generator.generate(script)
        changed_rows = [r for r in rows if r.change_type != OpType.EQUAL]
        if not changed_rows:
            self._writeln("Files are identical")
            return
        col_width = (self.config.width - 7) // 2
        truncator = TextTruncator(col_width)
        self._writeln(f"{'=' * self.config.width}")
        left_header = truncator.truncate_and_pad(file1)
        right_header = truncator.truncate(file2)
        self._writeln(f"{left_header}   |   {right_header}")
        self._writeln(f"{'=' * self.config.width}")
        context_before = self.config.context_lines
        context_after = self.config.context_lines
        all_indices = set()
        for i, row in enumerate(rows):
            if row.change_type != OpType.EQUAL:
                for j in range(max(0, i - context_before), min(len(rows), i + context_after + 1)):
                    all_indices.add(j)
        sorted_indices = sorted(all_indices)
        prev_idx = -2
        for idx in sorted_indices:
            if idx > prev_idx + 1:
                if prev_idx >= 0:
                    self._writeln(f"{'-' * self.config.width}")
            row = rows[idx]
            left = truncator.truncate_and_pad(row.left_content)
            right = truncator.truncate(row.right_content)
            if row.change_type == OpType.EQUAL:
                self._writeln(f"{left}   |   {right}")
            elif row.change_type == OpType.DELETE:
                self._writeln(f"{self.colors.red}{left}{self.colors.reset}   <   {right}")
            elif row.change_type == OpType.INSERT:
                self._writeln(f"{left}   >   {self.colors.green}{right}{self.colors.reset}")
            elif row.change_type == OpType.REPLACE:
                self._writeln(f"{self.colors.red}{left}{self.colors.reset}   |   {self.colors.green}{right}{self.colors.reset}")
            prev_idx = idx


class WordDiffFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.column_config = ColumnConfig(self.config.width)
        self.generator = SideBySideGenerator()
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        self._writeln(f"diff {file1} {file2}")
        rows = self.generator.generate(script)
        for row in rows:
            if row.change_type == OpType.EQUAL:
                self._writeln(f" {row.left_content}")
            elif row.change_type == OpType.DELETE:
                self._writeln(f"{self.colors.red}[-{row.left_content}-]{self.colors.reset}")
            elif row.change_type == OpType.INSERT:
                self._writeln(f"{self.colors.green}{{+{row.right_content}+}}{self.colors.reset}")
            elif row.change_type == OpType.REPLACE:
                self._writeln(f"{self.colors.red}[-{row.left_content}-]{self.colors.reset}{self.colors.green}{{+{row.right_content}+}}{self.colors.reset}")


class InlineDiffFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        self._writeln(f"--- {file1}")
        self._writeln(f"+++ {file2}")
        self._writeln("")
        line_num = 1
        for action in script:
            value = str(action.value)
            if action.op == OpType.EQUAL:
                self._writeln(f"{line_num:4d}   {value}")
                line_num += 1
            elif action.op == OpType.DELETE:
                self._writeln(f"{line_num:4d} {self.colors.red}- {value}{self.colors.reset}")
                line_num += 1
            elif action.op == OpType.INSERT:
                self._writeln(f"     {self.colors.green}+ {value}{self.colors.reset}")


FormatterFactory.register("side-by-side", SideBySideFormatter)
FormatterFactory.register("compact", CompactSideBySideFormatter)
FormatterFactory.register("word", WordDiffFormatter)
FormatterFactory.register("inline", InlineDiffFormatter)