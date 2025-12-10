from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algorithms.utils import OpType, EditAction
from formatters.base import BaseFormatter, FormatterConfig, FormatterFactory, HunkGenerator, DiffHunk


class UnifiedFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.hunk_generator = HunkGenerator(self.config.context_lines)

    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        if not self.has_changes(script):
            return
        self._writeln(f"{self.colors.bold}--- {file1}{self.colors.reset}")
        self._writeln(f"{self.colors.bold}+++ {file2}{self.colors.reset}")
        for hunk in self.hunk_generator.generate(script):
            self._write_hunk(hunk)

    def _write_hunk(self, hunk: DiffHunk):
        header = f"@@ -{hunk.orig_start + 1},{hunk.orig_count} +{hunk.mod_start + 1},{hunk.mod_count} @@"
        self._writeln(f"{self.colors.cyan}{header}{self.colors.reset}")
        for a in hunk.actions:
            v = str(a.value)
            if a.op == OpType.EQUAL:
                self._writeln(f" {v}")
            elif a.op == OpType.DELETE:
                self._writeln(f"{self.colors.red}-{v}{self.colors.reset}" if self.config.use_color else f"-{v}")
            elif a.op == OpType.INSERT:
                self._writeln(f"{self.colors.green}+{v}{self.colors.reset}" if self.config.use_color else f"+{v}")


class ContextDiffFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self.hunk_generator = HunkGenerator(self.config.context_lines)

    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        if not self.has_changes(script):
            return
        self._writeln(f"*** {file1}")
        self._writeln(f"--- {file2}")
        for hunk in self.hunk_generator.generate(script):
            self._writeln("***************")
            self._writeln(f"*** {hunk.orig_start + 1},{hunk.orig_start + hunk.orig_count} ****")
            for a in hunk.actions:
                if a.op == OpType.EQUAL:
                    self._writeln(f"  {a.value}")
                elif a.op == OpType.DELETE:
                    self._writeln(f"- {a.value}")
            self._writeln(f"--- {hunk.mod_start + 1},{hunk.mod_start + hunk.mod_count} ----")
            for a in hunk.actions:
                if a.op == OpType.EQUAL:
                    self._writeln(f"  {a.value}")
                elif a.op == OpType.INSERT:
                    self._writeln(f"+ {a.value}")


class NormalDiffFormatter(BaseFormatter):
    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        if not self.has_changes(script):
            return
        orig_line, mod_line, i = 0, 0, 0
        while i < len(script):
            a = script[i]
            if a.op == OpType.EQUAL:
                orig_line += 1
                mod_line += 1
                i += 1
            elif a.op == OpType.DELETE:
                del_start, dels = orig_line + 1, []
                while i < len(script) and script[i].op == OpType.DELETE:
                    dels.append(script[i].value)
                    orig_line += 1
                    i += 1
                ins = []
                ins_start = mod_line + 1
                while i < len(script) and script[i].op == OpType.INSERT:
                    ins.append(script[i].value)
                    mod_line += 1
                    i += 1
                del_end = del_start + len(dels) - 1
                ins_end = ins_start + len(ins) - 1
                if ins and dels:
                    self._writeln(f"{del_start},{del_end}c{ins_start},{ins_end}")
                    for l in dels:
                        self._writeln(f"< {l}")
                    self._writeln("---")
                    for l in ins:
                        self._writeln(f"> {l}")
                elif dels:
                    r = f"{del_start}" if len(dels) == 1 else f"{del_start},{del_end}"
                    self._writeln(f"{r}d{mod_line}")
                    for l in dels:
                        self._writeln(f"< {l}")
            elif a.op == OpType.INSERT:
                ins_start, ins = mod_line + 1, []
                while i < len(script) and script[i].op == OpType.INSERT:
                    ins.append(script[i].value)
                    mod_line += 1
                    i += 1
                r = f"{ins_start}" if len(ins) == 1 else f"{ins_start},{ins_start + len(ins) - 1}"
                self._writeln(f"{orig_line}a{r}")
                for l in ins:
                    self._writeln(f"> {l}")
            else:
                i += 1


FormatterFactory.register("unified", UnifiedFormatter)
FormatterFactory.register("context", ContextDiffFormatter)
FormatterFactory.register("normal", NormalDiffFormatter)