import sys
import os
import unittest
from typing import List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.algorithms.utils import (
    OpType, EditAction, EditScript, DiffResult, Hunk, TokenType,
    make_insert, make_delete, make_equal, make_replace,
    script_to_tuples, tuples_to_script, count_operations,
    tokenize_lines, tokenize_words, tokenize_chars,
    get_tokenizer, join_tokens, group_consecutive_ops,
    split_into_hunks, calculate_line_numbers
)
from src.algorithms.myers import (
    MyersDiff, diff, patch, edit_distance, lcs_length,
    similarity_ratio, find_middle_snake, SnakeInfo, EditGraphNode
)
from src.algorithms.hirschberg import (
    HirschbergDiff, diff_linear, LinearSpaceMyers,
    diff_linear_myers, DiffEngine, BatchDiffer
)


class TestOpType(unittest.TestCase):
    def test_op_type_values(self):
        self.assertEqual(OpType.INSERT.value, 'insert')
        self.assertEqual(OpType.DELETE.value, 'delete')
        self.assertEqual(OpType.EQUAL.value, 'equal')
        self.assertEqual(OpType.REPLACE.value, 'replace')
        
    def test_op_type_is_string_enum(self):
        self.assertIsInstance(OpType.INSERT, str)
        self.assertIsInstance(OpType.DELETE, str)
        
    def test_op_type_comparison(self):
        self.assertEqual(OpType.INSERT, 'insert')
        self.assertNotEqual(OpType.INSERT, OpType.DELETE)
        
    def test_op_type_iteration(self):
        ops = list(OpType)
        self.assertEqual(len(ops), 4)
        self.assertIn(OpType.INSERT, ops)
        self.assertIn(OpType.DELETE, ops)


class TestEditAction(unittest.TestCase):
    def test_create_insert_action(self):
        action = EditAction(OpType.INSERT, 'line1')
        self.assertEqual(action.op, OpType.INSERT)
        self.assertEqual(action.value, 'line1')
        self.assertIsNone(action.old_value)
        
    def test_create_delete_action(self):
        action = EditAction(OpType.DELETE, 'removed')
        self.assertEqual(action.op, OpType.DELETE)
        self.assertEqual(action.value, 'removed')
        
    def test_create_equal_action(self):
        action = EditAction(OpType.EQUAL, 'unchanged')
        self.assertEqual(action.op, OpType.EQUAL)
        self.assertEqual(action.value, 'unchanged')
        
    def test_create_replace_action(self):
        action = EditAction(OpType.REPLACE, 'new', 'old')
        self.assertEqual(action.op, OpType.REPLACE)
        self.assertEqual(action.value, 'new')
        self.assertEqual(action.old_value, 'old')
        
    def test_edit_action_repr(self):
        insert = EditAction(OpType.INSERT, 'x')
        self.assertIn('insert', repr(insert))
        replace = EditAction(OpType.REPLACE, 'new', 'old')
        self.assertIn('replace', repr(replace))
        self.assertIn('new', repr(replace))
        self.assertIn('old', repr(replace))
        
    def test_edit_action_named_tuple_access(self):
        action = EditAction(OpType.DELETE, 'val', None)
        self.assertEqual(action[0], OpType.DELETE)
        self.assertEqual(action[1], 'val')
        self.assertEqual(action[2], None)


class TestMakeHelpers(unittest.TestCase):
    def test_make_insert(self):
        action = make_insert('new_line')
        self.assertEqual(action.op, OpType.INSERT)
        self.assertEqual(action.value, 'new_line')
        
    def test_make_delete(self):
        action = make_delete('old_line')
        self.assertEqual(action.op, OpType.DELETE)
        self.assertEqual(action.value, 'old_line')
        
    def test_make_equal(self):
        action = make_equal('same')
        self.assertEqual(action.op, OpType.EQUAL)
        self.assertEqual(action.value, 'same')
        
    def test_make_replace(self):
        action = make_replace('new', 'old')
        self.assertEqual(action.op, OpType.REPLACE)
        self.assertEqual(action.value, 'new')
        self.assertEqual(action.old_value, 'old')
        
    def test_make_with_different_types(self):
        int_action = make_insert(42)
        self.assertEqual(int_action.value, 42)
        list_action = make_delete([1, 2, 3])
        self.assertEqual(list_action.value, [1, 2, 3])


class TestDiffResult(unittest.TestCase):
    def test_diff_result_creation(self):
        script = [make_equal('a'), make_insert('b')]
        result = DiffResult(
            script=script,
            original_length=1,
            modified_length=2,
            edit_distance=1,
            lcs_length=1,
            similarity_ratio=0.666
        )
        self.assertEqual(result.original_length, 1)
        self.assertEqual(result.modified_length, 2)
        self.assertEqual(len(result.script), 2)
        
    def test_diff_result_from_script_empty(self):
        result = DiffResult.from_script([], 0, 0)
        self.assertEqual(result.edit_distance, 0)
        self.assertEqual(result.lcs_length, 0)
        self.assertEqual(result.similarity_ratio, 1.0)
        
    def test_diff_result_from_script_all_equal(self):
        script = [make_equal('a'), make_equal('b'), make_equal('c')]
        result = DiffResult.from_script(script, 3, 3)
        self.assertEqual(result.edit_distance, 0)
        self.assertEqual(result.lcs_length, 3)
        self.assertEqual(result.similarity_ratio, 1.0)
        
    def test_diff_result_from_script_all_different(self):
        script = [make_delete('a'), make_insert('b')]
        result = DiffResult.from_script(script, 1, 1)
        self.assertEqual(result.edit_distance, 2)
        self.assertEqual(result.lcs_length, 0)
        self.assertEqual(result.similarity_ratio, 0.0)
        
    def test_diff_result_from_script_mixed(self):
        script = [make_equal('a'), make_delete('b'), make_insert('c'), make_equal('d')]
        result = DiffResult.from_script(script, 3, 3)
        self.assertEqual(result.edit_distance, 2)
        self.assertEqual(result.lcs_length, 2)


class TestTokenizers(unittest.TestCase):
    def test_tokenize_lines_empty(self):
        self.assertEqual(tokenize_lines(''), [])
        
    def test_tokenize_lines_single(self):
        result = tokenize_lines('hello')
        self.assertEqual(result, ['hello'])
        
    def test_tokenize_lines_multiple(self):
        result = tokenize_lines('line1\nline2\nline3')
        self.assertEqual(result, ['line1', 'line2', 'line3'])
        
    def test_tokenize_lines_trailing_newline(self):
        result = tokenize_lines('a\nb\n')
        self.assertEqual(result, ['a', 'b', ''])
        
    def test_tokenize_words_empty(self):
        self.assertEqual(tokenize_words(''), [])
        
    def test_tokenize_words_simple(self):
        result = tokenize_words('hello world')
        self.assertIn('hello', result)
        self.assertIn('world', result)
        
    def test_tokenize_words_preserves_whitespace(self):
        result = tokenize_words('a  b')
        joined = ''.join(result)
        self.assertEqual(joined, 'a  b')
        
    def test_tokenize_chars_empty(self):
        self.assertEqual(tokenize_chars(''), [])
        
    def test_tokenize_chars_simple(self):
        result = tokenize_chars('abc')
        self.assertEqual(result, ['a', 'b', 'c'])
        
    def test_tokenize_chars_with_spaces(self):
        result = tokenize_chars('a b')
        self.assertEqual(result, ['a', ' ', 'b'])


class TestGetTokenizer(unittest.TestCase):
    def test_get_line_tokenizer(self):
        tokenizer = get_tokenizer(TokenType.LINE)
        self.assertEqual(tokenizer, tokenize_lines)
        
    def test_get_word_tokenizer(self):
        tokenizer = get_tokenizer(TokenType.WORD)
        self.assertEqual(tokenizer, tokenize_words)
        
    def test_get_char_tokenizer(self):
        tokenizer = get_tokenizer(TokenType.CHAR)
        self.assertEqual(tokenizer, tokenize_chars)


class TestJoinTokens(unittest.TestCase):
    def test_join_lines(self):
        tokens = ['line1', 'line2', 'line3']
        result = join_tokens(tokens, TokenType.LINE)
        self.assertEqual(result, 'line1\nline2\nline3')
        
    def test_join_words(self):
        tokens = ['hello', ' ', 'world']
        result = join_tokens(tokens, TokenType.WORD)
        self.assertEqual(result, 'hello world')
        
    def test_join_chars(self):
        tokens = ['a', 'b', 'c']
        result = join_tokens(tokens, TokenType.CHAR)
        self.assertEqual(result, 'abc')
        
    def test_join_empty(self):
        self.assertEqual(join_tokens([], TokenType.LINE), '')
        self.assertEqual(join_tokens([], TokenType.WORD), '')
        self.assertEqual(join_tokens([], TokenType.CHAR), '')


class TestScriptConversion(unittest.TestCase):
    def test_script_to_tuples(self):
        script = [make_insert('a'), make_delete('b'), make_equal('c')]
        tuples = script_to_tuples(script)
        self.assertEqual(tuples, [('insert', 'a'), ('delete', 'b'), ('equal', 'c')])
        
    def test_tuples_to_script(self):
        tuples = [('insert', 'x'), ('delete', 'y')]
        script = tuples_to_script(tuples)
        self.assertEqual(len(script), 2)
        self.assertEqual(script[0].op, OpType.INSERT)
        self.assertEqual(script[0].value, 'x')
        
    def test_roundtrip_conversion(self):
        original = [make_equal('a'), make_insert('b'), make_delete('c')]
        tuples = script_to_tuples(original)
        restored = tuples_to_script(tuples)
        self.assertEqual(len(original), len(restored))
        for orig, rest in zip(original, restored):
            self.assertEqual(orig.op, rest.op)
            self.assertEqual(orig.value, rest.value)


class TestCountOperations(unittest.TestCase):
    def test_count_empty(self):
        counts = count_operations([])
        self.assertEqual(counts['total'], 0)
        self.assertEqual(counts['inserts'], 0)
        self.assertEqual(counts['deletes'], 0)
        
    def test_count_all_types(self):
        script = [
            make_insert('a'), make_insert('b'),
            make_delete('c'),
            make_equal('d'), make_equal('e'), make_equal('f'),
            make_replace('g', 'h')
        ]
        counts = count_operations(script)
        self.assertEqual(counts['inserts'], 2)
        self.assertEqual(counts['deletes'], 1)
        self.assertEqual(counts['equals'], 3)
        self.assertEqual(counts['replaces'], 1)
        self.assertEqual(counts['total'], 7)


class TestGroupConsecutiveOps(unittest.TestCase):
    def test_group_empty(self):
        self.assertEqual(group_consecutive_ops([]), [])
        
    def test_group_single(self):
        script = [make_insert('a')]
        groups = group_consecutive_ops(script)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], (OpType.INSERT, ['a']))
        
    def test_group_consecutive_same(self):
        script = [make_insert('a'), make_insert('b'), make_insert('c')]
        groups = group_consecutive_ops(script)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0], (OpType.INSERT, ['a', 'b', 'c']))
        
    def test_group_alternating(self):
        script = [make_insert('a'), make_delete('b'), make_insert('c')]
        groups = group_consecutive_ops(script)
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0][0], OpType.INSERT)
        self.assertEqual(groups[1][0], OpType.DELETE)
        self.assertEqual(groups[2][0], OpType.INSERT)
        
    def test_group_mixed_sequences(self):
        script = [
            make_equal('a'), make_equal('b'),
            make_delete('c'), make_delete('d'),
            make_insert('e')
        ]
        groups = group_consecutive_ops(script)
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0], (OpType.EQUAL, ['a', 'b']))
        self.assertEqual(groups[1], (OpType.DELETE, ['c', 'd']))
        self.assertEqual(groups[2], (OpType.INSERT, ['e']))


class TestSplitIntoHunks(unittest.TestCase):
    def test_split_empty(self):
        self.assertEqual(split_into_hunks([]), [])
        
    def test_split_all_equal(self):
        script = [make_equal('a'), make_equal('b')]
        hunks = split_into_hunks(script)
        self.assertEqual(hunks, [])
        
    def test_split_single_change(self):
        script = [make_equal('a'), make_insert('b'), make_equal('c')]
        hunks = split_into_hunks(script, context=1)
        self.assertEqual(len(hunks), 1)
        self.assertIn(make_insert('b'), hunks[0])
        
    def test_split_with_context(self):
        script = [
            make_equal('1'), make_equal('2'), make_equal('3'),
            make_insert('new'),
            make_equal('4'), make_equal('5'), make_equal('6')
        ]
        hunks = split_into_hunks(script, context=2)
        self.assertEqual(len(hunks), 1)
        
    def test_split_multiple_hunks(self):
        script = [
            make_equal('1'), make_insert('a'),
            make_equal('2'), make_equal('3'), make_equal('4'),
            make_equal('5'), make_equal('6'), make_equal('7'),
            make_delete('b'), make_equal('8')
        ]
        hunks = split_into_hunks(script, context=1)
        self.assertGreaterEqual(len(hunks), 1)


class TestCalculateLineNumbers(unittest.TestCase):
    def test_empty_script(self):
        result = calculate_line_numbers([])
        self.assertEqual(result, [])
        
    def test_all_equal(self):
        script = [make_equal('a'), make_equal('b')]
        result = calculate_line_numbers(script)
        self.assertEqual(result, [(1, 1), (2, 2)])
        
    def test_delete_only(self):
        script = [make_delete('a'), make_delete('b')]
        result = calculate_line_numbers(script)
        self.assertEqual(result, [(1, None), (2, None)])
        
    def test_insert_only(self):
        script = [make_insert('a'), make_insert('b')]
        result = calculate_line_numbers(script)
        self.assertEqual(result, [(None, 1), (None, 2)])
        
    def test_mixed_operations(self):
        script = [make_equal('a'), make_delete('b'), make_insert('c'), make_equal('d')]
        result = calculate_line_numbers(script)
        self.assertEqual(result[0], (1, 1))
        self.assertEqual(result[1], (2, None))
        self.assertEqual(result[2], (None, 2))
        self.assertEqual(result[3], (3, 3))


class TestMyersDiff(unittest.TestCase):
    def test_diff_empty_sequences(self):
        md = MyersDiff([], [])
        script = md.compute()
        self.assertEqual(script, [])
        
    def test_diff_empty_original(self):
        md = MyersDiff([], ['a', 'b'])
        script = md.compute()
        self.assertEqual(len(script), 2)
        self.assertTrue(all(a.op == OpType.INSERT for a in script))
        
    def test_diff_empty_modified(self):
        md = MyersDiff(['a', 'b'], [])
        script = md.compute()
        self.assertEqual(len(script), 2)
        self.assertTrue(all(a.op == OpType.DELETE for a in script))
        
    def test_diff_identical(self):
        md = MyersDiff(['a', 'b', 'c'], ['a', 'b', 'c'])
        script = md.compute()
        self.assertEqual(len(script), 3)
        self.assertTrue(all(a.op == OpType.EQUAL for a in script))
        
    def test_diff_single_insert(self):
        md = MyersDiff(['a', 'c'], ['a', 'b', 'c'])
        script = md.compute()
        inserts = [a for a in script if a.op == OpType.INSERT]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(inserts[0].value, 'b')
        
    def test_diff_single_delete(self):
        md = MyersDiff(['a', 'b', 'c'], ['a', 'c'])
        script = md.compute()
        deletes = [a for a in script if a.op == OpType.DELETE]
        self.assertEqual(len(deletes), 1)
        self.assertEqual(deletes[0].value, 'b')
        
    def test_diff_complete_replacement(self):
        md = MyersDiff(['a', 'b'], ['x', 'y'])
        script = md.compute()
        deletes = sum(1 for a in script if a.op == OpType.DELETE)
        inserts = sum(1 for a in script if a.op == OpType.INSERT)
        self.assertEqual(deletes + inserts, 4)
        
    def test_get_edit_distance(self):
        md = MyersDiff(['a', 'b', 'c'], ['a', 'x', 'c'])
        dist = md.get_edit_distance()
        self.assertEqual(dist, 2)
        
    def test_get_result(self):
        md = MyersDiff(['a', 'b'], ['a', 'b'])
        result = md.get_result()
        self.assertIsInstance(result, DiffResult)
        self.assertEqual(result.edit_distance, 0)
        self.assertEqual(result.similarity_ratio, 1.0)


class TestDiffFunction(unittest.TestCase):
    def test_diff_strings(self):
        script = diff(list('abc'), list('axc'))
        values = [a.value for a in script]
        self.assertIn('a', values)
        self.assertIn('c', values)
        
    def test_diff_integers(self):
        script = diff([1, 2, 3], [1, 4, 3])
        equals = [a for a in script if a.op == OpType.EQUAL]
        self.assertEqual(len(equals), 2)
        
    def test_diff_preserves_order(self):
        original = ['a', 'b', 'c', 'd', 'e']
        modified = ['a', 'x', 'c', 'y', 'e']
        script = diff(original, modified)
        result = patch(original, script)
        self.assertEqual(result, modified)


class TestPatchFunction(unittest.TestCase):
    def test_patch_empty(self):
        result = patch([], [])
        self.assertEqual(result, [])
        
    def test_patch_inserts_only(self):
        script = [make_insert('a'), make_insert('b')]
        result = patch([], script)
        self.assertEqual(result, ['a', 'b'])
        
    def test_patch_deletes_only(self):
        script = [make_delete('a'), make_delete('b')]
        result = patch(['a', 'b'], script)
        self.assertEqual(result, [])
        
    def test_patch_equals_only(self):
        script = [make_equal('a'), make_equal('b')]
        result = patch(['a', 'b'], script)
        self.assertEqual(result, ['a', 'b'])
        
    def test_patch_mixed(self):
        original = ['a', 'b', 'c']
        script = [make_equal('a'), make_delete('b'), make_insert('x'), make_equal('c')]
        result = patch(original, script)
        self.assertEqual(result, ['a', 'x', 'c'])
        
    def test_patch_raises_on_mismatch(self):
        script = [make_equal('x')]
        with self.assertRaises(ValueError):
            patch(['a'], script)
            
    def test_patch_raises_on_delete_mismatch(self):
        script = [make_delete('x')]
        with self.assertRaises(ValueError):
            patch(['a'], script)
            
    def test_patch_raises_on_incomplete(self):
        script = [make_equal('a')]
        with self.assertRaises(ValueError):
            patch(['a', 'b'], script)


class TestEditDistanceFunction(unittest.TestCase):
    def test_edit_distance_identical(self):
        dist = edit_distance(['a', 'b', 'c'], ['a', 'b', 'c'])
        self.assertEqual(dist, 0)
        
    def test_edit_distance_empty(self):
        dist = edit_distance([], [])
        self.assertEqual(dist, 0)
        
    def test_edit_distance_one_empty(self):
        dist = edit_distance(['a', 'b'], [])
        self.assertEqual(dist, 2)
        dist = edit_distance([], ['a', 'b'])
        self.assertEqual(dist, 2)
        
    def test_edit_distance_single_change(self):
        dist = edit_distance(['a', 'b', 'c'], ['a', 'x', 'c'])
        self.assertEqual(dist, 2)


class TestLcsLength(unittest.TestCase):
    def test_lcs_identical(self):
        length = lcs_length(['a', 'b', 'c'], ['a', 'b', 'c'])
        self.assertEqual(length, 3)
        
    def test_lcs_empty(self):
        length = lcs_length([], [])
        self.assertEqual(length, 0)
        
    def test_lcs_no_common(self):
        length = lcs_length(['a', 'b'], ['x', 'y'])
        self.assertEqual(length, 0)
        
    def test_lcs_partial(self):
        length = lcs_length(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'y'])
        self.assertEqual(length, 2)


class TestSimilarityRatio(unittest.TestCase):
    def test_similarity_identical(self):
        ratio = similarity_ratio(['a', 'b', 'c'], ['a', 'b', 'c'])
        self.assertEqual(ratio, 1.0)
        
    def test_similarity_empty(self):
        ratio = similarity_ratio([], [])
        self.assertEqual(ratio, 1.0)
        
    def test_similarity_no_common(self):
        ratio = similarity_ratio(['a', 'b'], ['x', 'y'])
        self.assertEqual(ratio, 0.0)
        
    def test_similarity_partial(self):
        ratio = similarity_ratio(['a', 'b'], ['a', 'x'])
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 1.0)


class TestSnakeInfo(unittest.TestCase):
    def test_snake_info_creation(self):
        snake = SnakeInfo(0, 0, 5, 5)
        self.assertEqual(snake.x_start, 0)
        self.assertEqual(snake.y_start, 0)
        self.assertEqual(snake.x_end, 5)
        self.assertEqual(snake.y_end, 5)
        
    def test_snake_length(self):
        snake = SnakeInfo(2, 3, 7, 8)
        self.assertEqual(snake.length, 5)


class TestEditGraphNode(unittest.TestCase):
    def test_node_creation(self):
        node = EditGraphNode(0, 0)
        self.assertEqual(node.x, 0)
        self.assertEqual(node.y, 0)
        self.assertIsNone(node.parent)
        self.assertIsNone(node.op)
        
    def test_node_with_parent(self):
        parent = EditGraphNode(0, 0)
        child = EditGraphNode(1, 1, parent, OpType.EQUAL)
        self.assertEqual(child.parent, parent)
        self.assertEqual(child.op, OpType.EQUAL)


class TestFindMiddleSnake(unittest.TestCase):
    def test_find_middle_snake_empty(self):
        result = find_middle_snake([], [])
        self.assertEqual(result[4], 0)
        
    def test_find_middle_snake_one_empty(self):
        result = find_middle_snake(['a'], [])
        self.assertEqual(result[4], 1)
        
    def test_find_middle_snake_identical(self):
        result = find_middle_snake(['a', 'b'], ['a', 'b'])
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 5)


class TestHirschbergDiff(unittest.TestCase):
    def test_hirschberg_empty(self):
        hd = HirschbergDiff([], [])
        script = hd.compute()
        self.assertEqual(script, [])
        
    def test_hirschberg_empty_original(self):
        hd = HirschbergDiff([], ['a', 'b'])
        script = hd.compute()
        self.assertEqual(len(script), 2)
        self.assertTrue(all(a.op == OpType.INSERT for a in script))
        
    def test_hirschberg_empty_modified(self):
        hd = HirschbergDiff(['a', 'b'], [])
        script = hd.compute()
        self.assertEqual(len(script), 2)
        self.assertTrue(all(a.op == OpType.DELETE for a in script))
        
    def test_hirschberg_identical(self):
        hd = HirschbergDiff(['a', 'b', 'c'], ['a', 'b', 'c'])
        script = hd.compute()
        equals = [a for a in script if a.op == OpType.EQUAL]
        self.assertGreaterEqual(len(equals), 3)
        
    def test_hirschberg_single_element_original(self):
        hd = HirschbergDiff(['a'], ['a', 'b', 'c'])
        script = hd.compute()
        self.assertIsInstance(script, list)
        
    def test_hirschberg_single_element_modified(self):
        hd = HirschbergDiff(['a', 'b', 'c'], ['b'])
        script = hd.compute()
        self.assertIsInstance(script, list)


class TestDiffLinear(unittest.TestCase):
    def test_diff_linear_basic(self):
        script = diff_linear(['a', 'b', 'c'], ['a', 'x', 'c'])
        self.assertIsInstance(script, list)
        
    def test_diff_linear_produces_valid_patch(self):
        original = ['line1', 'line2', 'line3']
        modified = ['line1', 'modified', 'line3']
        script = diff_linear(original, modified)
        equals = [a.value for a in script if a.op == OpType.EQUAL]
        self.assertIn('line1', equals)
        self.assertIn('line3', equals)


class TestLinearSpaceMyers(unittest.TestCase):
    def test_linear_myers_empty(self):
        lsm = LinearSpaceMyers([], [])
        script = lsm.compute()
        self.assertEqual(script, [])
        
    def test_linear_myers_basic(self):
        lsm = LinearSpaceMyers(['a', 'b', 'c'], ['a', 'x', 'c'])
        script = lsm.compute()
        self.assertIsInstance(script, list)
        
    def test_linear_myers_identical(self):
        lsm = LinearSpaceMyers(['a', 'b'], ['a', 'b'])
        script = lsm.compute()
        equals = [a for a in script if a.op == OpType.EQUAL]
        self.assertEqual(len(equals), 2)


class TestDiffLinearMyers(unittest.TestCase):
    def test_diff_linear_myers_basic(self):
        script = diff_linear_myers(['a'], ['b'])
        self.assertIsInstance(script, list)
        
    def test_diff_linear_myers_identical(self):
        script = diff_linear_myers(['a', 'b'], ['a', 'b'])
        equals = sum(1 for a in script if a.op == OpType.EQUAL)
        self.assertEqual(equals, 2)


class TestDiffEngine(unittest.TestCase):
    def test_engine_standard_mode(self):
        engine = DiffEngine(use_linear_space=False)
        script = engine.diff(['a', 'b'], ['a', 'x'])
        self.assertIsInstance(script, list)
        
    def test_engine_linear_space_mode(self):
        engine = DiffEngine(use_linear_space=True)
        script = engine.diff(['a', 'b'], ['a', 'x'])
        self.assertIsInstance(script, list)
        
    def test_engine_diff_strings_by_line(self):
        engine = DiffEngine()
        script = engine.diff_strings("line1\nline2", "line1\nmodified")
        self.assertIsInstance(script, list)
        
    def test_engine_diff_strings_by_char(self):
        engine = DiffEngine()
        script = engine.diff_strings("abc", "axc", by_line=False)
        self.assertIsInstance(script, list)
        
    def test_engine_compute_lcs(self):
        engine = DiffEngine()
        lcs = engine.compute_lcs(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'y'])
        self.assertIn('a', lcs)
        self.assertIn('c', lcs)
        
    def test_engine_compute_edit_distance(self):
        engine = DiffEngine()
        dist = engine.compute_edit_distance(['a', 'b'], ['a', 'x'])
        self.assertGreater(dist, 0)


class TestBatchDiffer(unittest.TestCase):
    def test_batch_differ_creation(self):
        bd = BatchDiffer()
        self.assertIsNotNone(bd.engine)
        
    def test_batch_differ_with_engine(self):
        engine = DiffEngine(use_linear_space=True)
        bd = BatchDiffer(engine)
        self.assertEqual(bd.engine, engine)
        
    def test_diff_multiple(self):
        bd = BatchDiffer()
        pairs = [
            (['a', 'b'], ['a', 'x']),
            (['x', 'y'], ['x', 'y']),
        ]
        results = bd.diff_multiple(pairs)
        self.assertEqual(len(results), 2)
        
    def test_diff_all_against_base(self):
        bd = BatchDiffer()
        base = ['a', 'b', 'c']
        targets = [
            ['a', 'b', 'c'],
            ['a', 'x', 'c'],
            ['x', 'y', 'z'],
        ]
        results = bd.diff_all_against_base(base, targets)
        self.assertEqual(len(results), 3)


class TestDiffConsistency(unittest.TestCase):
    def test_myers_hirschberg_consistency(self):
        original = ['a', 'b', 'c', 'd', 'e']
        modified = ['a', 'x', 'c', 'y', 'e']
        myers_script = diff(original, modified)
        hirschberg_script = diff_linear(original, modified)
        myers_equals = sum(1 for a in myers_script if a.op == OpType.EQUAL)
        hirsch_equals = sum(1 for a in hirschberg_script if a.op == OpType.EQUAL)
        self.assertEqual(myers_equals, hirsch_equals)
        
    def test_patch_roundtrip_myers(self):
        original = ['line1', 'line2', 'line3', 'line4']
        modified = ['line1', 'changed', 'line3', 'new', 'line4']
        script = diff(original, modified)
        result = patch(original, script)
        self.assertEqual(result, modified)
        
    def test_patch_roundtrip_hirschberg(self):
        original = ['a', 'b', 'c']
        modified = ['a', 'x', 'y', 'c']
        script = diff_linear(original, modified)
        equals_and_inserts = []
        orig_idx = 0
        for action in script:
            if action.op == OpType.EQUAL:
                equals_and_inserts.append(action.value)
                orig_idx += 1
            elif action.op == OpType.INSERT:
                equals_and_inserts.append(action.value)
            elif action.op == OpType.DELETE:
                orig_idx += 1
        self.assertEqual(equals_and_inserts, modified)


class TestEdgeCases(unittest.TestCase):
    def test_single_element_sequences(self):
        script = diff(['a'], ['a'])
        self.assertEqual(len(script), 1)
        self.assertEqual(script[0].op, OpType.EQUAL)
        
    def test_single_different_elements(self):
        script = diff(['a'], ['b'])
        deletes = sum(1 for a in script if a.op == OpType.DELETE)
        inserts = sum(1 for a in script if a.op == OpType.INSERT)
        self.assertEqual(deletes, 1)
        self.assertEqual(inserts, 1)
        
    def test_very_different_sequences(self):
        original = list('abcdefghij')
        modified = list('0123456789')
        script = diff(original, modified)
        self.assertIsInstance(script, list)
        
    def test_repeated_elements(self):
        original = ['a', 'a', 'a', 'a']
        modified = ['a', 'a', 'b', 'a']
        script = diff(original, modified)
        self.assertIsInstance(script, list)
        
    def test_unicode_content(self):
        original = ['привіт', 'світ']
        modified = ['привіт', 'мир']
        script = diff(original, modified)
        self.assertIsInstance(script, list)
        equals = [a for a in script if a.op == OpType.EQUAL]
        self.assertTrue(any(a.value == 'привіт' for a in equals))


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
