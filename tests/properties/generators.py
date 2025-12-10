import random
import string
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class GeneratorMode(Enum):
    RANDOM = "random"
    SIMILAR = "similar"
    EDGE_CASE = "edge_case"


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


class SequenceGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        
    def generate_list(self, length: Optional[int] = None, item_length: int = 10) -> List[str]:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return [self._random_string(item_length) for _ in range(length)]
        
    def generate_char_list(self, length: Optional[int] = None) -> List[str]:
        if length is None:
            length = random.randint(self.config.min_length, self.config.max_length)
        return [random.choice(self.config.alphabet) for _ in range(length)]
    
    def _random_string(self, length: int) -> str:
        return ''.join(random.choice(self.config.alphabet) for _ in range(length))


class SimilarSequenceGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        
    def generate_pair(self, base_length: Optional[int] = None) -> Tuple[List[str], List[str]]:
        if base_length is None:
            base_length = random.randint(self.config.min_length, self.config.max_length)
        base = [f"line_{i}" for i in range(base_length)]
        modified = base.copy()
        num_changes = max(1, int(base_length * (1 - self.config.similarity_ratio)))
        for _ in range(num_changes):
            if not modified:
                break
            op = random.choice(['delete', 'insert', 'modify'])
            if op == 'delete' and modified:
                modified.pop(random.randint(0, len(modified) - 1))
            elif op == 'insert':
                modified.insert(random.randint(0, len(modified)), f"new_{random.randint(1000, 9999)}")
            elif op == 'modify' and modified:
                modified[random.randint(0, len(modified) - 1)] = f"mod_{random.randint(1000, 9999)}"
        return base, modified


class EdgeCaseGenerator:
    def empty_sequences(self) -> Tuple[List[str], List[str]]:
        return [], []
        
    def first_empty(self, length: int = 5) -> Tuple[List[str], List[str]]:
        return [], [f"line_{i}" for i in range(length)]
        
    def second_empty(self, length: int = 5) -> Tuple[List[str], List[str]]:
        return [f"line_{i}" for i in range(length)], []
        
    def identical_sequences(self, length: int = 10) -> Tuple[List[str], List[str]]:
        seq = [f"line_{i}" for i in range(length)]
        return seq.copy(), seq.copy()
        
    def completely_different(self, length: int = 5) -> Tuple[List[str], List[str]]:
        return [f"old_{i}" for i in range(length)], [f"new_{i}" for i in range(length)]
        
    def single_element(self) -> Tuple[List[str], List[str]]:
        return ["only"], ["only"]
        
    def reversed_sequence(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq = [f"line_{i}" for i in range(length)]
        return seq.copy(), list(reversed(seq))
        
    def duplicated_lines(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq = ["same"] * length
        modified = seq.copy()
        modified[length // 2] = "different"
        return seq, modified
        
    def long_common_prefix(self, prefix_len: int = 10, diff_len: int = 2) -> Tuple[List[str], List[str]]:
        prefix = [f"common_{i}" for i in range(prefix_len)]
        return prefix + [f"old_{i}" for i in range(diff_len)], prefix + [f"new_{i}" for i in range(diff_len)]
        
    def long_common_suffix(self, suffix_len: int = 10, diff_len: int = 2) -> Tuple[List[str], List[str]]:
        suffix = [f"common_{i}" for i in range(suffix_len)]
        return [f"old_{i}" for i in range(diff_len)] + suffix, [f"new_{i}" for i in range(diff_len)] + suffix
    
    def interleaved_sequences(self, length: int = 5) -> Tuple[List[str], List[str]]:
        seq1 = [f"a_{i}" for i in range(length)]
        interleaved = []
        for i, a in enumerate(seq1):
            interleaved.extend([a, f"b_{i}"])
        return seq1, interleaved


class DiffTestCase:
    def __init__(self, old: List[Any], new: List[Any], name: str = "", expected_distance: Optional[int] = None):
        self.old, self.new, self.name, self.expected_distance = old, new, name, expected_distance


class TestCaseGenerator:
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        self.seq_gen = SequenceGenerator(config)
        self.similar_gen = SimilarSequenceGenerator(config)
        self.edge_gen = EdgeCaseGenerator()
        
    def generate_random_case(self) -> DiffTestCase:
        return DiffTestCase(self.seq_gen.generate_list(), self.seq_gen.generate_list(), "random")
        
    def generate_similar_case(self) -> DiffTestCase:
        old, new = self.similar_gen.generate_pair()
        return DiffTestCase(old, new, "similar")
        
    def generate_edge_cases(self) -> List[DiffTestCase]:
        cases = [
            DiffTestCase(*self.edge_gen.empty_sequences(), "empty_both", 0),
            DiffTestCase(*self.edge_gen.first_empty(), "first_empty"),
            DiffTestCase(*self.edge_gen.second_empty(), "second_empty"),
            DiffTestCase(*self.edge_gen.identical_sequences(), "identical", 0),
            DiffTestCase(*self.edge_gen.completely_different(), "completely_different"),
            DiffTestCase(*self.edge_gen.single_element(), "single_element", 0),
            DiffTestCase(*self.edge_gen.reversed_sequence(), "reversed"),
            DiffTestCase(*self.edge_gen.duplicated_lines(), "duplicated"),
            DiffTestCase(*self.edge_gen.long_common_prefix(), "common_prefix"),
            DiffTestCase(*self.edge_gen.long_common_suffix(), "common_suffix"),
        ]
        return cases
        
    def generate_batch(self, count: int, mode: GeneratorMode = GeneratorMode.RANDOM) -> List[DiffTestCase]:
        if mode == GeneratorMode.EDGE_CASE:
            return self.generate_edge_cases()
        gen = self.generate_similar_case if mode == GeneratorMode.SIMILAR else self.generate_random_case
        return [gen() for _ in range(count)]


def generate_random_sequences(count: int = 10, max_length: int = 50) -> List[Tuple[List[str], List[str]]]:
    gen = SequenceGenerator(GeneratorConfig(max_length=max_length))
    return [(gen.generate_list(), gen.generate_list()) for _ in range(count)]


def generate_similar_sequences(count: int = 10, max_length: int = 50, similarity: float = 0.8) -> List[Tuple[List[str], List[str]]]:
    gen = SimilarSequenceGenerator(GeneratorConfig(max_length=max_length, similarity_ratio=similarity))
    return [gen.generate_pair() for _ in range(count)]


def generate_edge_cases() -> List[Tuple[List[str], List[str]]]:
    g = EdgeCaseGenerator()
    return [g.empty_sequences(), g.first_empty(), g.second_empty(), g.identical_sequences(),
            g.completely_different(), g.single_element(), g.reversed_sequence(), g.duplicated_lines(),
            g.long_common_prefix(), g.long_common_suffix(), g.interleaved_sequences()]


def generate_test_cases(count: int = 20) -> List[DiffTestCase]:
    gen = TestCaseGenerator()
    cases = gen.generate_edge_cases()
    for _ in range(count // 2):
        cases.append(gen.generate_random_case())
        cases.append(gen.generate_similar_case())
    return cases
