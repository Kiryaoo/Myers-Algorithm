import random
import string
from typing import List, Tuple, Optional, Callable, Any, Iterator, Generator
from dataclasses import dataclass
from enum import Enum


class GeneratorMode(Enum):
    RANDOM = "random"
    SIMILAR = "similar"
    DIFFERENT = "different"
    EDGE_CASE = "edge_case"
    REALISTIC = "realistic"


@dataclass
class GeneratorConfig:
    min_length: int = 1
    max_length: int = 100
    alphabet: str = string.ascii_lowercase
    seed: Optional[int] = None
    similarity_ratio: float = 0.7
    
    def __post_init__(self):
        if self.seed is not None:
            random.seed(self.seed)


class RandomStringGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        
    def generate(self, length: Optional[int] = None) -> str:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return ''.join(random.choice(self.config.alphabet) for _ in range(length))
        
    def generate_many(self, count: int) -> List[str]:
        return [self.generate() for _ in range(count)]
        
    def generate_with_prefix(self, prefix: str, length: int) -> str:
        suffix_len = max(0, length - len(prefix))
        return prefix + self.generate(suffix_len)
        
    def generate_with_suffix(self, suffix: str, length: int) -> str:
        prefix_len = max(0, length - len(suffix))
        return self.generate(prefix_len) + suffix


class SequenceGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.string_gen = RandomStringGenerator(config)
        
    def generate_list(self, length: Optional[int] = None, item_length: int = 10) -> List[str]:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return [self.string_gen.generate(item_length) for _ in range(length)]
        
    def generate_integer_list(self, length: Optional[int] = None, min_val: int = 0, max_val: int = 100) -> List[int]:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return [random.randint(min_val, max_val) for _ in range(length)]
        
    def generate_char_list(self, length: Optional[int] = None) -> List[str]:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return [random.choice(self.config.alphabet) for _ in range(length)]


class SimilarSequenceGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        
    def generate_pair(self, base_length: Optional[int] = None) -> Tuple[List[str], List[str]]:
        if base_length is None:
            base_length = random.randint(self.config.min_length, self.config.max_length)
        base = [f"line_{i}" for i in range(base_length)]
        modified = base.copy()
        num_changes = int(base_length * (1 - self.config.similarity_ratio))
        num_changes = max(1, num_changes)
        for _ in range(num_changes):
            if not modified:
                break
            op = random.choice(['delete', 'insert', 'modify'])
            if op == 'delete' and modified:
                idx = random.randint(0, len(modified) - 1)
                modified.pop(idx)
            elif op == 'insert':
                idx = random.randint(0, len(modified))
                modified.insert(idx, f"new_line_{random.randint(1000, 9999)}")
            elif op == 'modify' and modified:
                idx = random.randint(0, len(modified) - 1)
                modified[idx] = f"modified_{random.randint(1000, 9999)}"
        return base, modified
        
    def generate_with_insertions(self, base: List[str], num_insertions: int) -> List[str]:
        result = base.copy()
        for _ in range(num_insertions):
            idx = random.randint(0, len(result))
            result.insert(idx, f"inserted_{random.randint(1000, 9999)}")
        return result
        
    def generate_with_deletions(self, base: List[str], num_deletions: int) -> List[str]:
        result = base.copy()
        num_deletions = min(num_deletions, len(result) - 1)
        for _ in range(num_deletions):
            if result:
                idx = random.randint(0, len(result) - 1)
                result.pop(idx)
        return result
        
    def generate_with_modifications(self, base: List[str], num_modifications: int) -> List[str]:
        result = base.copy()
        indices = random.sample(range(len(result)), min(num_modifications, len(result)))
        for idx in indices:
            result[idx] = f"modified_{random.randint(1000, 9999)}"
        return result


class EdgeCaseGenerator:
    def empty_sequences(self) -> Tuple[List[str], List[str]]:
        return [], []
        
    def first_empty(self, second_length: int = 5) -> Tuple[List[str], List[str]]:
        return [], [f"line_{i}" for i in range(second_length)]
        
    def second_empty(self, first_length: int = 5) -> Tuple[List[str], List[str]]:
        return [f"line_{i}" for i in range(first_length)], []
        
    def identical_sequences(self, length: int = 10) -> Tuple[List[str], List[str]]:
        seq = [f"line_{i}" for i in range(length)]
        return seq.copy(), seq.copy()
        
    def completely_different(self, length: int = 5) -> Tuple[List[str], List[str]]:
        return [f"old_{i}" for i in range(length)], [f"new_{i}" for i in range(length)]
        
    def single_element(self) -> Tuple[List[str], List[str]]:
        return ["only"], ["only"]
        
    def single_char_diff(self) -> Tuple[List[str], List[str]]:
        return ["abc"], ["abd"]
        
    def reversed_sequence(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq = [f"line_{i}" for i in range(length)]
        return seq.copy(), list(reversed(seq))
        
    def interleaved_sequences(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq1 = [f"a_{i}" for i in range(length)]
        seq2 = [f"b_{i}" for i in range(length)]
        interleaved = []
        for a, b in zip(seq1, seq2):
            interleaved.extend([a, b])
        return seq1, interleaved
        
    def duplicated_lines(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq = ["same_line"] * length
        modified = seq.copy()
        modified[length // 2] = "different_line"
        return seq, modified
        
    def long_common_prefix(self, prefix_len: int = 10, diff_len: int = 2) -> Tuple[List[str], List[str]]:
        prefix = [f"common_{i}" for i in range(prefix_len)]
        seq1 = prefix + [f"old_{i}" for i in range(diff_len)]
        seq2 = prefix + [f"new_{i}" for i in range(diff_len)]
        return seq1, seq2
        
    def long_common_suffix(self, suffix_len: int = 10, diff_len: int = 2) -> Tuple[List[str], List[str]]:
        suffix = [f"common_{i}" for i in range(suffix_len)]
        seq1 = [f"old_{i}" for i in range(diff_len)] + suffix
        seq2 = [f"new_{i}" for i in range(diff_len)] + suffix
        return seq1, seq2


class RealisticCodeGenerator:
    def __init__(self):
        self.indent = "    "
        
    def generate_function(self, name: str, num_lines: int = 5) -> List[str]:
        lines = [f"def {name}():"]
        for i in range(num_lines):
            lines.append(f"{self.indent}statement_{i} = value_{i}")
        lines.append(f"{self.indent}return result")
        return lines
        
    def generate_class(self, name: str, num_methods: int = 3) -> List[str]:
        lines = [f"class {name}:"]
        lines.append(f"{self.indent}def __init__(self):")
        lines.append(f"{self.indent}{self.indent}self.value = None")
        lines.append("")
        for i in range(num_methods):
            lines.append(f"{self.indent}def method_{i}(self):")
            lines.append(f"{self.indent}{self.indent}return self.value + {i}")
            lines.append("")
        return lines
        
    def generate_import_block(self, num_imports: int = 5) -> List[str]:
        modules = ["os", "sys", "json", "typing", "dataclasses", "enum", "re", "math"]
        selected = random.sample(modules, min(num_imports, len(modules)))
        return [f"import {m}" for m in selected]
        
    def generate_file(self, num_functions: int = 3, num_classes: int = 1) -> List[str]:
        lines = self.generate_import_block()
        lines.append("")
        lines.append("")
        for i in range(num_classes):
            lines.extend(self.generate_class(f"Class{i}"))
            lines.append("")
        for i in range(num_functions):
            lines.extend(self.generate_function(f"function_{i}"))
            lines.append("")
        return lines
        
    def modify_file(self, lines: List[str], num_changes: int = 3) -> List[str]:
        result = lines.copy()
        for _ in range(num_changes):
            if not result:
                break
            op = random.choice(['add_line', 'remove_line', 'modify_line'])
            if op == 'add_line':
                idx = random.randint(0, len(result))
                result.insert(idx, f"{self.indent}# Added comment {random.randint(1, 100)}")
            elif op == 'remove_line' and len(result) > 1:
                idx = random.randint(0, len(result) - 1)
                result.pop(idx)
            elif op == 'modify_line':
                idx = random.randint(0, len(result) - 1)
                if result[idx].strip().startswith('#'):
                    result[idx] = f"{self.indent}# Modified comment"
                else:
                    result[idx] = result[idx] + "  # modified"
        return result


class DiffTestCase:
    def __init__(self, old: List[Any], new: List[Any], name: str = "", expected_distance: Optional[int] = None):
        self.old = old
        self.new = new
        self.name = name
        self.expected_distance = expected_distance
        
    def __repr__(self) -> str:
        return f"DiffTestCase({self.name}, old_len={len(self.old)}, new_len={len(self.new)})"


class TestCaseGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.seq_gen = SequenceGenerator(config)
        self.similar_gen = SimilarSequenceGenerator(config)
        self.edge_gen = EdgeCaseGenerator()
        self.code_gen = RealisticCodeGenerator()
        
    def generate_random_case(self) -> DiffTestCase:
        old = self.seq_gen.generate_list()
        new = self.seq_gen.generate_list()
        return DiffTestCase(old, new, "random")
        
    def generate_similar_case(self) -> DiffTestCase:
        old, new = self.similar_gen.generate_pair()
        return DiffTestCase(old, new, "similar")
        
    def generate_edge_cases(self) -> List[DiffTestCase]:
        cases = []
        old, new = self.edge_gen.empty_sequences()
        cases.append(DiffTestCase(old, new, "empty_both", 0))
        old, new = self.edge_gen.first_empty()
        cases.append(DiffTestCase(old, new, "first_empty", len(new)))
        old, new = self.edge_gen.second_empty()
        cases.append(DiffTestCase(old, new, "second_empty", len(old)))
        old, new = self.edge_gen.identical_sequences()
        cases.append(DiffTestCase(old, new, "identical", 0))
        old, new = self.edge_gen.completely_different()
        cases.append(DiffTestCase(old, new, "completely_different"))
        old, new = self.edge_gen.single_element()
        cases.append(DiffTestCase(old, new, "single_element", 0))
        old, new = self.edge_gen.reversed_sequence()
        cases.append(DiffTestCase(old, new, "reversed"))
        old, new = self.edge_gen.duplicated_lines()
        cases.append(DiffTestCase(old, new, "duplicated"))
        old, new = self.edge_gen.long_common_prefix()
        cases.append(DiffTestCase(old, new, "common_prefix"))
        old, new = self.edge_gen.long_common_suffix()
        cases.append(DiffTestCase(old, new, "common_suffix"))
        return cases
        
    def generate_code_case(self) -> DiffTestCase:
        old = self.code_gen.generate_file()
        new = self.code_gen.modify_file(old)
        return DiffTestCase(old, new, "code_modification")
        
    def generate_batch(self, count: int, mode: GeneratorMode = GeneratorMode.RANDOM) -> List[DiffTestCase]:
        cases = []
        for i in range(count):
            if mode == GeneratorMode.RANDOM:
                cases.append(self.generate_random_case())
            elif mode == GeneratorMode.SIMILAR:
                cases.append(self.generate_similar_case())
            elif mode == GeneratorMode.EDGE_CASE:
                cases.extend(self.generate_edge_cases())
            elif mode == GeneratorMode.REALISTIC:
                cases.append(self.generate_code_case())
            else:
                cases.append(self.generate_random_case())
        return cases


class SequenceIterator:
    def __init__(self, generator: Callable[[], Tuple[List[Any], List[Any]]], count: int):
        self.generator = generator
        self.count = count
        self.current = 0
        
    def __iter__(self) -> Iterator[Tuple[List[Any], List[Any]]]:
        return self
        
    def __next__(self) -> Tuple[List[Any], List[Any]]:
        if self.current >= self.count:
            raise StopIteration
        self.current += 1
        return self.generator()


class InfiniteSequenceGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.seq_gen = SequenceGenerator(config)
        self.similar_gen = SimilarSequenceGenerator(config)
        
    def random_pairs(self) -> Generator[Tuple[List[str], List[str]], None, None]:
        while True:
            yield self.seq_gen.generate_list(), self.seq_gen.generate_list()
            
    def similar_pairs(self) -> Generator[Tuple[List[str], List[str]], None, None]:
        while True:
            yield self.similar_gen.generate_pair()
            
    def mixed_pairs(self) -> Generator[Tuple[List[str], List[str]], None, None]:
        generators = [
            lambda: (self.seq_gen.generate_list(), self.seq_gen.generate_list()),
            self.similar_gen.generate_pair,
        ]
        while True:
            gen = random.choice(generators)
            yield gen()


class LoadTestGenerator:
    def __init__(self):
        self.results = []
        
    def generate_scaling_test(self, sizes: List[int]) -> List[DiffTestCase]:
        cases = []
        for size in sizes:
            old = [f"line_{i}" for i in range(size)]
            new = old.copy()
            num_changes = max(1, size // 10)
            for _ in range(num_changes):
                idx = random.randint(0, len(new) - 1)
                new[idx] = f"modified_{random.randint(1000, 9999)}"
            cases.append(DiffTestCase(old, new, f"scale_{size}"))
        return cases
        
    def generate_worst_case(self, size: int) -> DiffTestCase:
        old = [f"a_{i}" for i in range(size)]
        new = [f"b_{i}" for i in range(size)]
        return DiffTestCase(old, new, f"worst_case_{size}")
        
    def generate_best_case(self, size: int) -> DiffTestCase:
        seq = [f"line_{i}" for i in range(size)]
        return DiffTestCase(seq.copy(), seq.copy(), f"best_case_{size}")


def generate_random_sequences(count: int = 10, max_length: int = 50) -> List[Tuple[List[str], List[str]]]:
    config = GeneratorConfig(max_length=max_length)
    gen = SequenceGenerator(config)
    return [(gen.generate_list(), gen.generate_list()) for _ in range(count)]


def generate_similar_sequences(count: int = 10, max_length: int = 50, similarity: float = 0.8) -> List[Tuple[List[str], List[str]]]:
    config = GeneratorConfig(max_length=max_length, similarity_ratio=similarity)
    gen = SimilarSequenceGenerator(config)
    return [gen.generate_pair() for _ in range(count)]


def generate_edge_cases() -> List[Tuple[List[str], List[str]]]:
    gen = EdgeCaseGenerator()
    return [
        gen.empty_sequences(),
        gen.first_empty(),
        gen.second_empty(),
        gen.identical_sequences(),
        gen.completely_different(),
        gen.single_element(),
        gen.reversed_sequence(),
        gen.duplicated_lines(),
        gen.long_common_prefix(),
        gen.long_common_suffix(),
        gen.interleaved_sequences(),
    ]


def generate_test_cases(count: int = 20) -> List[DiffTestCase]:
    gen = TestCaseGenerator()
    cases = gen.generate_edge_cases()
    for _ in range(count // 2):
        cases.append(gen.generate_random_case())
    for _ in range(count // 2):
        cases.append(gen.generate_similar_case())
    return cases
