from typing import TypeVar, List, Dict, Optional, Any, Tuple
from .utils import EditAction, EditScript, OpType, make_insert, make_delete, make_equal, DiffResult

T = TypeVar('T')

class MyersDiff:
    def __init__(self, original: List[T], modified: List[T]):
        self.original = original
        self.modified = modified
        self.n = len(original)
        self.m = len(modified)
        self._trace: List[Dict[int, int]] = []
        self._edit_distance: Optional[int] = None
        
    def compute(self) -> EditScript:
        if self.n == 0 and self.m == 0:
            return []
        if self.n == 0:
            return [make_insert(item) for item in self.modified]
        if self.m == 0:
            return [make_delete(item) for item in self.original]
        self._trace = self._find_path()
        return self._trace_path()
    
    def _find_path(self) -> List[Dict[int, int]]:
        n, m = self.n, self.m
        max_d = n + m
        v: Dict[int, int] = {1: 0}
        trace: List[Dict[int, int]] = []
        for d in range(max_d + 1):
            trace.append(v.copy())
            for k in range(-d, d + 1, 2):
                if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                    x = v.get(k + 1, 0)
                else:
                    x = v.get(k - 1, 0) + 1
                y = x - k
                while x < n and y < m and self.original[x] == self.modified[y]:
                    x += 1
                    y += 1
                v[k] = x
                if x >= n and y >= m:
                    self._edit_distance = d
                    return trace
        return trace
    
    def _trace_path(self) -> EditScript:
        x, y = self.n, self.m
        script_reversed: List[EditAction] = []
        for d in range(len(self._trace) - 1, -1, -1):
            v = self._trace[d]
            k = x - y
            if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                prev_k = k + 1
            else:
                prev_k = k - 1
            prev_x = v.get(prev_k, 0)
            prev_y = prev_x - prev_k
            while x > prev_x and y > prev_y:
                x -= 1
                y -= 1
                script_reversed.append(make_equal(self.original[x]))
            if d > 0:
                if x == prev_x:
                    y -= 1
                    script_reversed.append(make_insert(self.modified[y]))
                else:
                    x -= 1
                    script_reversed.append(make_delete(self.original[x]))
        script_reversed.reverse()
        return script_reversed
    
    def get_edit_distance(self) -> int:
        if self._edit_distance is None:
            self.compute()
        return self._edit_distance or 0
    
    def get_result(self) -> DiffResult:
        script = self.compute()
        return DiffResult.from_script(script, self.n, self.m)

def diff(original: List[T], modified: List[T]) -> EditScript:
    differ = MyersDiff(original, modified)
    return differ.compute()

def patch(original: List[T], script: EditScript) -> List[T]:
    result: List[T] = []
    orig_idx = 0
    for action in script:
        if action.op == OpType.EQUAL:
            if orig_idx >= len(original):
                raise ValueError(f"Script inconsistent at EQUAL, index {orig_idx}")
            if original[orig_idx] != action.value:
                raise ValueError(f"Mismatch at {orig_idx}: {original[orig_idx]} != {action.value}")
            result.append(action.value)
            orig_idx += 1
        elif action.op == OpType.DELETE:
            if orig_idx >= len(original):
                raise ValueError(f"Script inconsistent at DELETE, index {orig_idx}")
            if original[orig_idx] != action.value:
                raise ValueError(f"DELETE mismatch at {orig_idx}")
            orig_idx += 1
        elif action.op == OpType.INSERT:
            result.append(action.value)
        elif action.op == OpType.REPLACE:
            if orig_idx >= len(original):
                raise ValueError(f"Script inconsistent at REPLACE, index {orig_idx}")
            result.append(action.value)
            orig_idx += 1
    if orig_idx != len(original):
        raise ValueError(f"Script incomplete: consumed {orig_idx} of {len(original)}")
    return result

def edit_distance(original: List[T], modified: List[T]) -> int:
    differ = MyersDiff(original, modified)
    return differ.get_edit_distance()

def lcs_length(original: List[T], modified: List[T]) -> int:
    script = diff(original, modified)
    return sum(1 for action in script if action.op == OpType.EQUAL)

def similarity_ratio(original: List[T], modified: List[T]) -> float:
    if not original and not modified:
        return 1.0
    lcs = lcs_length(original, modified)
    total = len(original) + len(modified)
    return (2.0 * lcs) / total if total > 0 else 1.0

class SnakeInfo:
    def __init__(self, x_start: int, y_start: int, x_end: int, y_end: int):
        self.x_start = x_start
        self.y_start = y_start
        self.x_end = x_end
        self.y_end = y_end
        
    @property
    def length(self) -> int:
        return self.x_end - self.x_start

class EditGraphNode:
    def __init__(self, x: int, y: int, parent: Optional['EditGraphNode'] = None, op: Optional[OpType] = None):
        self.x = x
        self.y = y
        self.parent = parent
        self.op = op

def find_middle_snake(original: List[T], modified: List[T], 
                      x_offset: int = 0, y_offset: int = 0) -> Tuple[int, int, int, int, int]:
    n = len(original)
    m = len(modified)
    if n == 0 or m == 0:
        return (0, 0, 0, 0, n + m)
    max_d = (n + m + 1) // 2
    v_forward: Dict[int, int] = {1: 0}
    v_backward: Dict[int, int] = {1: 0}
    delta = n - m
    odd = delta % 2 != 0
    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v_forward.get(k - 1, 0) < v_forward.get(k + 1, 0)):
                x = v_forward.get(k + 1, 0)
            else:
                x = v_forward.get(k - 1, 0) + 1
            y = x - k
            x_start, y_start = x, y
            while x < n and y < m and original[x] == modified[y]:
                x += 1
                y += 1
            v_forward[k] = x
            if odd and (k - delta) >= -(d - 1) and (k - delta) <= (d - 1):
                if v_forward[k] + v_backward.get(delta - k, 0) >= n:
                    return (x_start + x_offset, y_start + y_offset,
                            x + x_offset, y + y_offset, 2 * d - 1)
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v_backward.get(k - 1, 0) < v_backward.get(k + 1, 0)):
                x = v_backward.get(k + 1, 0)
            else:
                x = v_backward.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and original[n - 1 - x] == modified[m - 1 - y]:
                x += 1
                y += 1
            v_backward[k] = x
            if not odd and (k - delta) >= -d and (k - delta) <= d:
                if v_backward[k] + v_forward.get(delta - k, 0) >= n:
                    x_end = n - v_backward[k]
                    y_end = m - (v_backward[k] - k)
                    return (x_end + x_offset, y_end + y_offset,
                            n - x + x_offset, m - y + y_offset, 2 * d)
    return (0, 0, n, m, n + m)