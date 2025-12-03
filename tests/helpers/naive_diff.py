from typing import List, Tuple, Any, Optional, TypeVar, Generic, Callable
from enum import Enum
from dataclasses import dataclass


class NaiveOpType(Enum):
    EQUAL = "equal"
    DELETE = "delete"
    INSERT = "insert"
    REPLACE = "replace"


@dataclass
class NaiveEditAction:
    op: NaiveOpType
    old_value: Any
    new_value: Any
    old_index: int
    new_index: int
    
    def __repr__(self) -> str:
        if self.op == NaiveOpType.EQUAL:
            return f"EQUAL({self.old_value})"
        elif self.op == NaiveOpType.DELETE:
            return f"DELETE({self.old_value})"
        elif self.op == NaiveOpType.INSERT:
            return f"INSERT({self.new_value})"
        elif self.op == NaiveOpType.REPLACE:
            return f"REPLACE({self.old_value} -> {self.new_value})"
        return f"Action({self.op})"


T = TypeVar('T')


class LCSMatrix:
    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self._data = [[0] * cols for _ in range(rows)]
        
    def get(self, i: int, j: int) -> int:
        if i < 0 or j < 0:
            return 0
        return self._data[i][j]
        
    def set(self, i: int, j: int, value: int):
        self._data[i][j] = value
        
    def __getitem__(self, key: Tuple[int, int]) -> int:
        return self.get(key[0], key[1])
        
    def __setitem__(self, key: Tuple[int, int], value: int):
        self.set(key[0], key[1], value)


class NaiveLCS:
    def __init__(self, seq1: List[T], seq2: List[T], eq: Optional[Callable[[T, T], bool]] = None):
        self.seq1 = seq1
        self.seq2 = seq2
        self.eq = eq or (lambda a, b: a == b)
        self.matrix: Optional[LCSMatrix] = None
        
    def compute_matrix(self) -> LCSMatrix:
        m = len(self.seq1)
        n = len(self.seq2)
        matrix = LCSMatrix(m + 1, n + 1)
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if self.eq(self.seq1[i - 1], self.seq2[j - 1]):
                    matrix[i, j] = matrix[i - 1, j - 1] + 1
                else:
                    matrix[i, j] = max(matrix[i - 1, j], matrix[i, j - 1])
        self.matrix = matrix
        return matrix
        
    def get_lcs_length(self) -> int:
        if self.matrix is None:
            self.compute_matrix()
        return self.matrix[len(self.seq1), len(self.seq2)]
        
    def backtrack_lcs(self) -> List[T]:
        if self.matrix is None:
            self.compute_matrix()
        result = []
        i, j = len(self.seq1), len(self.seq2)
        while i > 0 and j > 0:
            if self.eq(self.seq1[i - 1], self.seq2[j - 1]):
                result.append(self.seq1[i - 1])
                i -= 1
                j -= 1
            elif self.matrix[i - 1, j] > self.matrix[i, j - 1]:
                i -= 1
            else:
                j -= 1
        result.reverse()
        return result


class NaiveDiff:
    def __init__(self, eq: Optional[Callable[[Any, Any], bool]] = None):
        self.eq = eq or (lambda a, b: a == b)
        
    def diff(self, old: List[Any], new: List[Any]) -> List[NaiveEditAction]:
        lcs = NaiveLCS(old, new, self.eq)
        lcs.compute_matrix()
        actions = []
        i, j = len(old), len(new)
        stack = []
        while i > 0 or j > 0:
            if i > 0 and j > 0 and self.eq(old[i - 1], new[j - 1]):
                stack.append(NaiveEditAction(
                    NaiveOpType.EQUAL,
                    old[i - 1],
                    new[j - 1],
                    i - 1,
                    j - 1
                ))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or lcs.matrix[i, j - 1] >= lcs.matrix[i - 1, j]):
                stack.append(NaiveEditAction(
                    NaiveOpType.INSERT,
                    None,
                    new[j - 1],
                    i,
                    j - 1
                ))
                j -= 1
            elif i > 0:
                stack.append(NaiveEditAction(
                    NaiveOpType.DELETE,
                    old[i - 1],
                    None,
                    i - 1,
                    j
                ))
                i -= 1
        while stack:
            actions.append(stack.pop())
        return actions
        
    def edit_distance(self, old: List[Any], new: List[Any]) -> int:
        actions = self.diff(old, new)
        return sum(1 for a in actions if a.op != NaiveOpType.EQUAL)


class SimpleDiff:
    def diff(self, old: List[Any], new: List[Any]) -> List[Tuple[str, Any]]:
        m, n = len(old), len(new)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if old[i - 1] == new[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        result = []
        i, j = m, n
        temp = []
        while i > 0 or j > 0:
            if i > 0 and j > 0 and old[i - 1] == new[j - 1]:
                temp.append(('=', old[i - 1]))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                temp.append(('+', new[j - 1]))
                j -= 1
            else:
                temp.append(('-', old[i - 1]))
                i -= 1
        temp.reverse()
        return temp


class RecursiveLCS:
    def __init__(self, seq1: List[T], seq2: List[T]):
        self.seq1 = seq1
        self.seq2 = seq2
        self._cache = {}
        
    def lcs_length(self, i: int = None, j: int = None) -> int:
        if i is None:
            i = len(self.seq1)
        if j is None:
            j = len(self.seq2)
        if i == 0 or j == 0:
            return 0
        if (i, j) in self._cache:
            return self._cache[(i, j)]
        if self.seq1[i - 1] == self.seq2[j - 1]:
            result = 1 + self.lcs_length(i - 1, j - 1)
        else:
            result = max(self.lcs_length(i - 1, j), self.lcs_length(i, j - 1))
        self._cache[(i, j)] = result
        return result
        
    def get_lcs(self) -> List[T]:
        result = []
        i, j = len(self.seq1), len(self.seq2)
        while i > 0 and j > 0:
            if self.seq1[i - 1] == self.seq2[j - 1]:
                result.append(self.seq1[i - 1])
                i -= 1
                j -= 1
            elif self.lcs_length(i - 1, j) > self.lcs_length(i, j - 1):
                i -= 1
            else:
                j -= 1
        result.reverse()
        return result


class PatienceDiff:
    def diff(self, old: List[str], new: List[str]) -> List[NaiveEditAction]:
        old_unique = {}
        new_unique = {}
        for i, line in enumerate(old):
            if line in old_unique:
                old_unique[line] = None
            else:
                old_unique[line] = i
        for i, line in enumerate(new):
            if line in new_unique:
                new_unique[line] = None
            else:
                new_unique[line] = i
        matches = []
        for line, old_idx in old_unique.items():
            if old_idx is not None and line in new_unique:
                new_idx = new_unique[line]
                if new_idx is not None:
                    matches.append((old_idx, new_idx, line))
        matches.sort(key=lambda x: x[0])
        lis_indices = self._longest_increasing_subsequence([m[1] for m in matches])
        anchors = [matches[i] for i in lis_indices]
        actions = []
        old_pos = 0
        new_pos = 0
        for old_idx, new_idx, line in anchors:
            while old_pos < old_idx:
                actions.append(NaiveEditAction(
                    NaiveOpType.DELETE, old[old_pos], None, old_pos, new_pos
                ))
                old_pos += 1
            while new_pos < new_idx:
                actions.append(NaiveEditAction(
                    NaiveOpType.INSERT, None, new[new_pos], old_pos, new_pos
                ))
                new_pos += 1
            actions.append(NaiveEditAction(
                NaiveOpType.EQUAL, line, line, old_pos, new_pos
            ))
            old_pos += 1
            new_pos += 1
        while old_pos < len(old):
            actions.append(NaiveEditAction(
                NaiveOpType.DELETE, old[old_pos], None, old_pos, new_pos
            ))
            old_pos += 1
        while new_pos < len(new):
            actions.append(NaiveEditAction(
                NaiveOpType.INSERT, None, new[new_pos], old_pos, new_pos
            ))
            new_pos += 1
        return actions
        
    def _longest_increasing_subsequence(self, arr: List[int]) -> List[int]:
        if not arr:
            return []
        n = len(arr)
        dp = [1] * n
        parent = [-1] * n
        for i in range(1, n):
            for j in range(i):
                if arr[j] < arr[i] and dp[j] + 1 > dp[i]:
                    dp[i] = dp[j] + 1
                    parent[i] = j
        max_idx = 0
        for i in range(n):
            if dp[i] > dp[max_idx]:
                max_idx = i
        result = []
        idx = max_idx
        while idx != -1:
            result.append(idx)
            idx = parent[idx]
        result.reverse()
        return result


class HistogramDiff:
    def __init__(self, max_chain: int = 64):
        self.max_chain = max_chain
        
    def diff(self, old: List[str], new: List[str]) -> List[NaiveEditAction]:
        return self._diff_region(old, 0, len(old), new, 0, len(new))
        
    def _diff_region(
        self,
        old: List[str], old_start: int, old_end: int,
        new: List[str], new_start: int, new_end: int
    ) -> List[NaiveEditAction]:
        if old_start >= old_end and new_start >= new_end:
            return []
        if old_start >= old_end:
            return [
                NaiveEditAction(NaiveOpType.INSERT, None, new[i], old_start, i)
                for i in range(new_start, new_end)
            ]
        if new_start >= new_end:
            return [
                NaiveEditAction(NaiveOpType.DELETE, old[i], None, i, new_start)
                for i in range(old_start, old_end)
            ]
        histogram = {}
        for i in range(new_start, new_end):
            line = new[i]
            if line not in histogram:
                histogram[line] = []
            histogram[line].append(i)
        best_line = None
        best_old_idx = -1
        best_new_idx = -1
        best_count = self.max_chain + 1
        for i in range(old_start, old_end):
            line = old[i]
            if line in histogram and len(histogram[line]) < best_count:
                best_count = len(histogram[line])
                best_line = line
                best_old_idx = i
                best_new_idx = histogram[line][0]
        if best_line is None:
            actions = []
            for i in range(old_start, old_end):
                actions.append(NaiveEditAction(
                    NaiveOpType.DELETE, old[i], None, i, new_start
                ))
            for i in range(new_start, new_end):
                actions.append(NaiveEditAction(
                    NaiveOpType.INSERT, None, new[i], old_end, i
                ))
            return actions
        actions = []
        actions.extend(self._diff_region(
            old, old_start, best_old_idx,
            new, new_start, best_new_idx
        ))
        actions.append(NaiveEditAction(
            NaiveOpType.EQUAL, best_line, best_line, best_old_idx, best_new_idx
        ))
        actions.extend(self._diff_region(
            old, best_old_idx + 1, old_end,
            new, best_new_idx + 1, new_end
        ))
        return actions


class BlockDiff:
    def __init__(self, block_size: int = 3):
        self.block_size = block_size
        
    def diff(self, old: List[str], new: List[str]) -> List[NaiveEditAction]:
        old_blocks = self._create_blocks(old)
        new_blocks = self._create_blocks(new)
        block_matches = []
        used_new = set()
        for old_idx, old_block in old_blocks.items():
            for new_idx, new_block in new_blocks.items():
                if new_idx not in used_new and old_block == new_block:
                    block_matches.append((old_idx, new_idx))
                    used_new.add(new_idx)
                    break
        block_matches.sort()
        actions = []
        old_pos = 0
        new_pos = 0
        for old_idx, new_idx in block_matches:
            while old_pos < old_idx:
                actions.append(NaiveEditAction(
                    NaiveOpType.DELETE, old[old_pos], None, old_pos, new_pos
                ))
                old_pos += 1
            while new_pos < new_idx:
                actions.append(NaiveEditAction(
                    NaiveOpType.INSERT, None, new[new_pos], old_pos, new_pos
                ))
                new_pos += 1
            for offset in range(self.block_size):
                if old_pos + offset < len(old) and new_pos + offset < len(new):
                    actions.append(NaiveEditAction(
                        NaiveOpType.EQUAL,
                        old[old_pos + offset],
                        new[new_pos + offset],
                        old_pos + offset,
                        new_pos + offset
                    ))
            old_pos = old_idx + self.block_size
            new_pos = new_idx + self.block_size
        while old_pos < len(old):
            actions.append(NaiveEditAction(
                NaiveOpType.DELETE, old[old_pos], None, old_pos, new_pos
            ))
            old_pos += 1
        while new_pos < len(new):
            actions.append(NaiveEditAction(
                NaiveOpType.INSERT, None, new[new_pos], old_pos, new_pos
            ))
            new_pos += 1
        return actions
        
    def _create_blocks(self, lines: List[str]) -> dict:
        blocks = {}
        for i in range(len(lines) - self.block_size + 1):
            block = tuple(lines[i:i + self.block_size])
            if i not in blocks:
                blocks[i] = block
        return blocks


class DiffVerifier:
    def verify_diff(self, old: List[Any], new: List[Any], actions: List[NaiveEditAction]) -> bool:
        reconstructed = []
        for action in actions:
            if action.op == NaiveOpType.EQUAL:
                reconstructed.append(action.old_value)
            elif action.op == NaiveOpType.INSERT:
                reconstructed.append(action.new_value)
        return reconstructed == new
        
    def verify_reverse(self, old: List[Any], new: List[Any], actions: List[NaiveEditAction]) -> bool:
        reconstructed = []
        for action in actions:
            if action.op == NaiveOpType.EQUAL:
                reconstructed.append(action.old_value)
            elif action.op == NaiveOpType.DELETE:
                reconstructed.append(action.old_value)
        return reconstructed == old


class DiffStats:
    def __init__(self, actions: List[NaiveEditAction]):
        self.actions = actions
        self._compute_stats()
        
    def _compute_stats(self):
        self.equal_count = 0
        self.delete_count = 0
        self.insert_count = 0
        self.replace_count = 0
        for action in self.actions:
            if action.op == NaiveOpType.EQUAL:
                self.equal_count += 1
            elif action.op == NaiveOpType.DELETE:
                self.delete_count += 1
            elif action.op == NaiveOpType.INSERT:
                self.insert_count += 1
            elif action.op == NaiveOpType.REPLACE:
                self.replace_count += 1
                
    def total_changes(self) -> int:
        return self.delete_count + self.insert_count + self.replace_count
        
    def similarity_ratio(self) -> float:
        total = len(self.actions)
        if total == 0:
            return 1.0
        return self.equal_count / total
        
    def edit_distance(self) -> int:
        return self.delete_count + self.insert_count
        
    def __repr__(self) -> str:
        return (
            f"DiffStats(equal={self.equal_count}, "
            f"delete={self.delete_count}, "
            f"insert={self.insert_count})"
        )


def naive_diff(old: List[Any], new: List[Any]) -> List[NaiveEditAction]:
    differ = NaiveDiff()
    return differ.diff(old, new)


def simple_diff(old: List[Any], new: List[Any]) -> List[Tuple[str, Any]]:
    differ = SimpleDiff()
    return differ.diff(old, new)


def lcs(seq1: List[T], seq2: List[T]) -> List[T]:
    lcs_obj = NaiveLCS(seq1, seq2)
    return lcs_obj.backtrack_lcs()


def lcs_length(seq1: List[Any], seq2: List[Any]) -> int:
    lcs_obj = NaiveLCS(seq1, seq2)
    return lcs_obj.get_lcs_length()


def edit_distance(old: List[Any], new: List[Any]) -> int:
    differ = NaiveDiff()
    return differ.edit_distance(old, new)


def verify_diff(old: List[Any], new: List[Any], actions: List[NaiveEditAction]) -> bool:
    verifier = DiffVerifier()
    return verifier.verify_diff(old, new, actions)


def get_diff_stats(actions: List[NaiveEditAction]) -> DiffStats:
    return DiffStats(actions)


def patience_diff(old: List[str], new: List[str]) -> List[NaiveEditAction]:
    differ = PatienceDiff()
    return differ.diff(old, new)


def histogram_diff(old: List[str], new: List[str]) -> List[NaiveEditAction]:
    differ = HistogramDiff()
    return differ.diff(old, new)
