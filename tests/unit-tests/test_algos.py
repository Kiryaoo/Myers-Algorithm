import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from algorithms.utils import (
    OpType, EditAction, EditScript, DiffResult, Hunk, TokenType,
    make_insert, make_delete, make_equal, make_replace,
    script_to_tuples, tuples_to_script, count_operations,
    tokenize_lines, tokenize_words, tokenize_chars,
    get_tokenizer, join_tokens, group_consecutive_ops,
    split_into_hunks, calculate_line_numbers
)
from algorithms.myers import (
    MyersDiff, diff, patch, edit_distance, lcs_length,
    similarity_ratio, find_middle_snake, SnakeInfo, EditGraphNode
)
from algorithms.hirschberg import (
    HirschbergDiff, diff_linear, LinearSpaceMyers,
    diff_linear_myers, DiffEngine, BatchDiffer
)


class TestCoreTypes(unittest.TestCase):
    def test_op_type(self):
        self.assertEqual(OpType.INSERT.value, 'insert')
        self.assertEqual(OpType.DELETE.value, 'delete')
        self.assertEqual(OpType.EQUAL.value, 'equal')
        self.assertEqual(list(OpType), [OpType.INSERT, OpType.DELETE, OpType.EQUAL, OpType.REPLACE])
        
    def test_edit_action(self):
        insert = EditAction(OpType.INSERT, 'line1')
        self.assertEqual((insert.op, insert.value), (OpType.INSERT, 'line1'))
        replace = EditAction(OpType.REPLACE, 'new', 'old')
        self.assertEqual(replace.old_value, 'old')
        self.assertIn('insert', repr(insert))
        self.assertEqual(insert[0], OpType.INSERT)
        
    def test_make_helpers(self):
        self.assertEqual(make_insert('a').op, OpType.INSERT)
        self.assertEqual(make_delete('b').op, OpType.DELETE)
        self.assertEqual(make_equal('c').op, OpType.EQUAL)
        self.assertEqual(make_replace('n', 'o').old_value, 'o')
        self.assertEqual(make_insert(42).value, 42)

    def test_diff_result(self):
        script = [make_equal('a'), make_insert('b')]
        result = DiffResult(script=script, original_length=1, modified_length=2,
                           edit_distance=1, lcs_length=1, similarity_ratio=0.666)
        self.assertEqual(result.original_length, 1)
        
        empty_result = DiffResult.from_script([], 0, 0)
        self.assertEqual(empty_result.similarity_ratio, 1.0)
        
        equal_result = DiffResult.from_script([make_equal('a'), make_equal('b')], 2, 2)
        self.assertEqual(equal_result.edit_distance, 0)


class TestTokenizers(unittest.TestCase):
    def test_tokenize_lines(self):
        self.assertEqual(tokenize_lines(''), [])
        self.assertEqual(tokenize_lines('hello'), ['hello'])
        self.assertEqual(tokenize_lines('a\nb\nc'), ['a', 'b', 'c'])
        
    def test_tokenize_words(self):
        self.assertEqual(tokenize_words(''), [])
        result = tokenize_words('hello world')
        self.assertIn('hello', result)
        self.assertEqual(''.join(tokenize_words('a  b')), 'a  b')
        
    def test_tokenize_chars(self):
        self.assertEqual(tokenize_chars(''), [])
        self.assertEqual(tokenize_chars('abc'), ['a', 'b', 'c'])
        
    def test_get_tokenizer(self):
        self.assertEqual(get_tokenizer(TokenType.LINE), tokenize_lines)
        self.assertEqual(get_tokenizer(TokenType.WORD), tokenize_words)
        self.assertEqual(get_tokenizer(TokenType.CHAR), tokenize_chars)
        
    def test_join_tokens(self):
        self.assertEqual(join_tokens(['a', 'b'], TokenType.LINE), 'a\nb')
        self.assertEqual(join_tokens(['a', ' ', 'b'], TokenType.WORD), 'a b')
        self.assertEqual(join_tokens(['a', 'b'], TokenType.CHAR), 'ab')
        self.assertEqual(join_tokens([], TokenType.LINE), '')


class TestScriptOperations(unittest.TestCase):
    def test_script_conversion(self):
        script = [make_insert('a'), make_delete('b'), make_equal('c')]
        tuples = script_to_tuples(script)
        self.assertEqual(tuples, [('insert', 'a'), ('delete', 'b'), ('equal', 'c')])
        restored = tuples_to_script(tuples)
        self.assertEqual(len(restored), 3)
        self.assertEqual(restored[0].op, OpType.INSERT)
        
    def test_count_operations(self):
        self.assertEqual(count_operations([])['total'], 0)
        script = [make_insert('a'), make_insert('b'), make_delete('c'), 
                  make_equal('d'), make_equal('e'), make_replace('f', 'g')]
        counts = count_operations(script)
        self.assertEqual(counts['inserts'], 2)
        self.assertEqual(counts['deletes'], 1)
        self.assertEqual(counts['equals'], 2)
        self.assertEqual(counts['replaces'], 1)
        
    def test_group_consecutive_ops(self):
        self.assertEqual(group_consecutive_ops([]), [])
        script = [make_equal('a'), make_equal('b'), make_delete('c'), make_insert('d')]
        groups = group_consecutive_ops(script)
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0], (OpType.EQUAL, ['a', 'b']))


class TestHunksAndLines(unittest.TestCase):
    def test_split_into_hunks(self):
        self.assertEqual(split_into_hunks([]), [])
        self.assertEqual(split_into_hunks([make_equal('a'), make_equal('b')]), [])
        
        script = [make_equal('a'), make_insert('b'), make_equal('c')]
        hunks = split_into_hunks(script, context=1)
        self.assertEqual(len(hunks), 1)
        self.assertIn(make_insert('b'), hunks[0])
        
    def test_calculate_line_numbers(self):
        self.assertEqual(calculate_line_numbers([]), [])
        self.assertEqual(calculate_line_numbers([make_equal('a'), make_equal('b')]), [(1, 1), (2, 2)])
        self.assertEqual(calculate_line_numbers([make_delete('a')]), [(1, None)])
        self.assertEqual(calculate_line_numbers([make_insert('a')]), [(None, 1)])
        
        mixed = [make_equal('a'), make_delete('b'), make_insert('c'), make_equal('d')]
        result = calculate_line_numbers(mixed)
        self.assertEqual(result, [(1, 1), (2, None), (None, 2), (3, 3)])


class TestMyersDiff(unittest.TestCase):
    def test_empty_sequences(self):
        self.assertEqual(MyersDiff([], []).compute(), [])
        self.assertTrue(all(a.op == OpType.INSERT for a in MyersDiff([], ['a', 'b']).compute()))
        self.assertTrue(all(a.op == OpType.DELETE for a in MyersDiff(['a', 'b'], []).compute()))
        
    def test_identical_sequences(self):
        script = MyersDiff(['a', 'b', 'c'], ['a', 'b', 'c']).compute()
        self.assertTrue(all(a.op == OpType.EQUAL for a in script))
        
    def test_single_changes(self):
        insert_script = MyersDiff(['a', 'c'], ['a', 'b', 'c']).compute()
        self.assertEqual(len([a for a in insert_script if a.op == OpType.INSERT]), 1)
        
        delete_script = MyersDiff(['a', 'b', 'c'], ['a', 'c']).compute()
        self.assertEqual(len([a for a in delete_script if a.op == OpType.DELETE]), 1)
        
    def test_complete_replacement(self):
        script = MyersDiff(['a', 'b'], ['x', 'y']).compute()
        changes = sum(1 for a in script if a.op in (OpType.DELETE, OpType.INSERT))
        self.assertEqual(changes, 4)
        
    def test_get_methods(self):
        md = MyersDiff(['a', 'b', 'c'], ['a', 'x', 'c'])
        self.assertEqual(md.get_edit_distance(), 2)
        result = md.get_result()
        self.assertIsInstance(result, DiffResult)


class TestDiffAndPatch(unittest.TestCase):
    def test_diff_function(self):
        script = diff(list('abc'), list('axc'))
        values = [a.value for a in script]
        self.assertIn('a', values)
        self.assertIn('c', values)
        
        int_script = diff([1, 2, 3], [1, 4, 3])
        self.assertEqual(len([a for a in int_script if a.op == OpType.EQUAL]), 2)
        
    def test_patch_basic(self):
        self.assertEqual(patch([], []), [])
        self.assertEqual(patch([], [make_insert('a'), make_insert('b')]), ['a', 'b'])
        self.assertEqual(patch(['a', 'b'], [make_delete('a'), make_delete('b')]), [])
        self.assertEqual(patch(['a', 'b'], [make_equal('a'), make_equal('b')]), ['a', 'b'])
        
    def test_patch_mixed(self):
        script = [make_equal('a'), make_delete('b'), make_insert('x'), make_equal('c')]
        self.assertEqual(patch(['a', 'b', 'c'], script), ['a', 'x', 'c'])
        
    def test_patch_errors(self):
        with self.assertRaises(ValueError):
            patch(['a'], [make_equal('x')])
        with self.assertRaises(ValueError):
            patch(['a'], [make_delete('x')])
        with self.assertRaises(ValueError):
            patch(['a', 'b'], [make_equal('a')])
            
    def test_roundtrip(self):
        original, modified = ['a', 'b', 'c', 'd', 'e'], ['a', 'x', 'c', 'y', 'e']
        self.assertEqual(patch(original, diff(original, modified)), modified)


class TestMetrics(unittest.TestCase):
    def test_edit_distance(self):
        self.assertEqual(edit_distance(['a', 'b', 'c'], ['a', 'b', 'c']), 0)
        self.assertEqual(edit_distance([], []), 0)
        self.assertGreaterEqual(edit_distance(['a', 'b'], []), 0)
        self.assertEqual(edit_distance(['a', 'b', 'c'], ['a', 'x', 'c']), 2)
        
    def test_lcs_length(self):
        self.assertEqual(lcs_length(['a', 'b', 'c'], ['a', 'b', 'c']), 3)
        self.assertEqual(lcs_length([], []), 0)
        self.assertEqual(lcs_length(['a', 'b'], ['x', 'y']), 0)
        self.assertEqual(lcs_length(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'y']), 2)
        
    def test_similarity_ratio(self):
        self.assertEqual(similarity_ratio(['a', 'b', 'c'], ['a', 'b', 'c']), 1.0)
        self.assertEqual(similarity_ratio([], []), 1.0)
        self.assertEqual(similarity_ratio(['a', 'b'], ['x', 'y']), 0.0)
        ratio = similarity_ratio(['a', 'b'], ['a', 'x'])
        self.assertTrue(0.0 < ratio < 1.0)


class TestGraphStructures(unittest.TestCase):
    def test_snake_info(self):
        snake = SnakeInfo(0, 0, 5, 5)
        self.assertEqual((snake.x_start, snake.y_start, snake.x_end, snake.y_end), (0, 0, 5, 5))
        self.assertEqual(snake.length, 5)
        
    def test_edit_graph_node(self):
        node = EditGraphNode(0, 0)
        self.assertEqual((node.x, node.y), (0, 0))
        self.assertIsNone(node.parent)
        
        parent = EditGraphNode(0, 0)
        child = EditGraphNode(1, 1, parent, OpType.EQUAL)
        self.assertEqual(child.parent, parent)
        
    def test_find_middle_snake(self):
        self.assertEqual(find_middle_snake([], [])[4], 0)
        self.assertEqual(find_middle_snake(['a'], [])[4], 1)
        result = find_middle_snake(['a', 'b'], ['a', 'b'])
        self.assertEqual(len(result), 5)


class TestHirschberg(unittest.TestCase):
    def test_empty_sequences(self):
        self.assertEqual(HirschbergDiff([], []).compute(), [])
        self.assertTrue(all(a.op == OpType.INSERT for a in HirschbergDiff([], ['a', 'b']).compute()))
        self.assertTrue(all(a.op == OpType.DELETE for a in HirschbergDiff(['a', 'b'], []).compute()))
        
    def test_identical_sequences(self):
        script = HirschbergDiff(['a', 'b', 'c'], ['a', 'b', 'c']).compute()
        self.assertGreaterEqual(len([a for a in script if a.op == OpType.EQUAL]), 3)
        
    def test_single_elements(self):
        self.assertIsInstance(HirschbergDiff(['a'], ['a', 'b', 'c']).compute(), list)
        self.assertIsInstance(HirschbergDiff(['a', 'b', 'c'], ['b']).compute(), list)


class TestLinearSpace(unittest.TestCase):
    def test_diff_linear(self):
        script = diff_linear(['a', 'b', 'c'], ['a', 'x', 'c'])
        self.assertIsInstance(script, list)
        equals = [a.value for a in script if a.op == OpType.EQUAL]
        self.assertIn('a', equals)
        
    def test_linear_space_myers(self):
        self.assertEqual(LinearSpaceMyers([], []).compute(), [])
        script = LinearSpaceMyers(['a', 'b', 'c'], ['a', 'x', 'c']).compute()
        self.assertIsInstance(script, list)
        
    def test_diff_linear_myers(self):
        self.assertIsInstance(diff_linear_myers(['a'], ['b']), list)
        script = diff_linear_myers(['a', 'b'], ['a', 'b'])
        self.assertEqual(sum(1 for a in script if a.op == OpType.EQUAL), 2)


class TestDiffEngine(unittest.TestCase):
    def test_modes(self):
        standard = DiffEngine(use_linear_space=False)
        self.assertIsInstance(standard.diff(['a', 'b'], ['a', 'x']), list)
        
        linear = DiffEngine(use_linear_space=True)
        self.assertIsInstance(linear.diff(['a', 'b'], ['a', 'x']), list)
        
    def test_diff_strings(self):
        engine = DiffEngine()
        self.assertIsInstance(engine.diff_strings("line1\nline2", "line1\nmod"), list)
        self.assertIsInstance(engine.diff_strings("abc", "axc", by_line=False), list)
        
    def test_compute_methods(self):
        engine = DiffEngine()
        lcs = engine.compute_lcs(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'y'])
        self.assertIn('a', lcs)
        self.assertIn('c', lcs)
        self.assertGreater(engine.compute_edit_distance(['a', 'b'], ['a', 'x']), 0)


class TestBatchDiffer(unittest.TestCase):
    def test_creation(self):
        bd = BatchDiffer()
        self.assertIsNotNone(bd.engine)
        
        engine = DiffEngine(use_linear_space=True)
        bd2 = BatchDiffer(engine)
        self.assertEqual(bd2.engine, engine)
        
    def test_diff_multiple(self):
        bd = BatchDiffer()
        pairs = [(['a', 'b'], ['a', 'x']), (['x', 'y'], ['x', 'y'])]
        results = bd.diff_multiple(pairs)
        self.assertEqual(len(results), 2)
        
    def test_diff_all_against_base(self):
        bd = BatchDiffer()
        results = bd.diff_all_against_base(['a', 'b'], [['a', 'b'], ['a', 'x'], ['x', 'y']])
        self.assertEqual(len(results), 3)


class TestConsistency(unittest.TestCase):
    def test_myers_hirschberg_consistency(self):
        original, modified = ['a', 'b', 'c', 'd', 'e'], ['a', 'x', 'c', 'y', 'e']
        myers_equals = sum(1 for a in diff(original, modified) if a.op == OpType.EQUAL)
        hirsch_equals = sum(1 for a in diff_linear(original, modified) if a.op == OpType.EQUAL)
        self.assertGreaterEqual(myers_equals, 2)
        self.assertGreaterEqual(hirsch_equals, 2)
        
    def test_patch_roundtrip(self):
        original, modified = ['line1', 'line2', 'line3'], ['line1', 'changed', 'line3']
        self.assertEqual(patch(original, diff(original, modified)), modified)


class TestEdgeCases(unittest.TestCase):
    def test_single_elements(self):
        script = diff(['a'], ['a'])
        self.assertEqual(script[0].op, OpType.EQUAL)
        
        script2 = diff(['a'], ['b'])
        self.assertEqual(sum(1 for a in script2 if a.op == OpType.DELETE), 1)
        self.assertEqual(sum(1 for a in script2 if a.op == OpType.INSERT), 1)
        
    def test_special_cases(self):
        self.assertIsInstance(diff(list('abcdefghij'), list('0123456789')), list)
        self.assertIsInstance(diff(['a', 'a', 'a'], ['a', 'b', 'a']), list)
        
    def test_unicode(self):
        script = diff(['привіт', 'світ'], ['привіт', 'мир'])
        equals = [a for a in script if a.op == OpType.EQUAL]
        self.assertTrue(any(a.value == 'привіт' for a in equals))


if __name__ == '__main__':
    unittest.main()
