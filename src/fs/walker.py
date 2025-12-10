import os
import fnmatch
from typing import List, Optional, Iterator, Tuple, Set
from dataclasses import dataclass
from .binary_check import is_binary_file, get_file_encoding, FileTypeInfo


@dataclass
class FileEntry:
    path: str
    relative_path: str
    is_file: bool
    size: int
    extension: str

    @classmethod
    def from_path(cls, path: str, base: str) -> 'FileEntry':
        return cls(path=path, relative_path=os.path.relpath(path, base),
                   is_file=os.path.isfile(path),
                   size=os.path.getsize(path) if os.path.isfile(path) else 0,
                   extension=os.path.splitext(path)[1].lower())


DEFAULT_IGNORE = ['.git', '__pycache__', '*.pyc', '.pytest_cache', '.venv', 'venv',
                  'node_modules', '.idea', '.vscode', 'dist', 'build', '.coverage']


class DirectoryWalker:
    def __init__(self, root: str, use_gitignore: bool = True,
                 extra_ignore_patterns: Optional[List[str]] = None,
                 extensions: Optional[List[str]] = None,
                 max_depth: Optional[int] = None, skip_binary: bool = False):
        self.root = os.path.abspath(root)
        self.max_depth = max_depth
        self.skip_binary = skip_binary
        self.extensions = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                              for ext in (extensions or []))
        self.ignore = DEFAULT_IGNORE + (extra_ignore_patterns or [])

    def _should_ignore(self, path: str) -> bool:
        name = os.path.basename(path)
        rel = os.path.relpath(path, self.root)
        if name.startswith('.') and name != '.':
            return True
        for pat in self.ignore:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat):
                return True
        return False

    def walk(self) -> Iterator[str]:
        for e in self.walk_entries():
            yield e.path

    def walk_entries(self) -> Iterator[FileEntry]:
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel = os.path.relpath(dirpath, self.root)
            if self.max_depth is not None:
                depth = 0 if rel == '.' else rel.count(os.sep) + 1
                if depth > self.max_depth:
                    dirnames.clear()
                    continue
            dirnames[:] = [d for d in dirnames if not self._should_ignore(os.path.join(dirpath, d))]
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                if self._should_ignore(fp):
                    continue
                ext = os.path.splitext(fp)[1].lower()
                if self.extensions and ext not in self.extensions:
                    continue
                if self.skip_binary:
                    try:
                        if is_binary_file(fp):
                            continue
                    except (IOError, OSError):
                        continue
                yield FileEntry.from_path(fp, self.root)

    def get_all_files(self) -> List[str]:
        return list(self.walk())


def read_file_lines(filepath: str, encoding: Optional[str] = None) -> List[str]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    if is_binary_file(filepath):
        raise ValueError(f"Cannot read binary file: {filepath}")
    enc = encoding or get_file_encoding(filepath)
    with open(filepath, 'r', encoding=enc, errors='replace') as f:
        content = f.read()
    return content[:-1].split('\n') if content.endswith('\n') else (content.split('\n') if content else [])


class FileComparator:
    def __init__(self, file1: str, file2: str):
        self.file1, self.file2 = file1, file2
        self.info1, self.info2 = FileTypeInfo(file1), FileTypeInfo(file2)

    def can_compare(self) -> Tuple[bool, str]:
        if not self.info1.exists:
            return False, f"File not found: {self.file1}"
        if not self.info2.exists:
            return False, f"File not found: {self.file2}"
        if self.info1.is_binary:
            return False, f"Binary file: {self.file1}"
        if self.info2.is_binary:
            return False, f"Binary file: {self.file2}"
        return True, ""

    def get_lines(self) -> Tuple[List[str], List[str]]:
        ok, err = self.can_compare()
        if not ok:
            raise ValueError(err)
        return read_file_lines(self.file1), read_file_lines(self.file2)

    def are_identical(self) -> bool:
        ok, _ = self.can_compare()
        if not ok or self.info1.size != self.info2.size:
            return False
        l1, l2 = self.get_lines()
        return l1 == l2


class DirectoryComparator:
    def __init__(self, dir1: str, dir2: str, **kw):
        self.dir1, self.dir2 = os.path.abspath(dir1), os.path.abspath(dir2)
        self.kw = kw

    def compare(self) -> dict:
        w1, w2 = DirectoryWalker(self.dir1, **self.kw), DirectoryWalker(self.dir2, **self.kw)
        f1 = set(e.relative_path for e in w1.walk_entries())
        f2 = set(e.relative_path for e in w2.walk_entries())
        common = f1 & f2
        modified, identical = set(), set()
        for rel in common:
            cmp = FileComparator(os.path.join(self.dir1, rel), os.path.join(self.dir2, rel))
            ok, _ = cmp.can_compare()
            (identical if ok and cmp.are_identical() else modified).add(rel)
        return {'only_in_first': sorted(f1 - f2), 'only_in_second': sorted(f2 - f1),
                'modified': sorted(modified), 'identical': sorted(identical)}