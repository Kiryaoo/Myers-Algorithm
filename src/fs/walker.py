import os
import re
import fnmatch
from typing import List, Optional, Iterator, Tuple, Set, Callable
from pathlib import Path
from dataclasses import dataclass, field
from .binary_check import is_binary_file, get_file_encoding, FileTypeInfo


@dataclass
class FileEntry:
    path: str
    relative_path: str
    is_file: bool
    is_dir: bool
    size: int
    extension: str
    
    @classmethod
    def from_path(cls, path: str, base_path: str) -> 'FileEntry':
        rel_path = os.path.relpath(path, base_path)
        is_file = os.path.isfile(path)
        is_dir = os.path.isdir(path)
        size = os.path.getsize(path) if is_file else 0
        ext = os.path.splitext(path)[1].lower()
        return cls(
            path=path,
            relative_path=rel_path,
            is_file=is_file,
            is_dir=is_dir,
            size=size,
            extension=ext
        )


class GitIgnoreParser:
    def __init__(self, patterns: List[str]):
        self.patterns = patterns
        self.compiled_patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> List[Tuple[bool, str, Optional[re.Pattern]]]:
        compiled = []
        for pattern in self.patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue
            negated = False
            if pattern.startswith('!'):
                negated = True
                pattern = pattern[1:]
            if pattern.startswith('/'):
                pattern = pattern[1:]
            if pattern.endswith('/'):
                pattern = pattern[:-1]
                compiled.append((negated, pattern, None))
            else:
                try:
                    regex = self._pattern_to_regex(pattern)
                    compiled.append((negated, pattern, re.compile(regex)))
                except re.error:
                    compiled.append((negated, pattern, None))
        return compiled
    
    def _pattern_to_regex(self, pattern: str) -> str:
        regex = ''
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == '*':
                if i + 1 < len(pattern) and pattern[i + 1] == '*':
                    regex += '.*'
                    i += 1
                else:
                    regex += '[^/]*'
            elif c == '?':
                regex += '[^/]'
            elif c == '[':
                j = i + 1
                while j < len(pattern) and pattern[j] != ']':
                    j += 1
                regex += pattern[i:j+1]
                i = j
            elif c in '.^$+{}|()\\':
                regex += '\\' + c
            else:
                regex += c
            i += 1
        return f'^{regex}$|^{regex}/|/{regex}$|/{regex}/'
    
    def should_ignore(self, path: str) -> bool:
        path = path.replace('\\', '/')
        ignored = False
        for negated, pattern, regex in self.compiled_patterns:
            matched = False
            if regex:
                matched = bool(regex.search('/' + path + '/'))
            else:
                matched = fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)
            if matched:
                ignored = not negated
        return ignored
    
    @classmethod
    def from_file(cls, filepath: str) -> 'GitIgnoreParser':
        patterns = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                patterns = f.readlines()
        return cls(patterns)
    
    @classmethod
    def from_directory(cls, directory: str) -> 'GitIgnoreParser':
        gitignore_path = os.path.join(directory, '.gitignore')
        return cls.from_file(gitignore_path)


DEFAULT_IGNORE_PATTERNS = [
    '.git',
    '.git/',
    '__pycache__',
    '__pycache__/',
    '*.pyc',
    '*.pyo',
    '.pytest_cache',
    '.mypy_cache',
    '.venv',
    'venv',
    'node_modules',
    '.idea',
    '.vscode',
    '*.egg-info',
    'dist',
    'build',
    '.tox',
    '.coverage',
    'htmlcov',
    '.DS_Store',
    'Thumbs.db',
]


class DirectoryWalker:
    def __init__(self, root: str, 
                 use_gitignore: bool = True,
                 extra_ignore_patterns: Optional[List[str]] = None,
                 include_hidden: bool = False,
                 extensions: Optional[List[str]] = None,
                 exclude_extensions: Optional[List[str]] = None,
                 max_depth: Optional[int] = None,
                 skip_binary: bool = False):
        self.root = os.path.abspath(root)
        self.use_gitignore = use_gitignore
        self.include_hidden = include_hidden
        self.extensions = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                             for ext in (extensions or []))
        self.exclude_extensions = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                                       for ext in (exclude_extensions or []))
        self.max_depth = max_depth
        self.skip_binary = skip_binary
        ignore_patterns = list(DEFAULT_IGNORE_PATTERNS)
        if extra_ignore_patterns:
            ignore_patterns.extend(extra_ignore_patterns)
        self.ignore_parser = GitIgnoreParser(ignore_patterns)
        self.gitignore_parsers: dict = {}
        
    def _load_gitignore(self, directory: str) -> Optional[GitIgnoreParser]:
        if not self.use_gitignore:
            return None
        if directory not in self.gitignore_parsers:
            gitignore_path = os.path.join(directory, '.gitignore')
            if os.path.exists(gitignore_path):
                self.gitignore_parsers[directory] = GitIgnoreParser.from_file(gitignore_path)
            else:
                self.gitignore_parsers[directory] = None
        return self.gitignore_parsers[directory]
    
    def _should_ignore(self, path: str, is_dir: bool = False) -> bool:
        rel_path = os.path.relpath(path, self.root)
        name = os.path.basename(path)
        if not self.include_hidden and name.startswith('.') and name != '.':
            return True
        if self.ignore_parser.should_ignore(rel_path):
            return True
        current = self.root
        for part in Path(rel_path).parts[:-1]:
            current = os.path.join(current, part)
            parser = self._load_gitignore(current)
            if parser:
                sub_rel = os.path.relpath(path, current)
                if parser.should_ignore(sub_rel):
                    return True
        return False
    
    def _matches_extension_filter(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        if self.exclude_extensions and ext in self.exclude_extensions:
            return False
        if self.extensions:
            return ext in self.extensions
        return True
    
    def walk(self) -> Iterator[str]:
        for entry in self.walk_entries():
            if entry.is_file:
                yield entry.path
    
    def walk_entries(self) -> Iterator[FileEntry]:
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel_dir = os.path.relpath(dirpath, self.root)
            if self.max_depth is not None:
                depth = 0 if rel_dir == '.' else rel_dir.count(os.sep) + 1
                if depth > self.max_depth:
                    dirnames.clear()
                    continue
            dirnames[:] = [d for d in dirnames 
                          if not self._should_ignore(os.path.join(dirpath, d), is_dir=True)]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if self._should_ignore(filepath):
                    continue
                if not self._matches_extension_filter(filepath):
                    continue
                if self.skip_binary:
                    try:
                        if is_binary_file(filepath):
                            continue
                    except (IOError, OSError):
                        continue
                yield FileEntry.from_path(filepath, self.root)
    
    def walk_dirs(self) -> Iterator[str]:
        for dirpath, dirnames, _ in os.walk(self.root):
            rel_dir = os.path.relpath(dirpath, self.root)
            if self.max_depth is not None:
                depth = 0 if rel_dir == '.' else rel_dir.count(os.sep) + 1
                if depth > self.max_depth:
                    dirnames.clear()
                    continue
            dirnames[:] = [d for d in dirnames 
                          if not self._should_ignore(os.path.join(dirpath, d), is_dir=True)]
            for dirname in dirnames:
                yield os.path.join(dirpath, dirname)
    
    def count_files(self) -> int:
        return sum(1 for _ in self.walk())
    
    def get_all_files(self) -> List[str]:
        return list(self.walk())
    
    def get_all_entries(self) -> List[FileEntry]:
        return list(self.walk_entries())


def walk_directory(root: str,
                   extensions: Optional[List[str]] = None,
                   exclude_dirs: Optional[List[str]] = None,
                   max_depth: Optional[int] = None) -> Iterator[str]:
    walker = DirectoryWalker(
        root=root,
        extensions=extensions,
        extra_ignore_patterns=exclude_dirs,
        max_depth=max_depth
    )
    yield from walker.walk()


def read_file_lines(filepath: str, encoding: Optional[str] = None) -> List[str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    if is_binary_file(filepath):
        raise ValueError(f"Cannot read binary file: {filepath}")
    if encoding is None:
        encoding = get_file_encoding(filepath)
    with open(filepath, 'r', encoding=encoding, errors='replace') as f:
        content = f.read()
    if content.endswith('\n'):
        lines = content[:-1].split('\n')
    else:
        lines = content.split('\n') if content else []
    return lines


def read_file_lines_with_endings(filepath: str, encoding: Optional[str] = None) -> List[str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    if is_binary_file(filepath):
        raise ValueError(f"Cannot read binary file: {filepath}")
    if encoding is None:
        encoding = get_file_encoding(filepath)
    with open(filepath, 'r', encoding=encoding, errors='replace', newline='') as f:
        lines = f.readlines()
    return lines


def compare_files(file1: str, file2: str) -> Tuple[List[str], List[str]]:
    lines1 = read_file_lines(file1)
    lines2 = read_file_lines(file2)
    return lines1, lines2


def file_exists(filepath: str) -> bool:
    return os.path.isfile(filepath)


def get_file_info(filepath: str) -> dict:
    info = FileTypeInfo(filepath)
    return info.to_dict()


class FileComparator:
    def __init__(self, file1: str, file2: str):
        self.file1 = file1
        self.file2 = file2
        self.info1 = FileTypeInfo(file1)
        self.info2 = FileTypeInfo(file2)
        
    def can_compare(self) -> Tuple[bool, str]:
        if not self.info1.exists:
            return False, f"File not found: {self.file1}"
        if not self.info2.exists:
            return False, f"File not found: {self.file2}"
        if not self.info1.is_file:
            return False, f"Not a file: {self.file1}"
        if not self.info2.is_file:
            return False, f"Not a file: {self.file2}"
        if self.info1.is_binary:
            return False, f"Binary file: {self.file1}"
        if self.info2.is_binary:
            return False, f"Binary file: {self.file2}"
        return True, ""
    
    def get_lines(self) -> Tuple[List[str], List[str]]:
        can, error = self.can_compare()
        if not can:
            raise ValueError(error)
        return compare_files(self.file1, self.file2)
    
    def are_identical(self) -> bool:
        can, _ = self.can_compare()
        if not can:
            return False
        if self.info1.size != self.info2.size:
            return False
        lines1, lines2 = self.get_lines()
        return lines1 == lines2


class DirectoryComparator:
    def __init__(self, dir1: str, dir2: str, **walker_kwargs):
        self.dir1 = os.path.abspath(dir1)
        self.dir2 = os.path.abspath(dir2)
        self.walker_kwargs = walker_kwargs
        
    def get_file_sets(self) -> Tuple[Set[str], Set[str]]:
        walker1 = DirectoryWalker(self.dir1, **self.walker_kwargs)
        walker2 = DirectoryWalker(self.dir2, **self.walker_kwargs)
        files1 = set(e.relative_path for e in walker1.walk_entries())
        files2 = set(e.relative_path for e in walker2.walk_entries())
        return files1, files2
    
    def compare(self) -> dict:
        files1, files2 = self.get_file_sets()
        only_in_first = files1 - files2
        only_in_second = files2 - files1
        common = files1 & files2
        modified = set()
        identical = set()
        for rel_path in common:
            path1 = os.path.join(self.dir1, rel_path)
            path2 = os.path.join(self.dir2, rel_path)
            comparator = FileComparator(path1, path2)
            can, _ = comparator.can_compare()
            if can and comparator.are_identical():
                identical.add(rel_path)
            else:
                modified.add(rel_path)
        return {
            'only_in_first': sorted(only_in_first),
            'only_in_second': sorted(only_in_second),
            'modified': sorted(modified),
            'identical': sorted(identical),
        }
