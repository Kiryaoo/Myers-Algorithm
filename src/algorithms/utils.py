from typing import TypeVar, List, Tuple, NamedTuple, Optional, Callable, Iterator
from enum import Enum
from dataclasses import dataclass, field

T = TypeVar('T')

class OpType(str, Enum):
    INSERT = 'insert'
    DELETE = 'delete'
    EQUAL = 'equal'
    REPLACE = 'replace'

class EditAction(NamedTuple):
    op: OpType
    value: object
    old_value: Optional[object] = None
    
    def __repr__(self) -> str:
        if self.op == OpType.REPLACE:
            return f"EditAction({self.op.value!r}, {self.value!r}, {self.old_value!r})"
        return f"EditAction({self.op.value!r}, {self.value!r})"


EditScript = List[EditAction]


@dataclass
class DiffResult:
    script: EditScript
    original_length: int
    modified_length: int
    edit_distance: int
    lcs_length: int
    similarity_ratio: float
    
    @classmethod
    def from_script(cls, script: EditScript, orig_len: int, mod_len: int) -> 'DiffResult':
        edit_dist = sum(1 for a in script if a.op != OpType.EQUAL)
        lcs_len = sum(1 for a in script if a.op == OpType.EQUAL)
        total = orig_len + mod_len
        sim_ratio = (2.0 * lcs_len / total) if total > 0 else 1.0
        return cls(
            script=script,
            original_length=orig_len,
            modified_length=mod_len,
            edit_distance=edit_dist,
            lcs_length=lcs_len,
            similarity_ratio=sim_ratio
        )


@dataclass
class Hunk:
    orig_start: int
    orig_count: int
    mod_start: int
    mod_count: int
    operations: List[Tuple[str, str]]
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)


class TokenType(str, Enum):
    LINE = 'line'
    WORD = 'word'
    CHAR = 'char'


def make_insert(value: T) -> EditAction:
    return EditAction(OpType.INSERT, value)


def make_delete(value: T) -> EditAction:
    return EditAction(OpType.DELETE, value)


def make_equal(value: T) -> EditAction:
    return EditAction(OpType.EQUAL, value)


def make_replace(new_value: T, old_value: T) -> EditAction:
    return EditAction(OpType.REPLACE, new_value, old_value)


def script_to_tuples(script: EditScript) -> List[Tuple[str, object]]:
    return [(action.op.value, action.value) for action in script]


def tuples_to_script(tuples: List[Tuple[str, object]]) -> EditScript:
    result = []
    for op_str, value in tuples:
        op = OpType(op_str)
        result.append(EditAction(op, value))
    return result


def count_operations(script: EditScript) -> dict:
    counts = {
        'inserts': 0,
        'deletes': 0,
        'equals': 0,
        'replaces': 0,
        'total': len(script)
    }
    for action in script:
        if action.op == OpType.INSERT:
            counts['inserts'] += 1
        elif action.op == OpType.DELETE:
            counts['deletes'] += 1
        elif action.op == OpType.EQUAL:
            counts['equals'] += 1
        elif action.op == OpType.REPLACE:
            counts['replaces'] += 1
    return counts


def tokenize_lines(text: str) -> List[str]:
    if not text:
        return []
    lines = text.split('\n')
    return lines


def tokenize_words(text: str) -> List[str]:
    if not text:
        return []
    import re
    tokens = re.findall(r'\S+|\s+', text)
    return tokens


def tokenize_chars(text: str) -> List[str]:
    return list(text)


def get_tokenizer(token_type: TokenType) -> Callable[[str], List[str]]:
    tokenizers = {
        TokenType.LINE: tokenize_lines,
        TokenType.WORD: tokenize_words,
        TokenType.CHAR: tokenize_chars
    }
    return tokenizers[token_type]


def join_tokens(tokens: List[str], token_type: TokenType) -> str:
    if token_type == TokenType.LINE:
        return '\n'.join(tokens)
    elif token_type == TokenType.WORD:
        return ''.join(tokens)
    else:
        return ''.join(tokens)


def group_consecutive_ops(script: EditScript) -> List[Tuple[OpType, List[object]]]:
    if not script:
        return []
    groups = []
    current_op = script[0].op
    current_values = [script[0].value]
    for action in script[1:]:
        if action.op == current_op:
            current_values.append(action.value)
        else:
            groups.append((current_op, current_values))
            current_op = action.op
            current_values = [action.value]
    groups.append((current_op, current_values))
    return groups


def split_into_hunks(script: EditScript, context: int = 3) -> List[List[EditAction]]:
    if not script:
        return []
    change_indices = []
    for i, action in enumerate(script):
        if action.op != OpType.EQUAL:
            change_indices.append(i)
    if not change_indices:
        return []
    hunks = []
    current_hunk_start = max(0, change_indices[0] - context)
    current_hunk_end = min(len(script) - 1, change_indices[0] + context)
    for idx in change_indices[1:]:
        potential_start = max(0, idx - context)
        if potential_start <= current_hunk_end + 1:
            current_hunk_end = min(len(script) - 1, idx + context)
        else:
            hunks.append(script[current_hunk_start:current_hunk_end + 1])
            current_hunk_start = potential_start
            current_hunk_end = min(len(script) - 1, idx + context)
    hunks.append(script[current_hunk_start:current_hunk_end + 1])
    return hunks


def calculate_line_numbers(script: EditScript) -> List[Tuple[Optional[int], Optional[int]]]:
    result = []
    orig_line = 1
    mod_line = 1
    for action in script:
        if action.op == OpType.EQUAL:
            result.append((orig_line, mod_line))
            orig_line += 1
            mod_line += 1
        elif action.op == OpType.DELETE:
            result.append((orig_line, None))
            orig_line += 1
        elif action.op == OpType.INSERT:
            result.append((None, mod_line))
            mod_line += 1
        elif action.op == OpType.REPLACE:
            result.append((orig_line, mod_line))
            orig_line += 1
            mod_line += 1
    return result
