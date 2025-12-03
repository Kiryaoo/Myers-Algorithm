from typing import List, Optional, Dict, Any
from html import escape as html_escape
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.utils import OpType, EditAction
from formatters.base import BaseFormatter, FormatterConfig, FormatterFactory


class CSSStylesheet:
    def __init__(self):
        self.styles: Dict[str, Dict[str, str]] = {}
        
    def add_rule(self, selector: str, properties: Dict[str, str]):
        self.styles[selector] = properties
        
    def render(self) -> str:
        lines = []
        for selector, props in self.styles.items():
            prop_lines = [f"    {k}: {v};" for k, v in props.items()]
            lines.append(f"{selector} {{")
            lines.extend(prop_lines)
            lines.append("}")
        return "\n".join(lines)


class DiffStylesheet(CSSStylesheet):
    def __init__(self):
        super().__init__()
        self._add_default_styles()
        
    def _add_default_styles(self):
        self.add_rule("body", {
            "font-family": "monospace",
            "margin": "20px",
            "background-color": "#fafafa",
            "color": "#333"
        })
        self.add_rule(".diff-container", {
            "border": "1px solid #ddd",
            "border-radius": "4px",
            "overflow": "hidden",
            "margin-bottom": "20px"
        })
        self.add_rule(".diff-header", {
            "background": "#f7f7f7",
            "padding": "10px 15px",
            "border-bottom": "1px solid #ddd",
            "font-weight": "bold"
        })
        self.add_rule(".diff-header .filename", {
            "color": "#333"
        })
        self.add_rule("table", {
            "width": "100%",
            "border-collapse": "collapse",
            "font-size": "13px"
        })
        self.add_rule("td", {
            "padding": "2px 8px",
            "vertical-align": "top",
            "white-space": "pre-wrap",
            "word-wrap": "break-word"
        })
        self.add_rule(".line-num", {
            "width": "50px",
            "text-align": "right",
            "color": "#999",
            "background": "#f7f7f7",
            "border-right": "1px solid #eee",
            "user-select": "none"
        })
        self.add_rule(".equal", {
            "background": "#fff"
        })
        self.add_rule(".delete", {
            "background": "#ffeef0"
        })
        self.add_rule(".delete .line-num", {
            "background": "#ffdce0",
            "color": "#cb2431"
        })
        self.add_rule(".insert", {
            "background": "#e6ffed"
        })
        self.add_rule(".insert .line-num", {
            "background": "#cdffd8",
            "color": "#22863a"
        })
        self.add_rule(".marker", {
            "width": "20px",
            "text-align": "center",
            "font-weight": "bold"
        })
        self.add_rule(".marker-del", {
            "color": "#cb2431",
            "background": "#ffdce0"
        })
        self.add_rule(".marker-ins", {
            "color": "#22863a",
            "background": "#cdffd8"
        })
        self.add_rule(".hunk-header", {
            "background": "#f1f8ff",
            "color": "#0366d6",
            "padding": "8px 15px",
            "border-top": "1px solid #ddd"
        })
        self.add_rule(".stats", {
            "padding": "10px 15px",
            "background": "#f7f7f7",
            "border-top": "1px solid #ddd",
            "font-size": "12px"
        })
        self.add_rule(".stats .additions", {
            "color": "#22863a"
        })
        self.add_rule(".stats .deletions", {
            "color": "#cb2431"
        })


class HTMLElement:
    def __init__(self, tag: str, attrs: Optional[Dict[str, str]] = None, content: str = ""):
        self.tag = tag
        self.attrs = attrs or {}
        self.content = content
        self.children: List['HTMLElement'] = []
        
    def add_child(self, child: 'HTMLElement') -> 'HTMLElement':
        self.children.append(child)
        return child
        
    def add_text(self, text: str):
        self.content += text
        
    def render(self, indent: int = 0) -> str:
        indent_str = "  " * indent
        attrs_str = ""
        if self.attrs:
            attrs_str = " " + " ".join(f'{k}="{v}"' for k, v in self.attrs.items())
        if not self.children and not self.content:
            return f"{indent_str}<{self.tag}{attrs_str}></{self.tag}>"
        parts = [f"{indent_str}<{self.tag}{attrs_str}>"]
        if self.content:
            parts.append(self.content)
        for child in self.children:
            parts.append(child.render(indent + 1))
        if self.children:
            parts.append(f"{indent_str}</{self.tag}>")
        else:
            parts[-1] += f"</{self.tag}>"
        return "\n".join(parts)


class HTMLDocument:
    def __init__(self, title: str = "Diff"):
        self.title = title
        self.stylesheet = DiffStylesheet()
        self.body_content: List[str] = []
        
    def add_content(self, html: str):
        self.body_content.append(html)
        
    def render(self) -> str:
        parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"  <meta charset=\"UTF-8\">",
            f"  <title>{html_escape(self.title)}</title>",
            "  <style>",
            self.stylesheet.render(),
            "  </style>",
            "</head>",
            "<body>",
        ]
        parts.extend(self.body_content)
        parts.extend([
            "</body>",
            "</html>"
        ])
        return "\n".join(parts)


class DiffTableBuilder:
    def __init__(self):
        self.rows: List[str] = []
        self.insertions = 0
        self.deletions = 0
        
    def add_equal_row(self, orig_line: int, mod_line: int, content: str):
        escaped = html_escape(content)
        self.rows.append(
            f'<tr class="equal">'
            f'<td class="line-num">{orig_line}</td>'
            f'<td class="marker"> </td>'
            f'<td class="line-num">{mod_line}</td>'
            f'<td>{escaped}</td>'
            f'</tr>'
        )
        
    def add_delete_row(self, orig_line: int, content: str):
        escaped = html_escape(content)
        self.rows.append(
            f'<tr class="delete">'
            f'<td class="line-num">{orig_line}</td>'
            f'<td class="marker marker-del">-</td>'
            f'<td class="line-num"></td>'
            f'<td>{escaped}</td>'
            f'</tr>'
        )
        self.deletions += 1
        
    def add_insert_row(self, mod_line: int, content: str):
        escaped = html_escape(content)
        self.rows.append(
            f'<tr class="insert">'
            f'<td class="line-num"></td>'
            f'<td class="marker marker-ins">+</td>'
            f'<td class="line-num">{mod_line}</td>'
            f'<td>{escaped}</td>'
            f'</tr>'
        )
        self.insertions += 1
        
    def add_hunk_header(self, header: str):
        escaped = html_escape(header)
        self.rows.append(
            f'<tr><td colspan="4" class="hunk-header">{escaped}</td></tr>'
        )
        
    def render(self) -> str:
        return "<table>\n" + "\n".join(self.rows) + "\n</table>"
        
    def get_stats(self) -> Dict[str, int]:
        return {"insertions": self.insertions, "deletions": self.deletions}


class SideBySideTableBuilder:
    def __init__(self):
        self.rows: List[str] = []
        
    def add_equal_row(self, left_num: int, left_content: str, right_num: int, right_content: str):
        left_escaped = html_escape(left_content)
        right_escaped = html_escape(right_content)
        self.rows.append(
            f'<tr class="equal">'
            f'<td class="line-num">{left_num}</td>'
            f'<td class="content">{left_escaped}</td>'
            f'<td class="gutter"></td>'
            f'<td class="line-num">{right_num}</td>'
            f'<td class="content">{right_escaped}</td>'
            f'</tr>'
        )
        
    def add_change_row(
        self,
        left_num: Optional[int],
        left_content: str,
        right_num: Optional[int],
        right_content: str,
        change_type: str
    ):
        left_escaped = html_escape(left_content)
        right_escaped = html_escape(right_content)
        left_num_str = str(left_num) if left_num else ""
        right_num_str = str(right_num) if right_num else ""
        left_class = "delete" if change_type in ("delete", "change") else ""
        right_class = "insert" if change_type in ("insert", "change") else ""
        self.rows.append(
            f'<tr>'
            f'<td class="line-num {left_class}">{left_num_str}</td>'
            f'<td class="content {left_class}">{left_escaped}</td>'
            f'<td class="gutter"></td>'
            f'<td class="line-num {right_class}">{right_num_str}</td>'
            f'<td class="content {right_class}">{right_escaped}</td>'
            f'</tr>'
        )
        
    def render(self) -> str:
        return "<table>\n" + "\n".join(self.rows) + "\n</table>"


class HTMLFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        doc = HTMLDocument(f"Diff: {file1} vs {file2}")
        table_builder = DiffTableBuilder()
        orig_line = 1
        mod_line = 1
        for action in script:
            value = str(action.value)
            if action.op == OpType.EQUAL:
                table_builder.add_equal_row(orig_line, mod_line, value)
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                table_builder.add_delete_row(orig_line, value)
                orig_line += 1
            elif action.op == OpType.INSERT:
                table_builder.add_insert_row(mod_line, value)
                mod_line += 1
        header_html = (
            f'<div class="diff-container">'
            f'<div class="diff-header">'
            f'<span class="filename">--- {html_escape(file1)}</span><br>'
            f'<span class="filename">+++ {html_escape(file2)}</span>'
            f'</div>'
        )
        doc.add_content(header_html)
        doc.add_content(table_builder.render())
        stats = table_builder.get_stats()
        stats_html = (
            f'<div class="stats">'
            f'<span class="additions">+{stats["insertions"]} additions</span>, '
            f'<span class="deletions">-{stats["deletions"]} deletions</span>'
            f'</div>'
            f'</div>'
        )
        doc.add_content(stats_html)
        self._write(doc.render())


class SideBySideHTMLFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        self._add_side_by_side_styles()
        
    def _add_side_by_side_styles(self):
        pass
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        doc = HTMLDocument(f"Side-by-Side Diff: {file1} vs {file2}")
        doc.stylesheet.add_rule(".content", {
            "width": "45%"
        })
        doc.stylesheet.add_rule(".gutter", {
            "width": "10px",
            "background": "#f0f0f0"
        })
        table_builder = SideBySideTableBuilder()
        left_num = 1
        right_num = 1
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                table_builder.add_equal_row(
                    left_num, str(action.value),
                    right_num, str(action.value)
                )
                left_num += 1
                right_num += 1
                i += 1
            elif action.op == OpType.DELETE:
                if i + 1 < len(script) and script[i + 1].op == OpType.INSERT:
                    table_builder.add_change_row(
                        left_num, str(action.value),
                        right_num, str(script[i + 1].value),
                        "change"
                    )
                    left_num += 1
                    right_num += 1
                    i += 2
                else:
                    table_builder.add_change_row(
                        left_num, str(action.value),
                        None, "",
                        "delete"
                    )
                    left_num += 1
                    i += 1
            elif action.op == OpType.INSERT:
                table_builder.add_change_row(
                    None, "",
                    right_num, str(action.value),
                    "insert"
                )
                right_num += 1
                i += 1
            else:
                i += 1
        header_html = (
            f'<div class="diff-container">'
            f'<div class="diff-header">'
            f'<span class="filename">{html_escape(file1)}</span> vs '
            f'<span class="filename">{html_escape(file2)}</span>'
            f'</div>'
        )
        doc.add_content(header_html)
        doc.add_content(table_builder.render())
        doc.add_content('</div>')
        self._write(doc.render())


class GitHubStyleFormatter(BaseFormatter):
    def __init__(self, config: Optional[FormatterConfig] = None):
        super().__init__(config)
        
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        doc = HTMLDocument(f"Diff: {file1} vs {file2}")
        doc.stylesheet.add_rule(".blob-code-deletion", {
            "background-color": "#ffeef0"
        })
        doc.stylesheet.add_rule(".blob-code-addition", {
            "background-color": "#e6ffed"
        })
        doc.stylesheet.add_rule(".blob-num-deletion", {
            "background-color": "#ffdce0"
        })
        doc.stylesheet.add_rule(".blob-num-addition", {
            "background-color": "#cdffd8"
        })
        doc.stylesheet.add_rule(".blob-code-inner", {
            "padding": "0 10px"
        })
        doc.stylesheet.add_rule(".diff-table", {
            "border-collapse": "collapse",
            "width": "100%"
        })
        rows = []
        orig_line = 1
        mod_line = 1
        for action in script:
            value = html_escape(str(action.value))
            if action.op == OpType.EQUAL:
                rows.append(
                    f'<tr>'
                    f'<td class="blob-num">{orig_line}</td>'
                    f'<td class="blob-num">{mod_line}</td>'
                    f'<td class="blob-code"><span class="blob-code-inner">{value}</span></td>'
                    f'</tr>'
                )
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                rows.append(
                    f'<tr>'
                    f'<td class="blob-num blob-num-deletion">{orig_line}</td>'
                    f'<td class="blob-num blob-num-deletion"></td>'
                    f'<td class="blob-code blob-code-deletion"><span class="blob-code-inner">-{value}</span></td>'
                    f'</tr>'
                )
                orig_line += 1
            elif action.op == OpType.INSERT:
                rows.append(
                    f'<tr>'
                    f'<td class="blob-num blob-num-addition"></td>'
                    f'<td class="blob-num blob-num-addition">{mod_line}</td>'
                    f'<td class="blob-code blob-code-addition"><span class="blob-code-inner">+{value}</span></td>'
                    f'</tr>'
                )
                mod_line += 1
        header_html = (
            f'<div class="diff-container">'
            f'<div class="diff-header">'
            f'<span class="filename">{html_escape(file1)}</span> → '
            f'<span class="filename">{html_escape(file2)}</span>'
            f'</div>'
            f'<table class="diff-table">'
        )
        doc.add_content(header_html)
        doc.add_content("\n".join(rows))
        doc.add_content('</table></div>')
        self._write(doc.render())


class JSONFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        import json
        result = {
            "file1": file1,
            "file2": file2,
            "changes": [],
            "stats": {
                "insertions": 0,
                "deletions": 0,
                "unchanged": 0
            }
        }
        orig_line = 1
        mod_line = 1
        for action in script:
            value = str(action.value)
            if action.op == OpType.EQUAL:
                result["changes"].append({
                    "type": "equal",
                    "orig_line": orig_line,
                    "mod_line": mod_line,
                    "content": value
                })
                result["stats"]["unchanged"] += 1
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                result["changes"].append({
                    "type": "delete",
                    "orig_line": orig_line,
                    "content": value
                })
                result["stats"]["deletions"] += 1
                orig_line += 1
            elif action.op == OpType.INSERT:
                result["changes"].append({
                    "type": "insert",
                    "mod_line": mod_line,
                    "content": value
                })
                result["stats"]["insertions"] += 1
                mod_line += 1
        self._write(json.dumps(result, indent=2, ensure_ascii=False))


class XMLFormatter(BaseFormatter):
    def _format_impl(
        self,
        script: List[EditAction],
        file1: str,
        file2: str,
        lines1: Optional[List[str]],
        lines2: Optional[List[str]]
    ):
        self._writeln('<?xml version="1.0" encoding="UTF-8"?>')
        self._writeln('<diff>')
        self._writeln(f'  <file1>{html_escape(file1)}</file1>')
        self._writeln(f'  <file2>{html_escape(file2)}</file2>')
        self._writeln('  <changes>')
        orig_line = 1
        mod_line = 1
        for action in script:
            value = html_escape(str(action.value))
            if action.op == OpType.EQUAL:
                self._writeln(f'    <equal orig="{orig_line}" mod="{mod_line}">{value}</equal>')
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                self._writeln(f'    <delete orig="{orig_line}">{value}</delete>')
                orig_line += 1
            elif action.op == OpType.INSERT:
                self._writeln(f'    <insert mod="{mod_line}">{value}</insert>')
                mod_line += 1
        self._writeln('  </changes>')
        self._writeln('</diff>')


FormatterFactory.register("html", HTMLFormatter)
FormatterFactory.register("html-side-by-side", SideBySideHTMLFormatter)
FormatterFactory.register("github", GitHubStyleFormatter)
FormatterFactory.register("json", JSONFormatter)
FormatterFactory.register("xml", XMLFormatter)
