import os
from typing import BinaryIO, Optional, List, Set


BINARY_SIGNATURES = [
    b'\x89PNG\r\n\x1a\n',
    b'\xff\xd8\xff',
    b'GIF87a',
    b'GIF89a',
    b'PK\x03\x04',
    b'PK\x05\x06',
    b'%PDF',
    b'\x7fELF',
    b'MZ',
    b'\x00\x00\x01\x00',
    b'RIFF',
    b'\x1f\x8b',
    b'BZh',
    b'\xfd7zXZ\x00',
    b'Rar!\x1a\x07',
    b'\xca\xfe\xba\xbe',
    b'\xce\xfa\xed\xfe',
    b'\xcf\xfa\xed\xfe',
]


BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.tiff', '.tif',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
    '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.wav', '.ogg',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    '.pyc', '.pyo', '.class', '.o', '.obj',
    '.db', '.sqlite', '.sqlite3',
}


CHECK_SIZE = 8192
NULL_BYTE_THRESHOLD = 0.30


class BinaryDetector:
    def __init__(self):
        self.signatures = BINARY_SIGNATURES
        self.binary_extensions = BINARY_EXTENSIONS
        self.check_size = CHECK_SIZE
        self.null_threshold = NULL_BYTE_THRESHOLD
        
    def is_binary_by_extension(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.binary_extensions
    
    def is_binary_by_signature(self, data: bytes) -> bool:
        for sig in self.signatures:
            if data.startswith(sig):
                return True
        return False
    
    def is_binary_by_content(self, data: bytes) -> bool:
        if not data:
            return False
        if b'\x00' in data:
            return True
        try:
            data.decode('utf-8')
            return False
        except UnicodeDecodeError:
            pass
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = sum(1 for byte in data if byte not in text_chars)
        return (non_text / len(data)) > self.null_threshold
    
    def check_file(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        if not os.path.isfile(filepath):
            raise ValueError(f"Not a file: {filepath}")
        if os.path.getsize(filepath) == 0:
            return False
        if self.is_binary_by_extension(filepath):
            return True
        with open(filepath, 'rb') as f:
            chunk = f.read(self.check_size)
        if self.is_binary_by_signature(chunk):
            return True
        return self.is_binary_by_content(chunk)
    
    def check_stream(self, stream: BinaryIO) -> bool:
        chunk = stream.read(self.check_size)
        stream.seek(0)
        if not chunk:
            return False
        if self.is_binary_by_signature(chunk):
            return True
        return self.is_binary_by_content(chunk)


def is_binary_file(filepath: str) -> bool:
    detector = BinaryDetector()
    return detector.check_file(filepath)


def is_binary_content(file_obj: BinaryIO) -> bool:
    detector = BinaryDetector()
    return detector.check_stream(file_obj)


class EncodingDetector:
    ENCODINGS = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 
                 'latin-1', 'cp1251', 'cp1252', 'iso-8859-1', 'ascii']
    
    BOM_ENCODINGS = {
        b'\xef\xbb\xbf': 'utf-8-sig',
        b'\xff\xfe': 'utf-16-le',
        b'\xfe\xff': 'utf-16-be',
        b'\xff\xfe\x00\x00': 'utf-32-le',
        b'\x00\x00\xfe\xff': 'utf-32-be',
    }
    
    def __init__(self):
        self.encodings = self.ENCODINGS
        self.bom_map = self.BOM_ENCODINGS
        
    def detect_bom(self, data: bytes) -> Optional[str]:
        for bom, encoding in sorted(self.bom_map.items(), key=lambda x: -len(x[0])):
            if data.startswith(bom):
                return encoding
        return None
    
    def detect_encoding(self, filepath: str) -> str:
        with open(filepath, 'rb') as f:
            raw = f.read(CHECK_SIZE)
        bom_encoding = self.detect_bom(raw)
        if bom_encoding:
            return bom_encoding
        for encoding in self.encodings:
            try:
                raw.decode(encoding)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        return 'utf-8'
    
    def detect_from_content(self, data: bytes) -> str:
        bom_encoding = self.detect_bom(data)
        if bom_encoding:
            return bom_encoding
        for encoding in self.encodings:
            try:
                data.decode(encoding)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        return 'utf-8'


def get_file_encoding(filepath: str) -> str:
    detector = EncodingDetector()
    return detector.detect_encoding(filepath)


def detect_line_ending(filepath: str) -> str:
    with open(filepath, 'rb') as f:
        chunk = f.read(CHECK_SIZE)
    crlf_count = chunk.count(b'\r\n')
    lf_count = chunk.count(b'\n') - crlf_count
    cr_count = chunk.count(b'\r') - crlf_count
    if crlf_count >= lf_count and crlf_count >= cr_count:
        return '\r\n'
    elif cr_count > lf_count:
        return '\r'
    return '\n'


class FileTypeInfo:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.exists = os.path.exists(filepath)
        self.is_file = os.path.isfile(filepath) if self.exists else False
        self.is_dir = os.path.isdir(filepath) if self.exists else False
        self.size = os.path.getsize(filepath) if self.is_file else 0
        self._is_binary: Optional[bool] = None
        self._encoding: Optional[str] = None
        self._line_ending: Optional[str] = None
        
    @property
    def is_binary(self) -> bool:
        if self._is_binary is None:
            if not self.is_file or self.size == 0:
                self._is_binary = False
            else:
                self._is_binary = is_binary_file(self.filepath)
        return self._is_binary
    
    @property
    def encoding(self) -> str:
        if self._encoding is None:
            if self.is_binary:
                self._encoding = 'binary'
            else:
                self._encoding = get_file_encoding(self.filepath)
        return self._encoding
    
    @property
    def line_ending(self) -> str:
        if self._line_ending is None:
            if self.is_binary:
                self._line_ending = ''
            else:
                self._line_ending = detect_line_ending(self.filepath)
        return self._line_ending
    
    def to_dict(self) -> dict:
        return {
            'filepath': self.filepath,
            'exists': self.exists,
            'is_file': self.is_file,
            'is_dir': self.is_dir,
            'size': self.size,
            'is_binary': self.is_binary,
            'encoding': self.encoding,
            'line_ending': repr(self.line_ending),
        }