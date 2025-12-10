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
    GeneratorMode,
    generate_random_sequences,
    generate_similar_sequences,
    generate_edge_cases,
    generate_test_cases
)

class TestDiffProperties(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=42, max_length=20)
        self.test_gen = TestCaseGenerator(self.config)

    def _reconstruct_new(self, actions: List[EditAction]) -> List[str]:
        return [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]

    def _reconstruct_old(self, actions: List[EditAction]) -> List[str]:
        return [a.value for a in actions if a.op in (OpType.EQUAL, OpType.DELETE)]

    def test_basic_roundtrip_and_empty_cases(self):
        cases = [self.test_gen.generate_random_case(), *self.test_gen.generate_edge_cases()[:3]]
        for case in cases:
            actions = myers_diff(case.old, case.new)
            self.assertEqual(self._reconstruct_new(actions), case.new)
            if case.old:
                self.assertEqual(self._reconstruct_old(actions), case.old)

    def test_minimality_and_identical(self):
        for _ in range(8):
            case = self.test_gen.generate_similar_case()
            actions = myers_diff(case.old, case.new)
            myers_changes = sum(1 for a in actions if a.op != OpType.EQUAL)
            naive_changes = naive_edit_distance(case.old, case.new)
            self.assertLessEqual(myers_changes, naive_changes + 1)
        seq = [f"line_{i}" for i in range(5)]
        self.assertFalse(any(a.op != OpType.EQUAL for a in myers_diff(seq, seq.copy())))

class TestMyersVsNaive(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(seed=123, max_length=15)
        self.seq_gen = SequenceGenerator(self.config)
        self.similar_gen = SimilarSequenceGenerator(self.config)

    def _verify(self, old, new):
        actions = myers_diff(old, new)
        reconstructed = [a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)]
        return reconstructed == new

    def test_basic_random_and_similar(self):
        for _ in range(10):
            old = self.seq_gen.generate_char_list(random.randint(3, 10))
            new = self.seq_gen.generate_char_list(random.randint(3, 10))
            self.assertTrue(self._verify(old, new))
        for _ in range(8):
            old, new = self.similar_gen.generate_pair(random.randint(5, 12))
            self.assertTrue(self._verify(old, new))

class TestHirschbergProperties(unittest.TestCase):
    def setUp(self):
        self.similar_gen = SimilarSequenceGenerator(GeneratorConfig(seed=456, max_length=20))

    def test_hirschberg_matches_myers_and_roundtrips(self):
        for _ in range(8):
            old, new = self.similar_gen.generate_pair(random.randint(5, 15))
            h_actions = HirschbergDiff(old, new).compute()
            m_actions = myers_diff(old, new)
            self.assertEqual([a.value for a in h_actions if a.op in (OpType.EQUAL, OpType.INSERT)],
                             [a.value for a in m_actions if a.op in (OpType.EQUAL, OpType.INSERT)])
            self.assertEqual([a.value for a in h_actions if a.op in (OpType.EQUAL, OpType.INSERT)], new)

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
    def test_sequence_and_similar_generators(self):
        gen = SequenceGenerator(GeneratorConfig(min_length=3, max_length=6))
        for _ in range(6):
            seq = gen.generate_list()
            self.assertTrue(3 <= len(seq) <= 6)
        sgen = SimilarSequenceGenerator(GeneratorConfig(similarity_ratio=0.7))
        old, new = sgen.generate_pair(10)
        self.assertIsInstance(old, list)
        self.assertIsInstance(new, list)
        self.assertTrue(len(new) > 0)

class TestStressSmall(unittest.TestCase):
    def test_multiple_small_diffs(self):
        gen = SequenceGenerator(GeneratorConfig(seed=303, max_length=8))
        for _ in range(30):
            old = gen.generate_char_list()
            new = gen.generate_char_list()
            actions = myers_diff(old, new)
            self.assertEqual([a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)], new)

class TestSpecialCases(unittest.TestCase):
    def test_single_char_and_repeats(self):
        cases = [(['a'], ['a']), (['a'], ['b']), ([], ['a']), (['x']*5, ['x']*5)]
        for old, new in cases:
            actions = myers_diff(old, new)
            self.assertEqual([a.value for a in actions if a.op in (OpType.EQUAL, OpType.INSERT)], new)

class TestDeterminismAndBoundary(unittest.TestCase):
    def test_determinism_and_length_extremes(self):
        old = ['line_1', 'line_2', 'line_3']
        new = ['line_1', 'modified', 'line_3']
        first = [a.value for a in myers_diff(old, new) if a.op in (OpType.EQUAL, OpType.INSERT)]
        for _ in range(5):
            self.assertEqual(first, [a.value for a in myers_diff(old, new) if a.op in (OpType.EQUAL, OpType.INSERT)])
        self.assertEqual([a.value for a in myers_diff(['a']*2, ['b']*10) if a.op in (OpType.EQUAL, OpType.INSERT)], ['b']*10)
        self.assertEqual([a.value for a in myers_diff(['x']*10, ['y']*2) if a.op in (OpType.EQUAL, OpType.INSERT)], ['y']*2)

if __name__ == '__main__':
    unittest.main(verbosity=2)