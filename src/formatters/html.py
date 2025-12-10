from typing import List, Optional, Dict
from html import escape as html_escape
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from algorithms.utils import OpType, EditAction
from formatters.base import BaseFormatter, FormatterConfig, FormatterFactory


DEFAULT_STYLES = """
body { font-family: monospace; margin: 20px; background: #fafafa; color: #333; }
.diff-container { border: 1px solid #ddd; border-radius: 4px; overflow: hidden; margin-bottom: 20px; }
.diff-header { background: #f7f7f7; padding: 10px 15px; border-bottom: 1px solid #ddd; font-weight: bold; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td { padding: 2px 8px; vertical-align: top; white-space: pre-wrap; word-wrap: break-word; }
.line-num { width: 50px; text-align: right; color: #999; background: #f7f7f7; border-right: 1px solid #eee; }
.equal { background: #fff; }
.delete { background: #ffeef0; }
.delete .line-num { background: #ffdce0; color: #cb2431; }
.insert { background: #e6ffed; }
.insert .line-num { background: #cdffd8; color: #22863a; }
.marker { width: 20px; text-align: center; font-weight: bold; }
.marker-del { color: #cb2431; background: #ffdce0; }
.marker-ins { color: #22863a; background: #cdffd8; }
.stats { padding: 10px 15px; background: #f7f7f7; border-top: 1px solid #ddd; font-size: 12px; }
.stats .additions { color: #22863a; }
.stats .deletions { color: #cb2431; }
.content { width: 45%; }
.gutter { width: 10px; background: #f0f0f0; }
"""


class HTMLFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)

    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        rows, insertions, deletions = [], 0, 0
        orig_line, mod_line = 1, 1
        for action in script:
            v = html_escape(str(action.value))
            if action.op == OpType.EQUAL:
                rows.append(f'<tr class="equal"><td class="line-num">{orig_line}</td>'
                           f'<td class="marker"> </td><td class="line-num">{mod_line}</td><td>{v}</td></tr>')
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                rows.append(f'<tr class="delete"><td class="line-num">{orig_line}</td>'
                           f'<td class="marker marker-del">-</td><td class="line-num"></td><td>{v}</td></tr>')
                orig_line += 1
                deletions += 1
            elif action.op == OpType.INSERT:
                rows.append(f'<tr class="insert"><td class="line-num"></td>'
                           f'<td class="marker marker-ins">+</td><td class="line-num">{mod_line}</td><td>{v}</td></tr>')
                mod_line += 1
                insertions += 1

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Diff: {html_escape(file1)} vs {html_escape(file2)}</title>
<style>{DEFAULT_STYLES}</style></head><body>
<div class="diff-container">
<div class="diff-header"><span>--- {html_escape(file1)}</span><br><span>+++ {html_escape(file2)}</span></div>
<table>{"".join(rows)}</table>
<div class="stats"><span class="additions">+{insertions}</span>, <span class="deletions">-{deletions}</span></div>
</div></body></html>"""
        self._write(html)


class SideBySideHTMLFormatter(BaseFormatter):
    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        rows = []
        left_num, right_num, i = 1, 1, 0
        while i < len(script):
            a = script[i]
            if a.op == OpType.EQUAL:
                v = html_escape(str(a.value))
                rows.append(f'<tr class="equal"><td class="line-num">{left_num}</td><td class="content">{v}</td>'
                           f'<td class="gutter"></td><td class="line-num">{right_num}</td><td class="content">{v}</td></tr>')
                left_num += 1
                right_num += 1
                i += 1
            elif a.op == OpType.DELETE:
                lv = html_escape(str(a.value))
                if i + 1 < len(script) and script[i + 1].op == OpType.INSERT:
                    rv = html_escape(str(script[i + 1].value))
                    rows.append(f'<tr><td class="line-num delete">{left_num}</td><td class="content delete">{lv}</td>'
                               f'<td class="gutter"></td><td class="line-num insert">{right_num}</td><td class="content insert">{rv}</td></tr>')
                    left_num += 1
                    right_num += 1
                    i += 2
                else:
                    rows.append(f'<tr><td class="line-num delete">{left_num}</td><td class="content delete">{lv}</td>'
                               f'<td class="gutter"></td><td class="line-num"></td><td class="content"></td></tr>')
                    left_num += 1
                    i += 1
            elif a.op == OpType.INSERT:
                rv = html_escape(str(a.value))
                rows.append(f'<tr><td class="line-num"></td><td class="content"></td>'
                           f'<td class="gutter"></td><td class="line-num insert">{right_num}</td><td class="content insert">{rv}</td></tr>')
                right_num += 1
                i += 1
            else:
                i += 1

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Diff: {html_escape(file1)} vs {html_escape(file2)}</title>
<style>{DEFAULT_STYLES}</style></head><body>
<div class="diff-container">
<div class="diff-header">{html_escape(file1)} vs {html_escape(file2)}</div>
<table>{"".join(rows)}</table>
</div></body></html>"""
        self._write(html)


class JSONFormatter(BaseFormatter):
    def _format_impl(self, script: List[EditAction], file1: str, file2: str,
                     lines1: Optional[List[str]], lines2: Optional[List[str]]):
        import json
        result = {"file1": file1, "file2": file2, "changes": [],
                  "stats": {"insertions": 0, "deletions": 0, "unchanged": 0}}
        orig_line, mod_line = 1, 1
        for a in script:
            v = str(a.value)
            if a.op == OpType.EQUAL:
                result["changes"].append({"type": "equal", "orig_line": orig_line, "mod_line": mod_line, "content": v})
                result["stats"]["unchanged"] += 1
                orig_line += 1
                mod_line += 1
            elif a.op == OpType.DELETE:
                result["changes"].append({"type": "delete", "orig_line": orig_line, "content": v})
                result["stats"]["deletions"] += 1
                orig_line += 1
            elif a.op == OpType.INSERT:
                result["changes"].append({"type": "insert", "mod_line": mod_line, "content": v})
                result["stats"]["insertions"] += 1
                mod_line += 1
        self._write(json.dumps(result, indent=2, ensure_ascii=False))


FormatterFactory.register("html", HTMLFormatter)
FormatterFactory.register("html-side-by-side", SideBySideHTMLFormatter)
FormatterFactory.register("json", JSONFormatter)
