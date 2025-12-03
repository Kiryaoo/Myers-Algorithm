from typing import List, Optional, TextIO
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.utils import OpType, EditAction
from formatters.base import BaseFormatter, FormatterConfig, FormatterFactory, HunkGenerator, DiffHunk


class UnifiedDiffHeader:
    def __init__(self, file1: str, file2: str, timestamp1: Optional[str] = None, timestamp2: Optional[str] = None):
        self.file1 = file1
        self.file2 = file2
        self.timestamp1 = timestamp1
        self.timestamp2 = timestamp2
        
    def format_old_header(self) -> str:
        if self.timestamp1:
            return f"--- {self.file1}\t{self.timestamp1}"
        return f"--- {self.file1}"
        
    def format_new_header(self) -> str:
        if self.timestamp2:
            return f"+++ {self.file2}\t{self.timestamp2}"
        return f"+++ {self.file2}"


class HunkHeader:
    def __init__(self, hunk: DiffHunk, section_header: Optional[str] = None):
        self.hunk = hunk
        self.section_header = section_header
        
    def format(self) -> str:
        orig_start = self.hunk.orig_start + 1
        mod_start = self.hunk.mod_start + 1
        orig_count = self.hunk.orig_count
        mod_count = self.hunk.mod_count
        header = f"@@ -{orig_start},{orig_count} +{mod_start},{mod_count} @@"
        if self.section_header:
            header += f" {self.section_header}"
        return header


class UnifiedLineFormatter:
    def __init__(self, colors, use_color: bool = True):
        self.colors = colors
        self.use_color = use_color
        
    def format_context(self, line: str) -> str:
        return f" {line}"
        
    def format_deletion(self, line: str) -> str:
        if self.use_color:
            return f"{self.colors.red}-{line}{self.colors.reset}"
        return f"-{line}"
        
    def format_insertion(self, line: str) -> str:
        if self.use_color:
            return f"{self.colors.green}+{line}{self.colors.reset}"
        return f"+{line}"
        
    def format_action(self, action: EditAction) -> str:
        value = str(action.value)
        if action.op == OpType.EQUAL:
            return self.format_context(value)
        elif action.op == OpType.DELETE:
            return self.format_deletion(value)
        elif action.op == OpType.INSERT:
            return self.format_insertion(value)
        return value


class UnifiedDiffStats:
    def __init__(self):
        self.insertions = 0
        self.deletions = 0
        self.unchanged = 0
        
    def add_action(self, action: EditAction):
        if action.op == OpType.EQUAL:
            self.unchanged += 1
        elif action.op == OpType.DELETE:
            self.deletions += 1
        elif action.op == OpType.INSERT:
            self.insertions += 1
            
    def add_script(self, script: List[EditAction]):
        for action in script:
            self.add_action(action)
            
    def total_changes(self) -> int:
        return self.insertions + self.deletions
        
    def format_summary(self) -> str:
        parts = []
        if self.insertions > 0:
            parts.append(f"+{self.insertions}")
        if self.deletions > 0:
            parts.append(f"-{self.deletions}")
        return ", ".join(parts) if parts else "no changes"


class UnifiedFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.hunk_generator = HunkGenerator(self.config.context_lines)
        self.line_formatter = UnifiedLineFormatter(self.colors, self.config.use_color)
        self.stats = UnifiedDiffStats()
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        if not self.has_changes(script):
            return
        self._write_header(file1, file2)
        hunks = self.hunk_generator.generate(script)
        for hunk in hunks:
            self._write_hunk(hunk)
        self.stats.add_script(script)
        
    def _write_header(self, file1: str, file2: str):
        header = UnifiedDiffHeader(file1, file2)
        self._writeln(f"{self.colors.bold}{header.format_old_header()}{self.colors.reset}")
        self._writeln(f"{self.colors.bold}{header.format_new_header()}{self.colors.reset}")
        
    def _write_hunk(self, hunk: DiffHunk):
        hunk_header = HunkHeader(hunk)
        self._writeln(f"{self.colors.cyan}{hunk_header.format()}{self.colors.reset}")
        for action in hunk.actions:
            line = self.line_formatter.format_action(action)
            self._writeln(line)


class ContextDiffFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.hunk_generator = HunkGenerator(self.config.context_lines)
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        if not self.has_changes(script):
            return
        self._writeln(f"*** {file1}")
        self._writeln(f"--- {file2}")
        hunks = self.hunk_generator.generate(script)
        for hunk in hunks:
            self._write_context_hunk(hunk)
            
    def _write_context_hunk(self, hunk: DiffHunk):
        self._writeln("***************")
        orig_start = hunk.orig_start + 1
        orig_end = hunk.orig_start + hunk.orig_count
        self._writeln(f"*** {orig_start},{orig_end} ****")
        has_deletions = any(a.op in (OpType.EQUAL, OpType.DELETE) for a in hunk.actions)
        if has_deletions:
            for action in hunk.actions:
                if action.op == OpType.EQUAL:
                    self._writeln(f"  {action.value}")
                elif action.op == OpType.DELETE:
                    self._writeln(f"- {action.value}")
        mod_start = hunk.mod_start + 1
        mod_end = hunk.mod_start + hunk.mod_count
        self._writeln(f"--- {mod_start},{mod_end} ----")
        has_insertions = any(a.op in (OpType.EQUAL, OpType.INSERT) for a in hunk.actions)
        if has_insertions:
            for action in hunk.actions:
                if action.op == OpType.EQUAL:
                    self._writeln(f"  {action.value}")
                elif action.op == OpType.INSERT:
                    self._writeln(f"+ {action.value}")


class NormalDiffFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        if not self.has_changes(script):
            return
        orig_line = 0
        mod_line = 0
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                orig_line += 1
                mod_line += 1
                i += 1
            elif action.op == OpType.DELETE:
                delete_start = orig_line + 1
                deletions = []
                while i < len(script) and script[i].op == OpType.DELETE:
                    deletions.append(script[i].value)
                    orig_line += 1
                    i += 1
                insertions = []
                insert_start = mod_line + 1
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    mod_line += 1
                    i += 1
                delete_end = delete_start + len(deletions) - 1
                insert_end = insert_start + len(insertions) - 1
                if insertions and deletions:
                    self._writeln(f"{delete_start},{delete_end}c{insert_start},{insert_end}")
                    for line in deletions:
                        self._writeln(f"< {line}")
                    self._writeln("---")
                    for line in insertions:
                        self._writeln(f"> {line}")
                elif deletions:
                    if len(deletions) == 1:
                        self._writeln(f"{delete_start}d{mod_line}")
                    else:
                        self._writeln(f"{delete_start},{delete_end}d{mod_line}")
                    for line in deletions:
                        self._writeln(f"< {line}")
            elif action.op == OpType.INSERT:
                insert_start = mod_line + 1
                insertions = []
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    mod_line += 1
                    i += 1
                insert_end = insert_start + len(insertions) - 1
                if len(insertions) == 1:
                    self._writeln(f"{orig_line}a{insert_start}")
                else:
                    self._writeln(f"{orig_line}a{insert_start},{insert_end}")
                for line in insertions:
                    self._writeln(f"> {line}")
            else:
                i += 1


class EDDiffFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        if not self.has_changes(script):
            return
        commands = self._generate_ed_commands(script)
        for cmd in reversed(commands):
            self._writeln(cmd)
            
    def _generate_ed_commands(self, script: List[EditAction]) -> List[str]:
        commands = []
        orig_line = 0
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                orig_line += 1
                i += 1
            elif action.op == OpType.DELETE:
                delete_start = orig_line + 1
                deletions = []
                while i < len(script) and script[i].op == OpType.DELETE:
                    deletions.append(script[i].value)
                    orig_line += 1
                    i += 1
                insertions = []
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    i += 1
                delete_end = delete_start + len(deletions) - 1
                if insertions:
                    if len(deletions) == 1:
                        commands.append(f"{delete_start}c")
                    else:
                        commands.append(f"{delete_start},{delete_end}c")
                    for line in insertions:
                        commands.append(line)
                    commands.append(".")
                else:
                    if len(deletions) == 1:
                        commands.append(f"{delete_start}d")
                    else:
                        commands.append(f"{delete_start},{delete_end}d")
            elif action.op == OpType.INSERT:
                insert_after = orig_line
                insertions = []
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    i += 1
                commands.append(f"{insert_after}a")
                for line in insertions:
                    commands.append(line)
                commands.append(".")
            else:
                i += 1
        return commands


class RCSDiffFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        if not self.has_changes(script):
            return
        orig_line = 0
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                orig_line += 1
                i += 1
            elif action.op == OpType.DELETE:
                delete_start = orig_line + 1
                delete_count = 0
                while i < len(script) and script[i].op == OpType.DELETE:
                    delete_count += 1
                    orig_line += 1
                    i += 1
                insertions = []
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    i += 1
                self._writeln(f"d{delete_start} {delete_count}")
                if insertions:
                    self._writeln(f"a{delete_start} {len(insertions)}")
                    for line in insertions:
                        self._writeln(line)
            elif action.op == OpType.INSERT:
                insert_after = orig_line
                insertions = []
                while i < len(script) and script[i].op == OpType.INSERT:
                    insertions.append(script[i].value)
                    i += 1
                self._writeln(f"a{insert_after} {len(insertions)}")
                for line in insertions:
                    self._writeln(line)
            else:
                i += 1


FormatterFactory.register("unified", UnifiedFormatter)
FormatterFactory.register("context", ContextDiffFormatter)
FormatterFactory.register("normal", NormalDiffFormatter)
FormatterFactory.register("ed", EDDiffFormatter)
FormatterFactory.register("rcs", RCSDiffFormatter)
