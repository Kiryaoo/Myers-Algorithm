from typing import List, Tuple, Any, Optional, TypeVar, Callable
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
        return f"REPLACE({self.old_value} -> {self.new_value})"


T = TypeVar('T')


class NaiveLCS:
    def __init__(self, seq1: List[T], seq2: List[T],
                 eq: Optional[Callable[[T, T], bool]] = None):
        self.seq1, self.seq2 = seq1, seq2
        self.eq = eq or (lambda a, b: a == b)
        self._matrix: Optional[List[List[int]]] = None

    def compute_matrix(self) -> List[List[int]]:
        m, n = len(self.seq1), len(self.seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if self.eq(self.seq1[i - 1], self.seq2[j - 1]):
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        self._matrix = dp
        return dp

    def get_lcs_length(self) -> int:
        if self._matrix is None:
            self.compute_matrix()
        return self._matrix[len(self.seq1)][len(self.seq2)]

    def backtrack_lcs(self) -> List[T]:
        if self._matrix is None:
            self.compute_matrix()
        result, i, j = [], len(self.seq1), len(self.seq2)
        while i > 0 and j > 0:
            if self.eq(self.seq1[i - 1], self.seq2[j - 1]):
                result.append(self.seq1[i - 1])
                i, j = i - 1, j - 1
            elif self._matrix[i - 1][j] > self._matrix[i][j - 1]:
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
        actions, stack = [], []
        i, j = len(old), len(new)
        while i > 0 or j > 0:
            if i > 0 and j > 0 and self.eq(old[i - 1], new[j - 1]):
                stack.append(NaiveEditAction(NaiveOpType.EQUAL, old[i - 1],
                                              new[j - 1], i - 1, j - 1))
                i, j = i - 1, j - 1
            elif j > 0 and (i == 0 or lcs._matrix[i][j - 1] >= lcs._matrix[i - 1][j]):
                stack.append(NaiveEditAction(NaiveOpType.INSERT, None,
                                              new[j - 1], i, j - 1))
                j -= 1
            elif i > 0:
                stack.append(NaiveEditAction(NaiveOpType.DELETE, old[i - 1],
                                              None, i - 1, j))
                i -= 1
        while stack:
            actions.append(stack.pop())
        return actions

    def edit_distance(self, old: List[Any], new: List[Any]) -> int:
        return sum(1 for a in self.diff(old, new) if a.op != NaiveOpType.EQUAL)


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
        temp, i, j = [], m, n
        while i > 0 or j > 0:
            if i > 0 and j > 0 and old[i - 1] == new[j - 1]:
                temp.append(('=', old[i - 1]))
                i, j = i - 1, j - 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                temp.append(('+', new[j - 1]))
                j -= 1
            else:
                temp.append(('-', old[i - 1]))
                i -= 1
        temp.reverse()
        return temp


class DiffVerifier:
    def verify_diff(self, old: List[Any], new: List[Any],
                    actions: List[NaiveEditAction]) -> bool:
        reconstructed = [a.old_value if a.op == NaiveOpType.EQUAL else a.new_value
                         for a in actions if a.op in (NaiveOpType.EQUAL, NaiveOpType.INSERT)]
        return reconstructed == new

    def verify_reverse(self, old: List[Any], new: List[Any],
                       actions: List[NaiveEditAction]) -> bool:
        reconstructed = [a.old_value for a in actions
                         if a.op in (NaiveOpType.EQUAL, NaiveOpType.DELETE)]
        return reconstructed == old


class DiffStats:
    def __init__(self, actions: List[NaiveEditAction]):
        self.equal_count = sum(1 for a in actions if a.op == NaiveOpType.EQUAL)
        self.delete_count = sum(1 for a in actions if a.op == NaiveOpType.DELETE)
        self.insert_count = sum(1 for a in actions if a.op == NaiveOpType.INSERT)
        self.replace_count = sum(1 for a in actions if a.op == NaiveOpType.REPLACE)
        self._total = len(actions)

    def total_changes(self) -> int:
        return self.delete_count + self.insert_count + self.replace_count

    def similarity_ratio(self) -> float:
        return self.equal_count / self._total if self._total else 1.0

    def edit_distance(self) -> int:
        return self.delete_count + self.insert_count

    def __repr__(self) -> str:
        return f"DiffStats(eq={self.equal_count}, del={self.delete_count}, ins={self.insert_count})"


def naive_diff(old: List[Any], new: List[Any]) -> List[NaiveEditAction]:
    return NaiveDiff().diff(old, new)


def simple_diff(old: List[Any], new: List[Any]) -> List[Tuple[str, Any]]:
    return SimpleDiff().diff(old, new)


def lcs(seq1: List[T], seq2: List[T]) -> List[T]:
    return NaiveLCS(seq1, seq2).backtrack_lcs()


def lcs_length(seq1: List[Any], seq2: List[Any]) -> int:
    return NaiveLCS(seq1, seq2).get_lcs_length()


def edit_distance(old: List[Any], new: List[Any]) -> int:
    return NaiveDiff().edit_distance(old, new)


def verify_diff(old: List[Any], new: List[Any], actions: List[NaiveEditAction]) -> bool:
    return DiffVerifier().verify_diff(old, new, actions)


def get_diff_stats(actions: List[NaiveEditAction]) -> DiffStats:
    return DiffStats(actions)
