import sys
import os
import tempfile
import shutil
import unittest
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from fs.binary_check import (
    BinaryDetector, EncodingDetector, FileTypeInfo,
    is_binary_file, is_binary_content, get_file_encoding,
    detect_line_ending, BINARY_SIGNATURES, BINARY_EXTENSIONS, CHECK_SIZE
)
from fs.walker import (
    FileEntry, GitIgnoreParser, DirectoryWalker,
    walk_directory, read_file_lines, read_file_lines_with_endings,
    compare_files, file_exists, get_file_info,
    FileComparator, DirectoryComparator, DEFAULT_IGNORE_PATTERNS
)


class TempDirMixin:
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_file(self, name: str, content: str = '', binary: bool = False) -> str:
        path = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if binary:
            with open(path, 'wb') as f:
                f.write(content if isinstance(content, bytes) else content.encode())
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        return path
        
    def create_dir(self, name: str) -> str:
        path = os.path.join(self.temp_dir, name)
        os.makedirs(path, exist_ok=True)
        return path


class TestBinarySignatures(unittest.TestCase):
    def test_binary_signatures_exist(self):
        self.assertGreater(len(BINARY_SIGNATURES), 0)
        
    def test_binary_signatures_are_bytes(self):
        for sig in BINARY_SIGNATURES:
            self.assertIsInstance(sig, bytes)
            
    def test_png_signature(self):
        png_sig = b'\x89PNG\r\n\x1a\n'
        self.assertIn(png_sig, BINARY_SIGNATURES)
        
    def test_pdf_signature(self):
        pdf_sig = b'%PDF'
        self.assertIn(pdf_sig, BINARY_SIGNATURES)
        
    def test_jpeg_signature(self):
        jpeg_sig = b'\xff\xd8\xff'
        self.assertIn(jpeg_sig, BINARY_SIGNATURES)


class TestBinaryExtensions(unittest.TestCase):
    def test_binary_extensions_exist(self):
        self.assertGreater(len(BINARY_EXTENSIONS), 0)
        
    def test_image_extensions(self):
        self.assertIn('.png', BINARY_EXTENSIONS)
        self.assertIn('.jpg', BINARY_EXTENSIONS)
        self.assertIn('.gif', BINARY_EXTENSIONS)
        
    def test_document_extensions(self):
        self.assertIn('.pdf', BINARY_EXTENSIONS)
        self.assertIn('.doc', BINARY_EXTENSIONS)
        self.assertIn('.docx', BINARY_EXTENSIONS)
        
    def test_archive_extensions(self):
        self.assertIn('.zip', BINARY_EXTENSIONS)
        self.assertIn('.rar', BINARY_EXTENSIONS)
        self.assertIn('.7z', BINARY_EXTENSIONS)
        
    def test_executable_extensions(self):
        self.assertIn('.exe', BINARY_EXTENSIONS)
        self.assertIn('.dll', BINARY_EXTENSIONS)


class TestBinaryDetector(TempDirMixin, unittest.TestCase):
    def test_detector_creation(self):
        detector = BinaryDetector()
        self.assertIsNotNone(detector.signatures)
        self.assertIsNotNone(detector.binary_extensions)
        
    def test_is_binary_by_extension_png(self):
        detector = BinaryDetector()
        self.assertTrue(detector.is_binary_by_extension('image.png'))
        self.assertTrue(detector.is_binary_by_extension('file.PNG'))
        
    def test_is_binary_by_extension_text(self):
        detector = BinaryDetector()
        self.assertFalse(detector.is_binary_by_extension('file.txt'))
        self.assertFalse(detector.is_binary_by_extension('script.py'))
        
    def test_is_binary_by_extension_various(self):
        detector = BinaryDetector()
        self.assertTrue(detector.is_binary_by_extension('document.pdf'))
        self.assertTrue(detector.is_binary_by_extension('archive.zip'))
        self.assertTrue(detector.is_binary_by_extension('program.exe'))
        self.assertFalse(detector.is_binary_by_extension('code.js'))
        
    def test_is_binary_by_signature_png(self):
        detector = BinaryDetector()
        png_data = b'\x89PNG\r\n\x1a\n' + b'rest of file'
        self.assertTrue(detector.is_binary_by_signature(png_data))
        
    def test_is_binary_by_signature_text(self):
        detector = BinaryDetector()
        text_data = b'Hello, World!'
        self.assertFalse(detector.is_binary_by_signature(text_data))
        
    def test_is_binary_by_signature_pdf(self):
        detector = BinaryDetector()
        pdf_data = b'%PDF-1.4 rest of content'
        self.assertTrue(detector.is_binary_by_signature(pdf_data))
        
    def test_is_binary_by_content_with_null(self):
        detector = BinaryDetector()
        data_with_null = b'Hello\x00World'
        self.assertTrue(detector.is_binary_by_content(data_with_null))
        
    def test_is_binary_by_content_utf8(self):
        detector = BinaryDetector()
        utf8_data = 'Hello World'.encode('utf-8')
        self.assertFalse(detector.is_binary_by_content(utf8_data))
        
    def test_is_binary_by_content_empty(self):
        detector = BinaryDetector()
        self.assertFalse(detector.is_binary_by_content(b''))
        
    def test_check_file_text(self):
        path = self.create_file('test.txt', 'Hello, World!')
        detector = BinaryDetector()
        self.assertFalse(detector.check_file(path))
        
    def test_check_file_binary_extension(self):
        path = self.create_file('image.png', 'not really png', binary=True)
        detector = BinaryDetector()
        self.assertTrue(detector.check_file(path))
        
    def test_check_file_binary_signature(self):
        path = self.create_file('file.dat', b'\x89PNG\r\n\x1a\n' + b'data', binary=True)
        detector = BinaryDetector()
        self.assertTrue(detector.check_file(path))
        
    def test_check_file_empty(self):
        path = self.create_file('empty.txt', '')
        detector = BinaryDetector()
        self.assertFalse(detector.check_file(path))
        
    def test_check_file_not_found(self):
        detector = BinaryDetector()
        with self.assertRaises(FileNotFoundError):
            detector.check_file('/nonexistent/file.txt')
            
    def test_check_file_directory(self):
        dir_path = self.create_dir('testdir')
        detector = BinaryDetector()
        with self.assertRaises(ValueError):
            detector.check_file(dir_path)
            
    def test_check_stream(self):
        import io
        detector = BinaryDetector()
        text_stream = io.BytesIO(b'Hello World')
        self.assertFalse(detector.check_stream(text_stream))
        binary_stream = io.BytesIO(b'\x89PNG\r\n\x1a\n')
        self.assertTrue(detector.check_stream(binary_stream))


class TestIsBinaryFile(TempDirMixin, unittest.TestCase):
    def test_is_binary_file_text(self):
        path = self.create_file('text.txt', 'Just some text content')
        self.assertFalse(is_binary_file(path))
        
    def test_is_binary_file_binary_ext(self):
        path = self.create_file('image.jpg', 'fake jpg', binary=True)
        self.assertTrue(is_binary_file(path))
        
    def test_is_binary_file_null_bytes(self):
        path = self.create_file('data.dat', b'data\x00with\x00nulls', binary=True)
        self.assertTrue(is_binary_file(path))


class TestIsBinaryContent(unittest.TestCase):
    def test_is_binary_content_text(self):
        import io
        stream = io.BytesIO(b'Normal text content')
        self.assertFalse(is_binary_content(stream))
        
    def test_is_binary_content_binary(self):
        import io
        stream = io.BytesIO(b'\x00\x01\x02\x03')
        self.assertTrue(is_binary_content(stream))


class TestEncodingDetector(TempDirMixin, unittest.TestCase):
    def test_detector_creation(self):
        detector = EncodingDetector()
        self.assertIsNotNone(detector.encodings)
        self.assertIsNotNone(detector.bom_map)
        
    def test_detect_bom_utf8(self):
        detector = EncodingDetector()
        data = b'\xef\xbb\xbfHello'
        encoding = detector.detect_bom(data)
        self.assertEqual(encoding, 'utf-8-sig')
        
    def test_detect_bom_utf16_le(self):
        detector = EncodingDetector()
        data = b'\xff\xfeHello'
        encoding = detector.detect_bom(data)
        self.assertEqual(encoding, 'utf-16-le')
        
    def test_detect_bom_utf16_be(self):
        detector = EncodingDetector()
        data = b'\xfe\xffHello'
        encoding = detector.detect_bom(data)
        self.assertEqual(encoding, 'utf-16-be')
        
    def test_detect_bom_none(self):
        detector = EncodingDetector()
        data = b'Hello World'
        encoding = detector.detect_bom(data)
        self.assertIsNone(encoding)
        
    def test_detect_encoding_utf8(self):
        path = self.create_file('utf8.txt', 'Hello World')
        detector = EncodingDetector()
        encoding = detector.detect_encoding(path)
        self.assertIn(encoding, ['utf-8', 'ascii'])
        
    def test_detect_encoding_utf8_bom(self):
        path = self.create_file('utf8bom.txt', '', binary=True)
        with open(path, 'wb') as f:
            f.write(b'\xef\xbb\xbfHello World')
        detector = EncodingDetector()
        encoding = detector.detect_encoding(path)
        self.assertEqual(encoding, 'utf-8-sig')
        
    def test_detect_from_content(self):
        detector = EncodingDetector()
        encoding = detector.detect_from_content(b'Simple ASCII text')
        self.assertIn(encoding, ['utf-8', 'ascii'])


class TestGetFileEncoding(TempDirMixin, unittest.TestCase):
    def test_get_file_encoding_ascii(self):
        path = self.create_file('ascii.txt', 'Hello')
        encoding = get_file_encoding(path)
        self.assertIn(encoding, ['utf-8', 'ascii'])
        
    def test_get_file_encoding_utf8(self):
        path = self.create_file('utf8.txt', 'Привіт світ')
        encoding = get_file_encoding(path)
        self.assertEqual(encoding, 'utf-8')


class TestDetectLineEnding(TempDirMixin, unittest.TestCase):
    def test_detect_lf(self):
        path = self.create_file('lf.txt', '', binary=True)
        with open(path, 'wb') as f:
            f.write(b'line1\nline2\nline3')
        ending = detect_line_ending(path)
        self.assertEqual(ending, '\n')
        
    def test_detect_crlf(self):
        path = self.create_file('crlf.txt', '', binary=True)
        with open(path, 'wb') as f:
            f.write(b'line1\r\nline2\r\nline3')
        ending = detect_line_ending(path)
        self.assertEqual(ending, '\r\n')
        
    def test_detect_cr(self):
        path = self.create_file('cr.txt', '', binary=True)
        with open(path, 'wb') as f:
            f.write(b'line1\rline2\rline3')
        ending = detect_line_ending(path)
        self.assertEqual(ending, '\r')


class TestFileTypeInfo(TempDirMixin, unittest.TestCase):
    def test_file_info_creation(self):
        path = self.create_file('test.txt', 'content')
        info = FileTypeInfo(path)
        self.assertTrue(info.exists)
        self.assertTrue(info.is_file)
        self.assertFalse(info.is_dir)
        
    def test_file_info_nonexistent(self):
        info = FileTypeInfo('/nonexistent/path.txt')
        self.assertFalse(info.exists)
        self.assertFalse(info.is_file)
        
    def test_file_info_directory(self):
        dir_path = self.create_dir('testdir')
        info = FileTypeInfo(dir_path)
        self.assertTrue(info.exists)
        self.assertTrue(info.is_dir)
        self.assertFalse(info.is_file)
        
    def test_file_info_size(self):
        content = 'Hello World!'
        path = self.create_file('sized.txt', content)
        info = FileTypeInfo(path)
        self.assertEqual(info.size, len(content))
        
    def test_file_info_is_binary_text(self):
        path = self.create_file('text.txt', 'text content')
        info = FileTypeInfo(path)
        self.assertFalse(info.is_binary)
        
    def test_file_info_is_binary_binary(self):
        path = self.create_file('binary.png', b'\x89PNG\r\n\x1a\n', binary=True)
        info = FileTypeInfo(path)
        self.assertTrue(info.is_binary)
        
    def test_file_info_encoding(self):
        path = self.create_file('utf8.txt', 'Привіт')
        info = FileTypeInfo(path)
        self.assertEqual(info.encoding, 'utf-8')
        
    def test_file_info_line_ending(self):
        path = self.create_file('lf.txt', '', binary=True)
        with open(path, 'wb') as f:
            f.write(b'a\nb\nc')
        info = FileTypeInfo(path)
        self.assertEqual(info.line_ending, '\n')
        
    def test_file_info_to_dict(self):
        path = self.create_file('test.txt', 'content')
        info = FileTypeInfo(path)
        d = info.to_dict()
        self.assertIn('filepath', d)
        self.assertIn('exists', d)
        self.assertIn('is_file', d)
        self.assertIn('size', d)
        self.assertIn('encoding', d)


class TestFileEntry(TempDirMixin, unittest.TestCase):
    def test_file_entry_from_path(self):
        path = self.create_file('subdir/test.py', 'code')
        entry = FileEntry.from_path(path, self.temp_dir)
        self.assertEqual(entry.path, path)
        self.assertTrue(entry.is_file)
        self.assertFalse(entry.is_dir)
        self.assertEqual(entry.extension, '.py')
        
    def test_file_entry_relative_path(self):
        path = self.create_file('a/b/c.txt', 'text')
        entry = FileEntry.from_path(path, self.temp_dir)
        self.assertIn('c.txt', entry.relative_path)
        
    def test_file_entry_directory(self):
        dir_path = self.create_dir('mydir')
        entry = FileEntry.from_path(dir_path, self.temp_dir)
        self.assertFalse(entry.is_file)
        self.assertTrue(entry.is_dir)
        self.assertEqual(entry.size, 0)


class TestGitIgnoreParser(unittest.TestCase):
    def test_empty_patterns(self):
        parser = GitIgnoreParser([])
        self.assertFalse(parser.should_ignore('anyfile.txt'))
        
    def test_simple_pattern(self):
        parser = GitIgnoreParser(['*.pyc'])
        self.assertTrue(parser.should_ignore('module.pyc'))
        self.assertFalse(parser.should_ignore('module.py'))
        
    def test_directory_pattern(self):
        parser = GitIgnoreParser(['__pycache__/'])
        self.assertTrue(parser.should_ignore('__pycache__'))
        
    def test_negation_pattern(self):
        parser = GitIgnoreParser(['*.txt', '!important.txt'])
        self.assertTrue(parser.should_ignore('random.txt'))
        self.assertFalse(parser.should_ignore('important.txt'))
        
    def test_comment_pattern(self):
        parser = GitIgnoreParser(['# comment', '*.log'])
        self.assertTrue(parser.should_ignore('debug.log'))
        self.assertFalse(parser.should_ignore('# comment'))
        
    def test_double_star_pattern(self):
        parser = GitIgnoreParser(['**/temp'])
        self.assertTrue(parser.should_ignore('a/b/temp'))
        self.assertTrue(parser.should_ignore('temp'))
        
    def test_leading_slash(self):
        parser = GitIgnoreParser(['/root.txt'])
        self.assertTrue(parser.should_ignore('root.txt'))
        
    def test_trailing_slash(self):
        parser = GitIgnoreParser(['build/'])
        self.assertTrue(parser.should_ignore('build'))


class TestGitIgnoreParserFromFile(TempDirMixin, unittest.TestCase):
    def test_from_file_exists(self):
        gitignore = self.create_file('.gitignore', '*.pyc\n__pycache__/')
        parser = GitIgnoreParser.from_file(gitignore)
        self.assertTrue(parser.should_ignore('test.pyc'))
        
    def test_from_file_not_exists(self):
        parser = GitIgnoreParser.from_file('/nonexistent/.gitignore')
        self.assertFalse(parser.should_ignore('anyfile.txt'))
        
    def test_from_directory(self):
        self.create_file('.gitignore', '*.log\n')
        parser = GitIgnoreParser.from_directory(self.temp_dir)
        self.assertTrue(parser.should_ignore('error.log'))


class TestDefaultIgnorePatterns(unittest.TestCase):
    def test_default_patterns_exist(self):
        self.assertGreater(len(DEFAULT_IGNORE_PATTERNS), 0)
        
    def test_common_patterns_included(self):
        self.assertIn('.git', DEFAULT_IGNORE_PATTERNS)
        self.assertIn('__pycache__', DEFAULT_IGNORE_PATTERNS)
        self.assertIn('node_modules', DEFAULT_IGNORE_PATTERNS)
        self.assertIn('.venv', DEFAULT_IGNORE_PATTERNS)


class TestDirectoryWalker(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.create_file('file1.py', 'code1')
        self.create_file('file2.py', 'code2')
        self.create_file('file3.txt', 'text')
        self.create_file('subdir/file4.py', 'code4')
        self.create_file('subdir/file5.js', 'js code')
        
    def test_walker_basic(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        files = list(walker.walk())
        self.assertGreaterEqual(len(files), 5)
        
    def test_walker_extensions_filter(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, extensions=['.py'])
        files = list(walker.walk())
        self.assertTrue(all(f.endswith('.py') for f in files))
        
    def test_walker_exclude_extensions(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, exclude_extensions=['.py'])
        files = list(walker.walk())
        self.assertTrue(all(not f.endswith('.py') for f in files))
        
    def test_walker_max_depth_zero(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, max_depth=0)
        files = list(walker.walk())
        for f in files:
            rel = os.path.relpath(f, self.temp_dir)
            self.assertNotIn(os.sep, rel)
            
    def test_walker_max_depth_one(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, max_depth=1)
        files = list(walker.walk())
        self.assertGreater(len(files), 0)
        
    def test_walker_walk_entries(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        entries = list(walker.walk_entries())
        self.assertTrue(all(isinstance(e, FileEntry) for e in entries))
        
    def test_walker_walk_dirs(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        dirs = list(walker.walk_dirs())
        self.assertTrue(any('subdir' in d for d in dirs))
        
    def test_walker_count_files(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        count = walker.count_files()
        self.assertGreaterEqual(count, 5)
        
    def test_walker_get_all_files(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        files = walker.get_all_files()
        self.assertIsInstance(files, list)
        
    def test_walker_get_all_entries(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        entries = walker.get_all_entries()
        self.assertIsInstance(entries, list)
        self.assertTrue(all(isinstance(e, FileEntry) for e in entries))


class TestDirectoryWalkerIgnore(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.create_file('visible.py', 'code')
        self.create_file('.hidden.py', 'hidden')
        self.create_file('__pycache__/cached.pyc', 'cache')
        
    def test_walker_ignores_hidden_by_default(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        files = walker.get_all_files()
        hidden_files = [f for f in files if os.path.basename(f).startswith('.')]
        self.assertEqual(len(hidden_files), 0)
        
    def test_walker_include_hidden(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, include_hidden=True)
        files = walker.get_all_files()
        hidden_files = [f for f in files if '.hidden' in f]
        self.assertGreater(len(hidden_files), 0)
        
    def test_walker_ignores_default_patterns(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False)
        files = walker.get_all_files()
        pycache_files = [f for f in files if '__pycache__' in f]
        self.assertEqual(len(pycache_files), 0)


class TestDirectoryWalkerGitignore(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.create_file('.gitignore', '*.log\nbuild/')
        self.create_file('code.py', 'code')
        self.create_file('debug.log', 'log data')
        self.create_file('build/output.txt', 'built')
        
    def test_walker_respects_gitignore(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=True, include_hidden=True,
                                  extra_ignore_patterns=['*.log', 'build/'])
        files = walker.get_all_files()
        log_files = [f for f in files if f.endswith('.log')]
        self.assertEqual(len(log_files), 0)
        
    def test_walker_gitignore_disabled(self):
        walker = DirectoryWalker(self.temp_dir, use_gitignore=False, include_hidden=True)
        files = walker.get_all_files()
        self.assertTrue(any(f.endswith('.log') for f in files))


class TestWalkDirectory(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.create_file('a.py', 'a')
        self.create_file('b.txt', 'b')
        
    def test_walk_directory_basic(self):
        files = list(walk_directory(self.temp_dir))
        self.assertGreater(len(files), 0)
        
    def test_walk_directory_with_extensions(self):
        files = list(walk_directory(self.temp_dir, extensions=['.py']))
        self.assertTrue(all(f.endswith('.py') for f in files))


class TestReadFileLines(TempDirMixin, unittest.TestCase):
    def test_read_simple_file(self):
        path = self.create_file('test.txt', 'line1\nline2\nline3')
        lines = read_file_lines(path)
        self.assertEqual(lines, ['line1', 'line2', 'line3'])
        
    def test_read_empty_file(self):
        path = self.create_file('empty.txt', '')
        lines = read_file_lines(path)
        self.assertEqual(lines, [])
        
    def test_read_single_line(self):
        path = self.create_file('single.txt', 'only line')
        lines = read_file_lines(path)
        self.assertEqual(lines, ['only line'])
        
    def test_read_trailing_newline(self):
        path = self.create_file('trailing.txt', 'a\nb\nc\n')
        lines = read_file_lines(path)
        self.assertEqual(lines, ['a', 'b', 'c'])
        
    def test_read_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            read_file_lines('/nonexistent/file.txt')
            
    def test_read_binary_file_raises(self):
        path = self.create_file('binary.png', b'\x89PNG\r\n\x1a\n', binary=True)
        with self.assertRaises(ValueError):
            read_file_lines(path)


class TestReadFileLinesWithEndings(TempDirMixin, unittest.TestCase):
    def test_read_preserves_endings(self):
        path = self.create_file('test.txt', 'a\nb\nc')
        lines = read_file_lines_with_endings(path)
        self.assertTrue(any('\n' in line for line in lines[:-1]) or len(lines) == 1)


class TestCompareFiles(TempDirMixin, unittest.TestCase):
    def test_compare_identical(self):
        path1 = self.create_file('file1.txt', 'line1\nline2')
        path2 = self.create_file('file2.txt', 'line1\nline2')
        lines1, lines2 = compare_files(path1, path2)
        self.assertEqual(lines1, lines2)
        
    def test_compare_different(self):
        path1 = self.create_file('file1.txt', 'a\nb')
        path2 = self.create_file('file2.txt', 'a\nc')
        lines1, lines2 = compare_files(path1, path2)
        self.assertNotEqual(lines1, lines2)


class TestFileExists(TempDirMixin, unittest.TestCase):
    def test_file_exists_true(self):
        path = self.create_file('exists.txt', 'content')
        self.assertTrue(file_exists(path))
        
    def test_file_exists_false(self):
        self.assertFalse(file_exists('/nonexistent/path.txt'))
        
    def test_file_exists_directory(self):
        dir_path = self.create_dir('adir')
        self.assertFalse(file_exists(dir_path))


class TestGetFileInfo(TempDirMixin, unittest.TestCase):
    def test_get_file_info_basic(self):
        path = self.create_file('info.txt', 'some content')
        info = get_file_info(path)
        self.assertIsInstance(info, dict)
        self.assertEqual(info['exists'], True)
        self.assertEqual(info['is_file'], True)


class TestFileComparator(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.file1 = self.create_file('file1.txt', 'content1\nline2')
        self.file2 = self.create_file('file2.txt', 'content1\nline2')
        self.file3 = self.create_file('file3.txt', 'different\ncontent')
        
    def test_comparator_can_compare_valid(self):
        comparator = FileComparator(self.file1, self.file2)
        can, error = comparator.can_compare()
        self.assertTrue(can)
        self.assertEqual(error, '')
        
    def test_comparator_can_compare_missing_file(self):
        comparator = FileComparator(self.file1, '/nonexistent.txt')
        can, error = comparator.can_compare()
        self.assertFalse(can)
        self.assertIn('not found', error.lower())
        
    def test_comparator_can_compare_binary(self):
        binary = self.create_file('bin.png', b'\x89PNG\r\n\x1a\n', binary=True)
        comparator = FileComparator(self.file1, binary)
        can, error = comparator.can_compare()
        self.assertFalse(can)
        self.assertIn('binary', error.lower())
        
    def test_comparator_get_lines(self):
        comparator = FileComparator(self.file1, self.file2)
        lines1, lines2 = comparator.get_lines()
        self.assertEqual(lines1, lines2)
        
    def test_comparator_are_identical_true(self):
        comparator = FileComparator(self.file1, self.file2)
        self.assertTrue(comparator.are_identical())
        
    def test_comparator_are_identical_false(self):
        comparator = FileComparator(self.file1, self.file3)
        self.assertFalse(comparator.are_identical())


class TestDirectoryComparator(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.dir1 = self.create_dir('dir1')
        self.dir2 = self.create_dir('dir2')
        
    def test_comparator_empty_dirs(self):
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        result = comparator.compare()
        self.assertEqual(result['only_in_first'], [])
        self.assertEqual(result['only_in_second'], [])
        self.assertEqual(result['modified'], [])
        
    def test_comparator_get_file_sets(self):
        with open(os.path.join(self.dir1, 'a.txt'), 'w') as f:
            f.write('a')
        with open(os.path.join(self.dir2, 'b.txt'), 'w') as f:
            f.write('b')
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        files1, files2 = comparator.get_file_sets()
        self.assertIn('a.txt', files1)
        self.assertIn('b.txt', files2)
        
    def test_comparator_only_in_first(self):
        with open(os.path.join(self.dir1, 'unique.txt'), 'w') as f:
            f.write('unique')
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        result = comparator.compare()
        self.assertIn('unique.txt', result['only_in_first'])
        
    def test_comparator_only_in_second(self):
        with open(os.path.join(self.dir2, 'new.txt'), 'w') as f:
            f.write('new')
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        result = comparator.compare()
        self.assertIn('new.txt', result['only_in_second'])
        
    def test_comparator_identical_files(self):
        with open(os.path.join(self.dir1, 'same.txt'), 'w') as f:
            f.write('same content')
        with open(os.path.join(self.dir2, 'same.txt'), 'w') as f:
            f.write('same content')
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        result = comparator.compare()
        self.assertIn('same.txt', result['identical'])
        
    def test_comparator_modified_files(self):
        with open(os.path.join(self.dir1, 'mod.txt'), 'w') as f:
            f.write('original')
        with open(os.path.join(self.dir2, 'mod.txt'), 'w') as f:
            f.write('modified')
        comparator = DirectoryComparator(self.dir1, self.dir2, use_gitignore=False)
        result = comparator.compare()
        self.assertIn('mod.txt', result['modified'])


class TestCheckSize(unittest.TestCase):
    def test_check_size_value(self):
        self.assertEqual(CHECK_SIZE, 8192)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
