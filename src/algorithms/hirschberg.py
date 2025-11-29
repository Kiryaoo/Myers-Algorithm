from typing import TypeVar, List, Dict, Tuple, Optional
from .utils import EditAction, EditScript, OpType, make_insert, make_delete, make_equal


T = TypeVar('T')


class HirschbergDiff:
    def __init__(self, original: List[T], modified: List[T]):
        self.original = original
        self.modified = modified
        
    def compute(self) -> EditScript:
        return self._hirschberg(self.original, self.modified)
    
    def _hirschberg(self, a: List[T], b: List[T]) -> EditScript:
        n = len(a)
        m = len(b)
        if n == 0:
            return [make_insert(item) for item in b]
        if m == 0:
            return [make_delete(item) for item in a]
        if n == 1:
            return self._diff_single_element(a[0], b)
        if m == 1:
            return self._diff_against_single(a, b[0])
        mid = n // 2
        score_left = self._score_forward(a[:mid], b)
        score_right = self._score_backward(a[mid:], b)
        combined = [score_left[j] + score_right[m - j] for j in range(m + 1)]
        split_j = combined.index(max(combined))
        left_result = self._hirschberg(a[:mid], b[:split_j])
        right_result = self._hirschberg(a[mid:], b[split_j:])
        return left_result + right_result
    
    def _score_forward(self, a: List[T], b: List[T]) -> List[int]:
        n = len(a)
        m = len(b)
        prev = list(range(m + 1))
        curr = [0] * (m + 1)
        for i in range(1, n + 1):
            curr[0] = i
            for j in range(1, m + 1):
                if a[i - 1] == b[j - 1]:
                    curr[j] = prev[j - 1]
                else:
                    curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
            prev, curr = curr, prev
        return [m - x for x in prev]
    
    def _score_backward(self, a: List[T], b: List[T]) -> List[int]:
        return self._score_forward(a[::-1], b[::-1])[::-1]
    
    def _diff_single_element(self, elem: T, b: List[T]) -> EditScript:
        result = []
        found = False
        for i, item in enumerate(b):
            if item == elem and not found:
                result.append(make_equal(elem))
                found = True
            else:
                result.append(make_insert(item))
        if not found:
            result.insert(0, make_delete(elem))
        return result
    
    def _diff_against_single(self, a: List[T], elem: T) -> EditScript:
        result = []
        found = False
        for item in a:
            if item == elem and not found:
                result.append(make_equal(elem))
                found = True
            else:
                result.append(make_delete(item))
        if not found:
            result.append(make_insert(elem))
        return result


def diff_linear(original: List[T], modified: List[T]) -> EditScript:
    differ = HirschbergDiff(original, modified)
    return differ.compute()


class LinearSpaceMyers:
    def __init__(self, original: List[T], modified: List[T]):
        self.original = original
        self.modified = modified
        self.n = len(original)
        self.m = len(modified)
        
    def compute(self) -> EditScript:
        if self.n == 0 and self.m == 0:
            return []
        if self.n == 0:
            return [make_insert(item) for item in self.modified]
        if self.m == 0:
            return [make_delete(item) for item in self.original]
        return self._lcs_diff(0, self.n, 0, self.m)
    
    def _lcs_diff(self, x_start: int, x_end: int, y_start: int, y_end: int) -> EditScript:
        a = self.original[x_start:x_end]
        b = self.modified[y_start:y_end]
        n = len(a)
        m = len(b)
        if n == 0:
            return [make_insert(item) for item in b]
        if m == 0:
            return [make_delete(item) for item in a]
        if n == 1 or m == 1:
            return self._simple_diff(a, b)
        snake = self._find_middle_snake(a, b)
        x_mid, y_mid, u, v, d = snake
        if d > 1:
            left = self._lcs_diff(x_start, x_start + x_mid, y_start, y_start + y_mid)
            middle = []
            for i in range(x_mid, u):
                middle.append(make_equal(self.original[x_start + i]))
            right = self._lcs_diff(x_start + u, x_end, y_start + v, y_end)
            return left + middle + right
        else:
            return self._simple_diff(a, b)
    
    def _simple_diff(self, a: List[T], b: List[T]) -> EditScript:
        result = []
        i = j = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                result.append(make_equal(a[i]))
                i += 1
                j += 1
            elif i < len(a):
                result.append(make_delete(a[i]))
                i += 1
            else:
                result.append(make_insert(b[j]))
                j += 1
        while i < len(a):
            result.append(make_delete(a[i]))
            i += 1
        while j < len(b):
            result.append(make_insert(b[j]))
            j += 1
        return result
    
    def _find_middle_snake(self, a: List[T], b: List[T]) -> Tuple[int, int, int, int, int]:
        n = len(a)
        m = len(b)
        max_d = (n + m + 1) // 2
        v_size = 2 * max_d + 1
        v_forward = [0] * v_size
        v_backward = [0] * v_size
        delta = n - m
        odd = delta % 2 != 0
        def vf(k: int) -> int:
            return v_forward[k + max_d]
        def vb(k: int) -> int:
            return v_backward[k + max_d]
        def set_vf(k: int, val: int):
            v_forward[k + max_d] = val
        def set_vb(k: int, val: int):
            v_backward[k + max_d] = val
        for d in range(max_d + 1):
            for k in range(-d, d + 1, 2):
                if k == -d or (k != d and vf(k - 1) < vf(k + 1)):
                    x = vf(k + 1)
                else:
                    x = vf(k - 1) + 1
                y = x - k
                x_start, y_start = x, y
                while x < n and y < m and a[x] == b[y]:
                    x += 1
                    y += 1
                set_vf(k, x)
                if odd and -(d - 1) <= k - delta <= (d - 1):
                    if vf(k) + vb(delta - k) >= n:
                        return (x_start, y_start, x, y, 2 * d - 1)
            for k in range(-d, d + 1, 2):
                if k == -d or (k != d and vb(k - 1) < vb(k + 1)):
                    x = vb(k + 1)
                else:
                    x = vb(k - 1) + 1
                y = x - k
                while x < n and y < m and a[n - 1 - x] == b[m - 1 - y]:
                    x += 1
                    y += 1
                set_vb(k, x)
                if not odd and -d <= k - delta <= d:
                    if vb(k) + vf(delta - k) >= n:
                        x_end = n - vb(k)
                        y_end = m - (vb(k) - k)
                        return (x_end, y_end, n - x, m - y, 2 * d)
        return (0, 0, n, m, n + m)


def diff_linear_myers(original: List[T], modified: List[T]) -> EditScript:
    differ = LinearSpaceMyers(original, modified)
    return differ.compute()


class DiffEngine:
    def __init__(self, use_linear_space: bool = False):
        self.use_linear_space = use_linear_space
        
    def diff(self, original: List[T], modified: List[T]) -> EditScript:
        if self.use_linear_space:
            return diff_linear_myers(original, modified)
        from .myers import diff
        return diff(original, modified)
    
    def diff_strings(self, original: str, modified: str, by_line: bool = True) -> EditScript:
        if by_line:
            orig_lines = original.split('\n')
            mod_lines = modified.split('\n')
        else:
            orig_lines = list(original)
            mod_lines = list(modified)
        return self.diff(orig_lines, mod_lines)
    
    def compute_lcs(self, a: List[T], b: List[T]) -> List[T]:
        script = self.diff(a, b)
        return [action.value for action in script if action.op == OpType.EQUAL]
    
    def compute_edit_distance(self, a: List[T], b: List[T]) -> int:
        script = self.diff(a, b)
        return sum(1 for action in script if action.op != OpType.EQUAL)


class BatchDiffer:
    def __init__(self, engine: Optional[DiffEngine] = None):
        self.engine = engine or DiffEngine()
        
    def diff_multiple(self, pairs: List[Tuple[List[T], List[T]]]) -> List[EditScript]:
        results = []
        for orig, mod in pairs:
            results.append(self.engine.diff(orig, mod))
        return results
    
    def diff_all_against_base(self, base: List[T], targets: List[List[T]]) -> List[EditScript]:
        results = []
        for target in targets:
            results.append(self.engine.diff(base, target))
        return results
