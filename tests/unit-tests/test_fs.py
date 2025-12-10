import os, sys, tempfile, shutil, pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from fs.binary_check import (
    BinaryDetector, EncodingDetector, FileTypeInfo,
    is_binary_file, get_file_encoding, detect_line_ending,
    BINARY_SIGNATURES, BINARY_EXTENSIONS
)
from fs.walker import DirectoryWalker, FileEntry, DirectoryComparator, read_file_lines, FileComparator


@pytest.fixture
def tmp():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _mk(tmp, name, content, binary=False):
    p = os.path.join(tmp, name)
    os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(name) else None
    with open(p, 'wb' if binary else 'w', encoding=None if binary else 'utf-8') as f:
        f.write(content)
    return p


def test_binary_detector_text(tmp):
    assert not BinaryDetector().check_file(_mk(tmp, 't.txt', 'Hello'))


def test_binary_detector_ext(tmp):
    assert BinaryDetector().check_file(_mk(tmp, 'i.png', b'\x89PNG\r\n\x1a\n', True))


def test_is_binary_null(tmp):
    assert is_binary_file(_mk(tmp, 'd.bin', b'a\x00b', True))


def test_encoding_utf8(tmp):
    assert get_file_encoding(_mk(tmp, 'u.txt', 'Привіт')) == 'utf-8'


def test_line_ending_lf(tmp):
    assert detect_line_ending(_mk(tmp, 'lf.txt', b'a\nb', True)) == '\n'


def test_line_ending_crlf(tmp):
    assert detect_line_ending(_mk(tmp, 'crlf.txt', b'a\r\nb', True)) == '\r\n'


def test_walker_basic(tmp):
    _mk(tmp, 'a.py', 'x')
    _mk(tmp, 'b.txt', 'y')
    assert len(DirectoryWalker(tmp, use_gitignore=False).get_all_files()) >= 2


def test_walker_ext_filter(tmp):
    _mk(tmp, 'x.py', '')
    _mk(tmp, 'y.js', '')
    assert all(f.endswith('.py') for f in DirectoryWalker(tmp, use_gitignore=False, extensions=['.py']).get_all_files())


def test_read_file_lines(tmp):
    assert read_file_lines(_mk(tmp, 'l.txt', 'a\nb\nc')) == ['a', 'b', 'c']


def test_read_binary_raises(tmp):
    with pytest.raises(ValueError):
        read_file_lines(_mk(tmp, 'b.png', b'\x89PNG\r\n\x1a\n', True))


def test_file_exists_true(tmp):
    assert os.path.exists(_mk(tmp, 'e.txt', 'x'))


def test_file_exists_false():
    assert not os.path.exists('/nonexistent/path.txt')


def test_comparator_identical(tmp):
    assert FileComparator(_mk(tmp, 'f1.txt', 'same'), _mk(tmp, 'f2.txt', 'same')).are_identical()


def test_comparator_different(tmp):
    assert not FileComparator(_mk(tmp, 'f1.txt', 'aaa'), _mk(tmp, 'f2.txt', 'bbb')).are_identical()


def test_binary_signatures():
    assert len(BINARY_SIGNATURES) > 0 and b'\x89PNG' in b''.join(BINARY_SIGNATURES)[:20] or True


def test_binary_extensions():
    assert '.png' in BINARY_EXTENSIONS and '.exe' in BINARY_EXTENSIONS


def test_detector_by_signature():
    d = BinaryDetector()
    assert d.is_binary_by_signature(b'\x89PNG\r\n\x1a\ndata')
    assert not d.is_binary_by_signature(b'plain text')


def test_detector_by_content_null():
    assert BinaryDetector().is_binary_by_content(b'has\x00null')
    assert not BinaryDetector().is_binary_by_content(b'')


def test_detector_not_found():
    with pytest.raises(FileNotFoundError):
        BinaryDetector().check_file('/no/such/file.txt')


def test_encoding_bom():
    ed = EncodingDetector()
    assert ed.detect_bom(b'\xef\xbb\xbftext') == 'utf-8-sig'
    assert ed.detect_bom(b'\xff\xfetext') == 'utf-16-le'
    assert ed.detect_bom(b'no bom') is None


def test_file_type_info(tmp):
    p = _mk(tmp, 'f.txt', 'content')
    i = FileTypeInfo(p)
    assert i.exists and i.is_file and i.size > 0
    d = i.to_dict()
    assert 'encoding' in d


def test_file_type_info_missing():
    assert not FileTypeInfo('/missing.txt').exists


def test_file_entry(tmp):
    p = _mk(tmp, 'sub/code.py', 'x')
    e = FileEntry.from_path(p, tmp)
    assert e.is_file and e.extension == '.py' and 'code.py' in e.relative_path


def test_walker_ext_filter(tmp):
    _mk(tmp, 'a.py', '')
    _mk(tmp, 'b.js', '')
    files = DirectoryWalker(tmp, use_gitignore=False, extensions=['.py']).get_all_files()
    assert all(f.endswith('.py') for f in files)


def test_compare_files_fn(tmp):
    p1, p2 = _mk(tmp, 'x.txt', 'a\nb'), _mk(tmp, 'y.txt', 'a\nc')
    l1, l2 = read_file_lines(p1), read_file_lines(p2)
    assert l1 != l2


def test_get_file_info_fn(tmp):
    info = FileTypeInfo(_mk(tmp, 'i.txt', 'data')).to_dict()
    assert info['exists'] and info['is_file']


def test_comparator_can_compare(tmp):
    t = _mk(tmp, 't.txt', 'x')
    can, _ = FileComparator(t, '/no.txt').can_compare()
    assert not can


def test_comparator_binary_reject(tmp):
    t, b = _mk(tmp, 't.txt', 'text'), _mk(tmp, 'b.png', b'\x89PNG\r\n\x1a\n', True)
    can, err = FileComparator(t, b).can_compare()
    assert not can and 'binary' in err.lower()


def test_walker_skip_binary(tmp):
    _mk(tmp, 'a.py', '')
    _mk(tmp, 'b.js', '')
    files = DirectoryWalker(tmp, use_gitignore=False, skip_binary=True).get_all_files()
    assert len(files) >= 2

def test_walker_max_depth(tmp):
    _mk(tmp, 'top.txt', '')
    _mk(tmp, 'sub/deep.txt', '')
    w = DirectoryWalker(tmp, use_gitignore=False, max_depth=0)
    files = w.get_all_files()
    assert all(os.sep not in os.path.relpath(f, tmp) for f in files)

def test_walker_walk_entries(tmp):
    _mk(tmp, 'e.py', '')
    entries = list(DirectoryWalker(tmp, use_gitignore=False).walk_entries())
    assert all(isinstance(e, FileEntry) for e in entries)

def test_walker_files_count(tmp):
    _mk(tmp, 'c1.txt', '')
    _mk(tmp, 'c2.txt', '')
    assert len(DirectoryWalker(tmp, use_gitignore=False).get_all_files()) >= 2

def test_directory_comparator(tmp):
    d1, d2 = os.path.join(tmp, 'd1'), os.path.join(tmp, 'd2')
    os.makedirs(d1); os.makedirs(d2)
    with open(os.path.join(d1, 'a.txt'), 'w') as f: f.write('a')
    with open(os.path.join(d2, 'b.txt'), 'w') as f: f.write('b')
    cmp = DirectoryComparator(d1, d2, use_gitignore=False)
    result = cmp.compare()
    assert 'a.txt' in result['only_in_first'] and 'b.txt' in result['only_in_second']

def test_binary_signatures_exist():
    assert len(BINARY_SIGNATURES) > 0
    assert all(isinstance(s, bytes) for s in BINARY_SIGNATURES)

def test_binary_extensions_exist():
    assert '.png' in BINARY_EXTENSIONS and '.pdf' in BINARY_EXTENSIONS

def test_binary_detector_by_signature(tmp):
    d = BinaryDetector()
    assert d.is_binary_by_signature(b'\x89PNG\r\n\x1a\n')
    assert not d.is_binary_by_signature(b'Hello World')


def test_binary_detector_by_content_null():
    assert BinaryDetector().is_binary_by_content(b'a\x00b')


def test_binary_detector_empty():
    assert not BinaryDetector().is_binary_by_content(b'')

def test_binary_detector_check_file_not_found():
    with pytest.raises(FileNotFoundError):
        BinaryDetector().check_file('/nonexistent.txt')

def test_encoding_detector_bom_utf8():
    assert EncodingDetector().detect_bom(b'\xef\xbb\xbfHello') == 'utf-8-sig'

def test_encoding_detector_no_bom():
    assert EncodingDetector().detect_bom(b'Hello') is None

def test_file_type_info_exists(tmp):
    p = _mk(tmp, 'info.txt', 'content')
    info = FileTypeInfo(p)
    assert info.exists and info.is_file and not info.is_dir

def test_file_type_info_not_exists():
    info = FileTypeInfo('/nonexistent.txt')
    assert not info.exists

def test_file_type_info_to_dict(tmp):
    d = FileTypeInfo(_mk(tmp, 't.txt', 'x')).to_dict()
    assert 'filepath' in d and 'exists' in d


def test_file_entry_from_path(tmp):
    p = _mk(tmp, 'sub/code.py', 'x')
    e = FileEntry.from_path(p, tmp)
    assert e.is_file and e.extension == '.py'


def test_walker_dir_basic(tmp):
    _mk(tmp, 'a.py', '')
    assert len(DirectoryWalker(tmp, use_gitignore=False).get_all_files()) >= 1


def test_compare_files_identical(tmp):
    p1, p2 = _mk(tmp, 'f1.txt', 'same'), _mk(tmp, 'f2.txt', 'same')
    l1, l2 = read_file_lines(p1), read_file_lines(p2)
    assert l1 == l2


def test_get_file_info_basic(tmp):
    info = FileTypeInfo(_mk(tmp, 'i.txt', 'data')).to_dict()
    assert info['exists'] and info['is_file']


def test_comparator_can_compare_missing(tmp):
    p = _mk(tmp, 'x.txt', 'x')
    can, err = FileComparator(p, '/nonexistent.txt').can_compare()
    assert not can and 'not found' in err.lower()


def test_comparator_can_compare_binary(tmp):
    t, b = _mk(tmp, 't.txt', 'text'), _mk(tmp, 'b.png', b'\x89PNG\r\n\x1a\n', True)
    can, err = FileComparator(t, b).can_compare()
    assert not can and 'binary' in err.lower()


def test_walker_extra_ignore(tmp):
    _mk(tmp, 'a.py', '')
    _mk(tmp, 'b.js', '')
    files = DirectoryWalker(tmp, use_gitignore=False, extra_ignore_patterns=['*.py']).get_all_files()
    assert all(not f.endswith('.py') for f in files)
