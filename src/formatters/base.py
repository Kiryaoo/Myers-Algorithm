from abc import ABC, abstractmethod
from typing import List, TextIO, Optional, Any, Dict, Tuple
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.utils import OpType, EditAction


class OutputTarget(Enum):
    STDOUT = "stdout"
    FILE = "file"
    STRING = "string"


class FormatterConfig:
    def __init__(
        self,
        context_lines: int = 3,
        width: int = 130,
        use_color: bool = True,
        tab_size: int = 4,
        show_line_numbers: bool = True,
        ignore_whitespace: bool = False,
        ignore_case: bool = False,
        encoding: str = "utf-8"
    ):
        self.context_lines = context_lines
        self.width = width
        self.use_color = use_color
        self.tab_size = tab_size
        self.show_line_numbers = show_line_numbers
        self.ignore_whitespace = ignore_whitespace
        self.ignore_case = ignore_case
        self.encoding = encoding
        
    def copy(self) -> 'FormatterConfig':
        return FormatterConfig(
            context_lines=self.context_lines,
            width=self.width,
            use_color=self.use_color,
            tab_size=self.tab_size,
            show_line_numbers=self.show_line_numbers,
            ignore_whitespace=self.ignore_whitespace,
            ignore_case=self.ignore_case,
            encoding=self.encoding
        )
        
    def with_context_lines(self, lines: int) -> 'FormatterConfig':
        cfg = self.copy()
        cfg.context_lines = lines
        return cfg
        
    def with_width(self, width: int) -> 'FormatterConfig':
        cfg = self.copy()
        cfg.width = width
        return cfg
        
    def with_color(self, use_color: bool) -> 'FormatterConfig':
        cfg = self.copy()
        cfg.use_color = use_color
        return cfg


class ColorScheme:
    def __init__(self):
        self.reset = '\033[0m'
        self.bold = '\033[1m'
        self.dim = '\033[2m'
        self.red = '\033[31m'
        self.green = '\033[32m'
        self.yellow = '\033[33m'
        self.blue = '\033[34m'
        self.magenta = '\033[35m'
        self.cyan = '\033[36m'
        self.white = '\033[37m'
        self.bg_red = '\033[41m'
        self.bg_green = '\033[42m'
        self.bg_yellow = '\033[43m'
        
    def disable_colors(self):
        self.reset = ''
        self.bold = ''
        self.dim = ''
        self.red = ''
        self.green = ''
        self.yellow = ''
        self.blue = ''
        self.magenta = ''
        self.cyan = ''
        self.white = ''
        self.bg_red = ''
        self.bg_green = ''
        self.bg_yellow = ''
        
    @classmethod
    def no_color(cls) -> 'ColorScheme':
        scheme = cls()
        scheme.disable_colors()
        return scheme


class OutputWriter:
    def __init__(self, target: OutputTarget = OutputTarget.STDOUT, output: Optional[TextIO] = None):
        self.target = target
        self._output = output or sys.stdout
        self._buffer: List[str] = []
        
    def write(self, text: str):
        if self.target == OutputTarget.STRING:
            self._buffer.append(text)
        else:
            self._output.write(text)
            
    def writeln(self, text: str = ""):
        self.write(text + "\n")
        
    def get_output(self) -> str:
        return "".join(self._buffer)
        
    def flush(self):
        if self.target != OutputTarget.STRING:
            self._output.flush()


class DiffHunk:
    def __init__(
        self,
        orig_start: int,
        orig_count: int,
        mod_start: int,
        mod_count: int,
        actions: List[EditAction]
    ):
        self.orig_start = orig_start
        self.orig_count = orig_count
        self.mod_start = mod_start
        self.mod_count = mod_count
        self.actions = actions
        
    def __repr__(self) -> str:
        return f"DiffHunk(@@ -{self.orig_start},{self.orig_count} +{self.mod_start},{self.mod_count} @@)"
        
    def is_empty(self) -> bool:
        return len(self.actions) == 0
        
    def has_changes(self) -> bool:
        return any(a.op != OpType.EQUAL for a in self.actions)


class HunkGenerator:
    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines
        
    def generate(self, script: List[EditAction]) -> List[DiffHunk]:
        if not script:
            return []
        change_indices = self._find_change_indices(script)
        if not change_indices:
            return []
        ranges = self._merge_ranges(change_indices, len(script))
        hunks = []
        for start, end in ranges:
            hunk = self._create_hunk(script, start, end)
            hunks.append(hunk)
        return hunks
        
    def _find_change_indices(self, script: List[EditAction]) -> List[int]:
        indices = []
        for i, action in enumerate(script):
            if action.op != OpType.EQUAL:
                indices.append(i)
        return indices
        
    def _merge_ranges(self, change_indices: List[int], script_len: int) -> List[Tuple[int, int]]:
        if not change_indices:
            return []
        ranges = []
        current_start = max(0, change_indices[0] - self.context_lines)
        current_end = min(script_len - 1, change_indices[0] + self.context_lines)
        for idx in change_indices[1:]:
            potential_start = max(0, idx - self.context_lines)
            if potential_start <= current_end + 1:
                current_end = min(script_len - 1, idx + self.context_lines)
            else:
                ranges.append((current_start, current_end))
                current_start = potential_start
                current_end = min(script_len - 1, idx + self.context_lines)
        ranges.append((current_start, current_end))
        return ranges
        
    def _create_hunk(self, script: List[EditAction], start: int, end: int) -> DiffHunk:
        orig_start = 0
        mod_start = 0
        for i in range(start):
            if script[i].op == OpType.EQUAL:
                orig_start += 1
                mod_start += 1
            elif script[i].op == OpType.DELETE:
                orig_start += 1
            elif script[i].op == OpType.INSERT:
                mod_start += 1
        orig_count = 0
        mod_count = 0
        actions = []
        for i in range(start, end + 1):
            action = script[i]
            actions.append(action)
            if action.op == OpType.EQUAL:
                orig_count += 1
                mod_count += 1
            elif action.op == OpType.DELETE:
                orig_count += 1
            elif action.op == OpType.INSERT:
                mod_count += 1
        return DiffHunk(orig_start, orig_count, mod_start, mod_count, actions)


class BaseFormatter(ABC):
    def __init__(self, config: Optional[FormatterConfig] = None):
        self.config = config or FormatterConfig()
        self.colors = ColorScheme() if self.config.use_color else ColorScheme.no_color()
        self.writer: Optional[OutputWriter] = None
        
    def format(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]] = None,
        lines2: Optional[List[str]] = None,
        output: Optional[TextIO] = None
    ) -> str:
        if output is None:
            self.writer = OutputWriter(OutputTarget.STRING)
        else:
            self.writer = OutputWriter(OutputTarget.FILE, output)
        self._format_impl(script, file1, file2, lines1, lines2)
        if output is None:
            return self.writer.get_output()
        return ""
        
    @abstractmethod
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        pass
        
    def has_changes(self, script: List[EditAction]) -> bool:
        return any(action.op != OpType.EQUAL for action in script)
        
    def _write(self, text: str):
        if self.writer:
            self.writer.write(text)
            
    def _writeln(self, text: str = ""):
        if self.writer:
            self.writer.writeln(text)


class SimpleFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        for action in script:
            value = str(action.value)
            if action.op == OpType.EQUAL:
                self._writeln(f" {value}")
            elif action.op == OpType.DELETE:
                self._writeln(f"{self.colors.red}-{value}{self.colors.reset}")
            elif action.op == OpType.INSERT:
                self._writeln(f"{self.colors.green}+{value}{self.colors.reset}")


class FormatterFactory:
    _formatters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, formatter_class: type):
        cls._formatters[name] = formatter_class
        
    @classmethod
    def create(cls, name: str, config: Optional[FormatterConfig] = None) -> BaseFormatter:
        if name not in cls._formatters:
            raise ValueError(f"Unknown formatter: {name}")
        return cls._formatters[name](config)
        
    @classmethod
    def available(cls) -> List[str]:
        return list(cls._formatters.keys())


FormatterFactory.register("simple", SimpleFormatter)
