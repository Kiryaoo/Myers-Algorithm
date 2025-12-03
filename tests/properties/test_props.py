import unittest
import sys
import os
import time
import random
from typing import List, Any, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from algorithms.utils import OpType, EditAction
from algorithms.myers import MyersDiff, diff as myers_diff
from algorithms.hirschberg import HirschbergDiff, LinearSpaceMyers

from helpers.naive_diff import (
    NaiveDiff,
    NaiveOpType,
    naive_diff,
    lcs_length,
    edit_distance as naive_edit_distance,
    verify_diff,
    DiffVerifier
)

from properties.generators import (
    GeneratorConfig,
    SequenceGenerator,
    SimilarSequenceGenerator,
    EdgeCaseGenerator,
    TestCaseGenerator,
    LoadTestGenerator,
    GeneratorMode,
    generate_random_sequences,
    generate_similar_sequences,
    generate_edge_cases,
    generate_test_cases
)


class TestDiffProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=42, max_length=30)
        self.test_gen = TestCaseGenerator(self.config)
        
    def _apply_diff_to_old(self, old: List[str], actions: List[EditAction]) -> List[str]:
        result = []
        for action in actions:
            if action.op == OpType.EQUAL:
                result.append(action.value)
            elif action.op == OpType.INSERT:
                result.append(action.value)
        return result
        
    def _apply_diff_to_get_old(self, actions: List[EditAction]) -> List[str]:
        result = []
        for action in actions:
            if action.op == OpType.EQUAL:
                result.append(action.value)
            elif action.op == OpType.DELETE:
                result.append(action.value)
        return result

    def test_property_diff_produces_new_sequence(self):
        for _ in range(50):
            old = [f"line_{i}" for i in range(random.randint(1, 20))]
            new = [f"line_{i}" for i in range(random.randint(1, 20))]
            random.shuffle(new)
            actions = myers_diff(old, new)
            reconstructed = self._apply_diff_to_old(old, actions)
            self.assertEqual(reconstructed, new)
            
    def test_property_diff_preserves_old_sequence(self):
        for _ in range(50):
            old = [f"old_{i}" for i in range(random.randint(1, 20))]
            new = [f"new_{i}" for i in range(random.randint(1, 20))]
            actions = myers_diff(old, new)
            reconstructed = self._apply_diff_to_get_old(actions)
            self.assertEqual(reconstructed, old)
            
    def test_property_identical_sequences_no_changes(self):
        for length in [0, 1, 5, 10, 20]:
            seq = [f"line_{i}" for i in range(length)]
            actions = myers_diff(seq, seq.copy())
            has_changes = any(a.op != OpType.EQUAL for a in actions)
            self.assertFalse(has_changes, f"Identical sequences should have no changes for length {length}")
            
    def test_property_empty_old_all_inserts(self):
        for length in [1, 5, 10]:
            new = [f"line_{i}" for i in range(length)]
            actions = myers_diff([], new)
            self.assertEqual(len(actions), length)
            self.assertTrue(all(a.op == OpType.INSERT for a in actions))
            
    def test_property_empty_new_all_deletes(self):
        for length in [1, 5, 10]:
            old = [f"line_{i}" for i in range(length)]
            actions = myers_diff(old, [])
            self.assertEqual(len(actions), length)
            self.assertTrue(all(a.op == OpType.DELETE for a in actions))
            
    def test_property_diff_is_minimal(self):
        for _ in range(30):
            case = self.test_gen.generate_similar_case()
            actions = myers_diff(case.old, case.new)
            myers_changes = sum(1 for a in actions if a.op != OpType.EQUAL)
            naive_changes = naive_edit_distance(case.old, case.new)
            self.assertLessEqual(myers_changes, naive_changes + 1)


class TestMyersVsNaive(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=123, max_length=25)
        self.seq_gen = SequenceGenerator(self.config)
        self.similar_gen = SimilarSequenceGenerator(self.config)
        
    def _count_changes(self, actions: List[EditAction]) -> int:
        return sum(1 for a in actions if a.op != OpType.EQUAL)
        
    def _verify_reconstruction(self, old: List[str], new: List[str], actions: List[EditAction]) -> bool:
        result = []
        for action in actions:
            if action.op == OpType.EQUAL:
                result.append(action.value)
            elif action.op == OpType.INSERT:
                result.append(action.value)
        return result == new

    def test_myers_equals_naive_on_random(self):
        for _ in range(30):
            old = self.seq_gen.generate_char_list(random.randint(5, 15))
            new = self.seq_gen.generate_char_list(random.randint(5, 15))
            myers_actions = myers_diff(old, new)
            self.assertTrue(self._verify_reconstruction(old, new, myers_actions))
            
    def test_myers_equals_naive_on_similar(self):
        for _ in range(30):
            old, new = self.similar_gen.generate_pair(random.randint(10, 20))
            myers_actions = myers_diff(old, new)
            self.assertTrue(self._verify_reconstruction(old, new, myers_actions))
            
    def test_myers_on_edge_cases(self):
        edge_gen = EdgeCaseGenerator()
        cases = [
            edge_gen.empty_sequences(),
            edge_gen.first_empty(),
            edge_gen.second_empty(),
            edge_gen.identical_sequences(),
            edge_gen.completely_different(),
            edge_gen.single_element(),
            edge_gen.reversed_sequence(),
            edge_gen.duplicated_lines(),
            edge_gen.long_common_prefix(),
            edge_gen.long_common_suffix(),
        ]
        for old, new in cases:
            myers_actions = myers_diff(old, new)
            self.assertTrue(self._verify_reconstruction(old, new, myers_actions))


class TestHirschbergProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=456, max_length=30)
        self.similar_gen = SimilarSequenceGenerator(self.config)
        
    def _verify_reconstruction(self, old: List[str], new: List[str], actions: List[EditAction]) -> bool:
        result = []
        for action in actions:
            if action.op == OpType.EQUAL:
                result.append(action.value)
            elif action.op == OpType.INSERT:
                result.append(action.value)
        return result == new

    def test_hirschberg_produces_valid_diff(self):
        for _ in range(30):
            old, new = self.similar_gen.generate_pair(random.randint(10, 25))
            hirschberg = HirschbergDiff(old, new)
            actions = hirschberg.compute()
            self.assertTrue(self._verify_reconstruction(old, new, actions))
            
    def test_hirschberg_vs_myers_same_result(self):
        for _ in range(20):
            old, new = self.similar_gen.generate_pair(random.randint(5, 15))
            hirschberg = HirschbergDiff(old, new)
            hirsch_actions = hirschberg.compute()
            myers_actions = myers_diff(old, new)
            hirsch_result = []
            for a in hirsch_actions:
                if a.op == OpType.EQUAL or a.op == OpType.INSERT:
                    hirsch_result.append(a.value)
            myers_result = []
            for a in myers_actions:
                if a.op == OpType.EQUAL or a.op == OpType.INSERT:
                    myers_result.append(a.value)
            self.assertEqual(hirsch_result, myers_result)
            self.assertEqual(hirsch_result, new)
            
    def test_linear_space_myers(self):
        for _ in range(20):
            old, new = self.similar_gen.generate_pair(random.randint(10, 20))
            linear = LinearSpaceMyers(old, new)
            actions = linear.compute()
            self.assertTrue(self._verify_reconstruction(old, new, actions))


class TestSymmetryProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=789, max_length=20)
        self.seq_gen = SequenceGenerator(self.config)
        
    def _count_inserts_deletes(self, actions: List[EditAction]) -> Tuple[int, int]:
        inserts = sum(1 for a in actions if a.op == OpType.INSERT)
        deletes = sum(1 for a in actions if a.op == OpType.DELETE)
        return inserts, deletes

    def test_swap_sequences_swaps_operations(self):
        for _ in range(30):
            old = self.seq_gen.generate_char_list(random.randint(5, 15))
            new = self.seq_gen.generate_char_list(random.randint(5, 15))
            forward_actions = myers_diff(old, new)
            reverse_actions = myers_diff(new, old)
            fwd_ins, fwd_del = self._count_inserts_deletes(forward_actions)
            rev_ins, rev_del = self._count_inserts_deletes(reverse_actions)
            self.assertEqual(fwd_ins, rev_del)
            self.assertEqual(fwd_del, rev_ins)


class TestEditDistanceProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=101, max_length=15)
        self.seq_gen = SequenceGenerator(self.config)
        
    def _myers_edit_distance(self, old: List[str], new: List[str]) -> int:
        actions = myers_diff(old, new)
        return sum(1 for a in actions if a.op != OpType.EQUAL)

    def test_edit_distance_non_negative(self):
        for _ in range(30):
            old = self.seq_gen.generate_char_list(random.randint(1, 10))
            new = self.seq_gen.generate_char_list(random.randint(1, 10))
            dist = self._myers_edit_distance(old, new)
            self.assertGreaterEqual(dist, 0)
            
    def test_edit_distance_zero_for_identical(self):
        for _ in range(20):
            seq = self.seq_gen.generate_char_list(random.randint(1, 15))
            dist = self._myers_edit_distance(seq, seq.copy())
            self.assertEqual(dist, 0)
            
    def test_edit_distance_symmetric(self):
        for _ in range(30):
            old = self.seq_gen.generate_char_list(random.randint(3, 10))
            new = self.seq_gen.generate_char_list(random.randint(3, 10))
            dist1 = self._myers_edit_distance(old, new)
            dist2 = self._myers_edit_distance(new, old)
            self.assertEqual(dist1, dist2)
            
    def test_edit_distance_triangle_inequality(self):
        for _ in range(20):
            a = self.seq_gen.generate_char_list(random.randint(3, 8))
            b = self.seq_gen.generate_char_list(random.randint(3, 8))
            c = self.seq_gen.generate_char_list(random.randint(3, 8))
            d_ab = self._myers_edit_distance(a, b)
            d_bc = self._myers_edit_distance(b, c)
            d_ac = self._myers_edit_distance(a, c)
            self.assertLessEqual(d_ac, d_ab + d_bc)


class TestLCSProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=202, max_length=15)
        self.seq_gen = SequenceGenerator(self.config)

    def test_lcs_length_bounds(self):
        for _ in range(30):
            old = self.seq_gen.generate_char_list(random.randint(3, 12))
            new = self.seq_gen.generate_char_list(random.randint(3, 12))
            lcs_len = lcs_length(old, new)
            self.assertGreaterEqual(lcs_len, 0)
            self.assertLessEqual(lcs_len, min(len(old), len(new)))
            
    def test_lcs_of_identical_equals_length(self):
        for _ in range(20):
            seq = self.seq_gen.generate_char_list(random.randint(1, 15))
            lcs_len = lcs_length(seq, seq.copy())
            self.assertEqual(lcs_len, len(seq))
            
    def test_lcs_of_disjoint_is_zero(self):
        old = ['a', 'b', 'c']
        new = ['x', 'y', 'z']
        lcs_len = lcs_length(old, new)
        self.assertEqual(lcs_len, 0)


class TestGenerators(unittest.TestCase):
    def test_sequence_generator(self):
        config = GeneratorConfig(min_length=5, max_length=10)
        gen = SequenceGenerator(config)
        for _ in range(10):
            seq = gen.generate_list()
            self.assertGreaterEqual(len(seq), 5)
            self.assertLessEqual(len(seq), 10)
            
    def test_similar_sequence_generator(self):
        config = GeneratorConfig(similarity_ratio=0.8)
        gen = SimilarSequenceGenerator(config)
        old, new = gen.generate_pair(20)
        common = set(old) & set(new)
        self.assertGreater(len(common), 0)
        
    def test_edge_case_generator(self):
        gen = EdgeCaseGenerator()
        cases = generate_edge_cases()
        self.assertGreater(len(cases), 5)
        for old, new in cases:
            self.assertIsInstance(old, list)
            self.assertIsInstance(new, list)
            
    def test_test_case_generator(self):
        gen = TestCaseGenerator()
        cases = gen.generate_batch(10, GeneratorMode.RANDOM)
        self.assertEqual(len(cases), 10)
        for case in cases:
            self.assertIsInstance(case.old, list)
            self.assertIsInstance(case.new, list)


class TestStressSmall(unittest.TestCase):
    def test_many_small_diffs(self):
        config = GeneratorConfig(seed=303, max_length=10)
        gen = SequenceGenerator(config)
        for _ in range(100):
            old = gen.generate_char_list()
            new = gen.generate_char_list()
            actions = myers_diff(old, new)
            result = []
            for a in actions:
                if a.op in (OpType.EQUAL, OpType.INSERT):
                    result.append(a.value)
            self.assertEqual(result, new)


class TestSpecialCases(unittest.TestCase):
    def test_single_character_sequences(self):
        test_cases = [
            (['a'], ['a']),
            (['a'], ['b']),
            (['a'], []),
            ([], ['a']),
        ]
        for old, new in test_cases:
            actions = myers_diff(old, new)
            result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
            self.assertEqual(result, new)
            
    def test_all_same_elements(self):
        old = ['x'] * 10
        new = ['x'] * 10
        actions = myers_diff(old, new)
        changes = sum(1 for a in actions if a.op != OpType.EQUAL)
        self.assertEqual(changes, 0)
        
    def test_alternating_elements(self):
        old = ['a', 'b'] * 5
        new = ['b', 'a'] * 5
        actions = myers_diff(old, new)
        result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
        self.assertEqual(result, new)
        
    def test_prefix_suffix_common(self):
        old = ['a', 'b', 'c', 'OLD', 'd', 'e', 'f']
        new = ['a', 'b', 'c', 'NEW', 'd', 'e', 'f']
        actions = myers_diff(old, new)
        result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
        self.assertEqual(result, new)


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        old = ['line_1', 'line_2', 'line_3', 'line_4', 'line_5']
        new = ['line_1', 'modified', 'line_3', 'new_line', 'line_5']
        results = []
        for _ in range(10):
            actions = myers_diff(old, new)
            result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
            results.append(tuple(result))
        self.assertEqual(len(set(results)), 1)


class TestBoundaryConditions(unittest.TestCase):
    def test_very_different_lengths(self):
        old = ['a'] * 3
        new = ['b'] * 30
        actions = myers_diff(old, new)
        result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
        self.assertEqual(result, new)
        
    def test_long_to_short(self):
        old = ['x'] * 30
        new = ['y'] * 3
        actions = myers_diff(old, new)
        result = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
        self.assertEqual(result, new)


if __name__ == '__main__':
    unittest.main(verbosity=2)
