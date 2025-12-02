#!/usr/bin/env python3
import argparse
import sys
import os
from typing import Optional, List, TextIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ANSIColors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    
    @classmethod
    def disable(cls):
        cls.RESET = ''
        cls.BOLD = ''
        cls.DIM = ''
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BG_RED = ''
        cls.BG_GREEN = ''


class ColorPrinter:
    def __init__(self, use_color: bool = True, output: TextIO = sys.stdout):
        self.use_color = use_color
        self.output = output
        if not use_color:
            ANSIColors.disable()
            
    def print(self, text: str, end: str = '\n'):
        self.output.write(text + end)
        
    def print_added(self, text: str):
        self.print(f"{ANSIColors.GREEN}+{text}{ANSIColors.RESET}")
        
    def print_removed(self, text: str):
        self.print(f"{ANSIColors.RED}-{text}{ANSIColors.RESET}")
        
    def print_context(self, text: str):
        self.print(f" {text}")
        
    def print_header(self, text: str):
        self.print(f"{ANSIColors.BOLD}{text}{ANSIColors.RESET}")
        
    def print_hunk_header(self, text: str):
        self.print(f"{ANSIColors.CYAN}{text}{ANSIColors.RESET}")
        
    def print_error(self, text: str):
        sys.stderr.write(f"{ANSIColors.RED}Error: {text}{ANSIColors.RESET}\n")
        
    def print_warning(self, text: str):
        sys.stderr.write(f"{ANSIColors.YELLOW}Warning: {text}{ANSIColors.RESET}\n")
        
    def print_info(self, text: str):
        sys.stderr.write(f"{ANSIColors.BLUE}{text}{ANSIColors.RESET}\n")


class DiffOutputFormatter:
    def __init__(self, printer: ColorPrinter, context_lines: int = 3):
        self.printer = printer
        self.context_lines = context_lines
        
    def format_unified(self, script, file1: str, file2: str, lines1: List[str], lines2: List[str]):
        from algorithms.utils import OpType
        has_changes = any(action.op != OpType.EQUAL for action in script)
        if not has_changes:
            return
        self.printer.print_header(f"--- {file1}")
        self.printer.print_header(f"+++ {file2}")
        hunks = self._generate_hunks(script)
        for hunk in hunks:
            self._print_hunk(hunk, script)
            
    def _generate_hunks(self, script) -> List[dict]:
        from algorithms.utils import OpType
        if not script:
            return []
        change_indices = []
        for i, action in enumerate(script):
            if action.op != OpType.EQUAL:
                change_indices.append(i)
        if not change_indices:
            return []
        hunks = []
        current_start = max(0, change_indices[0] - self.context_lines)
        current_end = min(len(script) - 1, change_indices[0] + self.context_lines)
        for idx in change_indices[1:]:
            potential_start = max(0, idx - self.context_lines)
            if potential_start <= current_end + 1:
                current_end = min(len(script) - 1, idx + self.context_lines)
            else:
                hunks.append({'start': current_start, 'end': current_end})
                current_start = potential_start
                current_end = min(len(script) - 1, idx + self.context_lines)
        hunks.append({'start': current_start, 'end': current_end})
        return hunks
    
    def _print_hunk(self, hunk: dict, script):
        from algorithms.utils import OpType
        start = hunk['start']
        end = hunk['end']
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
        for i in range(start, end + 1):
            if script[i].op == OpType.EQUAL:
                orig_count += 1
                mod_count += 1
            elif script[i].op == OpType.DELETE:
                orig_count += 1
            elif script[i].op == OpType.INSERT:
                mod_count += 1
        header = f"@@ -{orig_start + 1},{orig_count} +{mod_start + 1},{mod_count} @@"
        self.printer.print_hunk_header(header)
        for i in range(start, end + 1):
            action = script[i]
            if action.op == OpType.EQUAL:
                self.printer.print_context(str(action.value))
            elif action.op == OpType.DELETE:
                self.printer.print_removed(str(action.value))
            elif action.op == OpType.INSERT:
                self.printer.print_added(str(action.value))

    def format_simple(self, script, file1: str, file2: str):
        from algorithms.utils import OpType
        for action in script:
            if action.op == OpType.EQUAL:
                self.printer.print_context(str(action.value))
            elif action.op == OpType.DELETE:
                self.printer.print_removed(str(action.value))
            elif action.op == OpType.INSERT:
                self.printer.print_added(str(action.value))


class CLIApplication:
    def __init__(self):
        self.parser = self._create_parser()
        self.printer: Optional[ColorPrinter] = None
        
    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog='myers-diff',
            description='Compare files using Myers diff algorithm',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  %(prog)s file1.txt file2.txt
  %(prog)s -u file1.txt file2.txt
  %(prog)s --side-by-side file1.txt file2.txt
  %(prog)s -r dir1 dir2
  %(prog)s --no-color file1.txt file2.txt
            '''
        )
        parser.add_argument('file1', help='First file or directory')
        parser.add_argument('file2', help='Second file or directory')
        format_group = parser.add_mutually_exclusive_group()
        format_group.add_argument(
            '-u', '--unified',
            action='store_true',
            default=True,
            help='Output unified diff (default)'
        )
        format_group.add_argument(
            '-y', '--side-by-side',
            action='store_true',
            help='Output side-by-side diff'
        )
        format_group.add_argument(
            '--html',
            action='store_true',
            help='Output HTML diff'
        )
        format_group.add_argument(
            '-s', '--simple',
            action='store_true',
            help='Output simple diff'
        )
        parser.add_argument(
            '-c', '--context',
            type=int,
            default=3,
            metavar='NUM',
            help='Number of context lines (default: 3)'
        )
        parser.add_argument(
            '-w', '--width',
            type=int,
            default=130,
            metavar='NUM',
            help='Output width for side-by-side (default: 130)'
        )
        parser.add_argument(
            '-r', '--recursive',
            action='store_true',
            help='Recursively compare directories'
        )
        parser.add_argument(
            '-q', '--quiet',
            action='store_true',
            help='Report only whether files differ'
        )
        parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        parser.add_argument(
            '-o', '--output',
            type=str,
            metavar='FILE',
            help='Write output to file'
        )
        parser.add_argument(
            '--ignore-whitespace',
            action='store_true',
            help='Ignore whitespace differences'
        )
        parser.add_argument(
            '--ignore-case',
            action='store_true',
            help='Ignore case differences'
        )
        parser.add_argument(
            '-v', '--version',
            action='version',
            version='%(prog)s 1.0.0'
        )
        return parser
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        args = self.parser.parse_args(argv)
        use_color = not args.no_color and sys.stdout.isatty()
        if args.output:
            output_file = open(args.output, 'w', encoding='utf-8')
            self.printer = ColorPrinter(use_color=False, output=output_file)
        else:
            self.printer = ColorPrinter(use_color=use_color)
        try:
            result = self._execute(args)
        except KeyboardInterrupt:
            self.printer.print_error("Interrupted")
            result = 130
        except Exception as e:
            self.printer.print_error(str(e))
            result = 2
        finally:
            if args.output:
                output_file.close()
        return result
    
    def _execute(self, args) -> int:
        file1 = args.file1
        file2 = args.file2
        if not os.path.exists(file1):
            self.printer.print_error(f"File not found: {file1}")
            return 2
        if not os.path.exists(file2):
            self.printer.print_error(f"File not found: {file2}")
            return 2
        if args.recursive and os.path.isdir(file1) and os.path.isdir(file2):
            return self._compare_directories(args, file1, file2)
        if os.path.isdir(file1) or os.path.isdir(file2):
            self.printer.print_error("Cannot compare directory with file. Use -r for directories.")
            return 2
        return self._compare_files(args, file1, file2)
    
    def _compare_files(self, args, file1: str, file2: str) -> int:
        from fs.binary_check import is_binary_file
        from fs.walker import read_file_lines
        from algorithms.myers import diff
        from algorithms.utils import OpType
        try:
            if is_binary_file(file1):
                self.printer.print_error(f"Binary file: {file1}")
                return 2
            if is_binary_file(file2):
                self.printer.print_error(f"Binary file: {file2}")
                return 2
        except Exception as e:
            self.printer.print_error(f"Error checking files: {e}")
            return 2
        try:
            lines1 = read_file_lines(file1)
            lines2 = read_file_lines(file2)
        except Exception as e:
            self.printer.print_error(f"Error reading files: {e}")
            return 2
        if args.ignore_whitespace:
            lines1 = [line.strip() for line in lines1]
            lines2 = [line.strip() for line in lines2]
        if args.ignore_case:
            lines1 = [line.lower() for line in lines1]
            lines2 = [line.lower() for line in lines2]
        try:
            script = diff(lines1, lines2)
        except Exception as e:
            self.printer.print_error(f"Error computing diff: {e}")
            return 2
        has_changes = any(action.op != OpType.EQUAL for action in script)
        if args.quiet:
            if has_changes:
                self.printer.print(f"Files {file1} and {file2} differ")
            return 1 if has_changes else 0
        if not has_changes:
            return 0
        formatter = DiffOutputFormatter(self.printer, args.context)
        if args.side_by_side:
            self._format_side_by_side(script, file1, file2, args.width)
        elif args.html:
            self._format_html(script, file1, file2, lines1, lines2)
        elif args.simple:
            formatter.format_simple(script, file1, file2)
        else:
            formatter.format_unified(script, file1, file2, lines1, lines2)
        return 1 if has_changes else 0
    
    def _compare_directories(self, args, dir1: str, dir2: str) -> int:
        from fs.walker import DirectoryComparator
        comparator = DirectoryComparator(dir1, dir2)
        result = comparator.compare()
        has_changes = bool(result['only_in_first'] or result['only_in_second'] or result['modified'])
        if args.quiet:
            return 1 if has_changes else 0
        if result['only_in_first']:
            self.printer.print_header(f"Only in {dir1}:")
            for f in result['only_in_first']:
                self.printer.print_removed(f"  {f}")
        if result['only_in_second']:
            self.printer.print_header(f"Only in {dir2}:")
            for f in result['only_in_second']:
                self.printer.print_added(f"  {f}")
        if result['modified']:
            self.printer.print_header("Modified files:")
            for f in result['modified']:
                self.printer.print(f"  {ANSIColors.YELLOW}{f}{ANSIColors.RESET}")
                if not args.quiet:
                    f1 = os.path.join(dir1, f)
                    f2 = os.path.join(dir2, f)
                    self._compare_files(args, f1, f2)
        return 1 if has_changes else 0
    
    def _format_side_by_side(self, script, file1: str, file2: str, width: int):
        from algorithms.utils import OpType
        col_width = (width - 3) // 2
        self.printer.print(f"{'=' * width}")
        self.printer.print(f"{file1:<{col_width}} | {file2}")
        self.printer.print(f"{'=' * width}")
        i = 0
        while i < len(script):
            action = script[i]
            if action.op == OpType.EQUAL:
                left = str(action.value)[:col_width]
                right = str(action.value)[:col_width]
                self.printer.print(f"{left:<{col_width}} | {right}")
                i += 1
            elif action.op == OpType.DELETE:
                if i + 1 < len(script) and script[i + 1].op == OpType.INSERT:
                    left = str(action.value)[:col_width]
                    right = str(script[i + 1].value)[:col_width]
                    line = f"{ANSIColors.RED}{left:<{col_width}}{ANSIColors.RESET} < {ANSIColors.GREEN}{right}{ANSIColors.RESET}"
                    self.printer.print(line)
                    i += 2
                else:
                    left = str(action.value)[:col_width]
                    line = f"{ANSIColors.RED}{left:<{col_width}}{ANSIColors.RESET} <"
                    self.printer.print(line)
                    i += 1
            elif action.op == OpType.INSERT:
                right = str(action.value)[:col_width]
                line = f"{'':<{col_width}} > {ANSIColors.GREEN}{right}{ANSIColors.RESET}"
                self.printer.print(line)
                i += 1
            else:
                i += 1
    
    def _format_html(self, script, file1: str, file2: str, lines1: List[str], lines2: List[str]):
        from algorithms.utils import OpType
        from html import escape
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html><head><meta charset="UTF-8">')
        html_parts.append(f'<title>Diff: {escape(file1)} vs {escape(file2)}</title>')
        html_parts.append('<style>')
        html_parts.append('body { font-family: monospace; margin: 20px; }')
        html_parts.append('.diff-container { border: 1px solid #ddd; border-radius: 4px; }')
        html_parts.append('.diff-header { background: #f7f7f7; padding: 10px; border-bottom: 1px solid #ddd; }')
        html_parts.append('table { width: 100%; border-collapse: collapse; }')
        html_parts.append('td { padding: 2px 8px; vertical-align: top; white-space: pre-wrap; }')
        html_parts.append('.line-num { width: 50px; text-align: right; color: #999; background: #f7f7f7; }')
        html_parts.append('.equal { background: #fff; }')
        html_parts.append('.delete { background: #ffeef0; }')
        html_parts.append('.insert { background: #e6ffed; }')
        html_parts.append('.marker { width: 20px; text-align: center; font-weight: bold; }')
        html_parts.append('.marker-del { color: #cb2431; }')
        html_parts.append('.marker-ins { color: #22863a; }')
        html_parts.append('</style></head><body>')
        html_parts.append('<div class="diff-container">')
        html_parts.append(f'<div class="diff-header"><b>--- {escape(file1)}</b><br><b>+++ {escape(file2)}</b></div>')
        html_parts.append('<table>')
        orig_line = 1
        mod_line = 1
        for action in script:
            if action.op == OpType.EQUAL:
                content = escape(str(action.value))
                html_parts.append(f'<tr class="equal"><td class="line-num">{orig_line}</td>')
                html_parts.append(f'<td class="marker"> </td><td class="line-num">{mod_line}</td>')
                html_parts.append(f'<td>{content}</td></tr>')
                orig_line += 1
                mod_line += 1
            elif action.op == OpType.DELETE:
                content = escape(str(action.value))
                html_parts.append(f'<tr class="delete"><td class="line-num">{orig_line}</td>')
                html_parts.append(f'<td class="marker marker-del">-</td><td class="line-num"></td>')
                html_parts.append(f'<td>{content}</td></tr>')
                orig_line += 1
            elif action.op == OpType.INSERT:
                content = escape(str(action.value))
                html_parts.append(f'<tr class="insert"><td class="line-num"></td>')
                html_parts.append(f'<td class="marker marker-ins">+</td><td class="line-num">{mod_line}</td>')
                html_parts.append(f'<td>{content}</td></tr>')
                mod_line += 1
        html_parts.append('</table></div></body></html>')
        self.printer.print('\n'.join(html_parts))


def main(argv: Optional[List[str]] = None) -> int:
    app = CLIApplication()
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main())
