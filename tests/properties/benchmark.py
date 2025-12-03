import time
import random
import sys
import os
from typing import List, Tuple, Callable, Any, Dict
from dataclasses import dataclass
from statistics import mean, stdev, median

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from algorithms.myers import MyersDiff, diff as myers_diff
from algorithms.hirschberg import HirschbergDiff, LinearSpaceMyers
from helpers.naive_diff import NaiveDiff, naive_diff


@dataclass
class BenchmarkResult:
    name: str
    input_size: int
    times: List[float]
    
    @property
    def mean_time(self) -> float:
        return mean(self.times)
        
    @property
    def std_time(self) -> float:
        if len(self.times) < 2:
            return 0.0
        return stdev(self.times)
        
    @property
    def median_time(self) -> float:
        return median(self.times)
        
    @property
    def min_time(self) -> float:
        return min(self.times)
        
    @property
    def max_time(self) -> float:
        return max(self.times)
        
    def __repr__(self) -> str:
        return (
            f"BenchmarkResult({self.name}, size={self.input_size}, "
            f"mean={self.mean_time*1000:.3f}ms, "
            f"std={self.std_time*1000:.3f}ms)"
        )


class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    def start(self):
        self.start_time = time.perf_counter()
        
    def stop(self) -> float:
        self.end_time = time.perf_counter()
        return self.elapsed
        
    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.perf_counter()
        return end - self.start_time
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, *args):
        self.stop()


class DataGenerator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        
    def generate_random_pair(self, size: int) -> Tuple[List[str], List[str]]:
        old = [f"line_{i}_{random.randint(0, 100)}" for i in range(size)]
        new = [f"line_{i}_{random.randint(0, 100)}" for i in range(size)]
        return old, new
        
    def generate_similar_pair(self, size: int, similarity: float = 0.8) -> Tuple[List[str], List[str]]:
        old = [f"line_{i}" for i in range(size)]
        new = old.copy()
        num_changes = int(size * (1 - similarity))
        for _ in range(num_changes):
            idx = random.randint(0, len(new) - 1)
            new[idx] = f"modified_{random.randint(1000, 9999)}"
        return old, new
        
    def generate_worst_case(self, size: int) -> Tuple[List[str], List[str]]:
        old = [f"a_{i}" for i in range(size)]
        new = [f"b_{i}" for i in range(size)]
        return old, new
        
    def generate_best_case(self, size: int) -> Tuple[List[str], List[str]]:
        seq = [f"line_{i}" for i in range(size)]
        return seq.copy(), seq.copy()
        
    def generate_real_code_like(self, size: int) -> Tuple[List[str], List[str]]:
        old = []
        for i in range(size):
            if i % 10 == 0:
                old.append(f"def function_{i // 10}():")
            elif i % 10 == 9:
                old.append("")
            else:
                old.append(f"    statement_{i} = value")
        new = old.copy()
        num_changes = max(1, size // 20)
        for _ in range(num_changes):
            idx = random.randint(0, len(new) - 1)
            new[idx] = f"    # modified at {idx}"
        return old, new


class Benchmark:
    def __init__(self, iterations: int = 5, warmup: int = 1):
        self.iterations = iterations
        self.warmup = warmup
        self.results: List[BenchmarkResult] = []
        self.data_gen = DataGenerator()
        
    def run_single(
        self,
        func: Callable[[List[str], List[str]], Any],
        old: List[str],
        new: List[str]
    ) -> float:
        timer = Timer()
        timer.start()
        func(old, new)
        return timer.stop()
        
    def benchmark_function(
        self,
        name: str,
        func: Callable[[List[str], List[str]], Any],
        old: List[str],
        new: List[str]
    ) -> BenchmarkResult:
        for _ in range(self.warmup):
            func(old, new)
        times = []
        for _ in range(self.iterations):
            elapsed = self.run_single(func, old, new)
            times.append(elapsed)
        result = BenchmarkResult(name, len(old), times)
        self.results.append(result)
        return result
        
    def compare_algorithms(
        self,
        old: List[str],
        new: List[str]
    ) -> Dict[str, BenchmarkResult]:
        def hirschberg_diff(o, n):
            return HirschbergDiff(o, n).compute()
        def linear_myers_diff(o, n):
            return LinearSpaceMyers(o, n).compute()
        algorithms = {
            'Myers': myers_diff,
            'Hirschberg': hirschberg_diff,
            'LinearSpaceMyers': linear_myers_diff,
        }
        results = {}
        for name, func in algorithms.items():
            result = self.benchmark_function(name, func, old, new)
            results[name] = result
        return results


class ScalingBenchmark:
    def __init__(self, sizes: List[int] = None):
        self.sizes = sizes or [10, 50, 100, 200, 500]
        self.benchmark = Benchmark(iterations=3, warmup=1)
        self.data_gen = DataGenerator()
        self.results: Dict[str, List[BenchmarkResult]] = {}
        
    def run_scaling_test(self, test_type: str = "similar") -> Dict[str, List[BenchmarkResult]]:
        self.results = {
            'Myers': [],
            'Hirschberg': [],
            'LinearSpaceMyers': [],
        }
        for size in self.sizes:
            if test_type == "similar":
                old, new = self.data_gen.generate_similar_pair(size)
            elif test_type == "worst":
                old, new = self.data_gen.generate_worst_case(size)
            elif test_type == "best":
                old, new = self.data_gen.generate_best_case(size)
            else:
                old, new = self.data_gen.generate_random_pair(size)
            comparison = self.benchmark.compare_algorithms(old, new)
            for algo_name, result in comparison.items():
                self.results[algo_name].append(result)
        return self.results
        
    def print_results(self):
        print("\n" + "=" * 70)
        print("SCALING BENCHMARK RESULTS")
        print("=" * 70)
        print(f"{'Size':<10}", end="")
        for algo in self.results.keys():
            print(f"{algo:<20}", end="")
        print()
        print("-" * 70)
        for i, size in enumerate(self.sizes):
            print(f"{size:<10}", end="")
            for algo, results in self.results.items():
                time_ms = results[i].mean_time * 1000
                print(f"{time_ms:>8.3f} ms          ", end="")
            print()


class MemoryBenchmark:
    def __init__(self):
        self.results = []
        
    def estimate_memory(self, size: int) -> Dict[str, int]:
        return {
            'Myers': size * 2 * 8,
            'Hirschberg': size * 8,
            'Naive_LCS': size * size * 8,
        }
        
    def run(self, sizes: List[int]) -> List[Dict[str, int]]:
        self.results = []
        for size in sizes:
            self.results.append({
                'size': size,
                'memory': self.estimate_memory(size)
            })
        return self.results
        
    def print_results(self):
        print("\n" + "=" * 70)
        print("MEMORY USAGE ESTIMATES (bytes)")
        print("=" * 70)
        print(f"{'Size':<10}{'Myers':<15}{'Hirschberg':<15}{'Naive LCS':<15}")
        print("-" * 70)
        for result in self.results:
            size = result['size']
            mem = result['memory']
            print(f"{size:<10}{mem['Myers']:<15}{mem['Hirschberg']:<15}{mem['Naive_LCS']:<15}")


class AlgorithmComparison:
    def __init__(self):
        self.data_gen = DataGenerator()
        
    def verify_correctness(self, old: List[str], new: List[str]) -> bool:
        myers_result = myers_diff(old, new)
        hirsch_result = HirschbergDiff(old, new).compute()
        linear_result = LinearSpaceMyers(old, new).compute()
        def reconstruct(actions):
            result = []
            for a in actions:
                if hasattr(a, 'op'):
                    from algorithms.utils import OpType
                    if a.op in (OpType.EQUAL, OpType.INSERT):
                        result.append(a.value)
            return result
        myers_new = reconstruct(myers_result)
        hirsch_new = reconstruct(hirsch_result)
        linear_new = reconstruct(linear_result)
        return myers_new == new and hirsch_new == new and linear_new == new
        
    def run_correctness_tests(self, num_tests: int = 20) -> Tuple[int, int]:
        passed = 0
        failed = 0
        for i in range(num_tests):
            size = random.randint(10, 50)
            old, new = self.data_gen.generate_similar_pair(size)
            if self.verify_correctness(old, new):
                passed += 1
            else:
                failed += 1
        return passed, failed


def run_quick_benchmark():
    print("Running Quick Benchmark...")
    print("=" * 50)
    benchmark = Benchmark(iterations=3, warmup=1)
    data_gen = DataGenerator()
    sizes = [50, 100, 200]
    for size in sizes:
        print(f"\nSize: {size}")
        old, new = data_gen.generate_similar_pair(size, 0.9)
        results = benchmark.compare_algorithms(old, new)
        for name, result in results.items():
            print(f"  {name}: {result.mean_time*1000:.3f}ms")


def run_full_benchmark():
    print("Running Full Benchmark Suite...")
    print("=" * 70)
    scaling = ScalingBenchmark(sizes=[10, 25, 50, 100, 200])
    print("\n--- Similar Sequences (90% similarity) ---")
    scaling.run_scaling_test("similar")
    scaling.print_results()
    print("\n--- Best Case (identical) ---")
    scaling.run_scaling_test("best")
    scaling.print_results()
    print("\n--- Memory Estimates ---")
    mem_bench = MemoryBenchmark()
    mem_bench.run([100, 500, 1000, 5000])
    mem_bench.print_results()
    print("\n--- Correctness Verification ---")
    comparison = AlgorithmComparison()
    passed, failed = comparison.run_correctness_tests(30)
    print(f"Correctness Tests: {passed} passed, {failed} failed")


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_full_benchmark()
    else:
        run_quick_benchmark()


if __name__ == "__main__":
    main()
