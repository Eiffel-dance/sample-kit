import math
import unittest

import app
from app import weighted_sample, serialize_metrics


class WeightedSampleTest(unittest.TestCase):
    def test_deterministic_same_seed(self):
        args = (['red', 'green', 'blue'], [1, 3, 2], 2)
        first = weighted_sample(*args, seed=42)
        self.assertEqual(first, weighted_sample(*args, seed=42))
        self.assertEqual(len(first), 2)

    def test_known_baseline_result(self):
        self.assertEqual(weighted_sample(['red', 'green', 'blue'], [1, 3, 2], 2, 42),
                         ['green', 'red'])

    def test_does_not_mutate_inputs(self):
        items = ['a', 'b', 'c']
        weights = [1, 2, 3]
        weighted_sample(items, weights, 2, 7)
        self.assertEqual(items, ['a', 'b', 'c'])
        self.assertEqual(weights, [1, 2, 3])

    def test_duplicate_values_drawn_by_position(self):
        result = weighted_sample(['x', 'x', 'y'], [1, 1, 1], 3, 5)
        self.assertEqual(sorted(result), ['x', 'x', 'y'])

    def test_zero_weight_never_selected(self):
        for seed in range(20):
            self.assertEqual(weighted_sample(['a', 'b', 'c'], [0, 1, 0], 1, seed),
                             ['b'])

    def test_k_zero_returns_empty_list(self):
        self.assertEqual(weighted_sample([], [], 0, 1), [])
        self.assertEqual(weighted_sample(['a'], [0], 0, 1), [])
        self.assertEqual(weighted_sample(['a', 'b'], [1, 2], 0, 1), [])

    def test_exhausted_positive_weight_raises(self):
        with self.assertRaises(ValueError):
            weighted_sample(['a', 'b'], [1, 0], 2, 3)

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            weighted_sample(iter([1, 2]), [1, 1], 1)          # no len()
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], 5, 1)                     # not a sequence
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], [1, 1], True)             # bool k
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], [1, 1], 1.5)              # non-int k
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], [1, 1], 1, seed=[1])      # bad seed
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], [1, 'x'], 1)              # non-numeric weight
        with self.assertRaises(TypeError):
            weighted_sample([1, 2], [1, True], 1)             # bool weight

    def test_value_errors(self):
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1], 1)                   # length mismatch
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, 1], -1)               # negative k
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, 1], 3)                # k too large
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, -0.5], 1)             # negative weight
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, math.nan], 1)         # NaN weight
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, math.inf], 1)         # infinite weight
        with self.assertRaises(ValueError):
            weighted_sample([1, 2], [1, -math.inf], 1)        # -inf weight

    def test_validation_happens_before_sampling(self):
        # k=0 still validates weights and seed.
        with self.assertRaises(ValueError):
            weighted_sample(['a'], [-1], 0)
        with self.assertRaises(TypeError):
            weighted_sample(['a'], [1], 0, seed=object())


class SerializeMetricsTest(unittest.TestCase):
    def test_compact_sorted_unicode(self):
        self.assertEqual(serialize_metrics({'b': 1, 'a': 'é'}),
                         '{"a":"é","b":1}')

    def test_big_integers_exact(self):
        big = 9007199254740993
        out = serialize_metrics({'events': big, 'neg': -big,
                                 'nested': [big]})
        self.assertEqual(
            out,
            '{"events":9007199254740993,"neg":-9007199254740993,'
            '"nested":[9007199254740993]}')

    def test_scalar_semantics(self):
        self.assertEqual(serialize_metrics({'t': True, 'n': None,
                                            'f': 1.5, 's': 'x'}),
                         '{"f":1.5,"n":null,"s":"x","t":true}')

    def test_nan_and_infinity_raise_value_error(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                serialize_metrics({'v': bad})
            with self.assertRaises(ValueError):
                serialize_metrics([bad])
            with self.assertRaises(ValueError):
                serialize_metrics(bad)

    def test_unrepresentable_raises_type_error(self):
        with self.assertRaises(TypeError):
            serialize_metrics({'s': {1, 2, 3}})
        with self.assertRaises(TypeError):
            serialize_metrics(object())
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaises(TypeError):
            serialize_metrics(cyclic)
        cyclic_dict = {}
        cyclic_dict['self'] = cyclic_dict
        with self.assertRaises(TypeError):
            serialize_metrics(cyclic_dict)


if __name__ == '__main__':
    unittest.main()
