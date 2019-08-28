from __future__ import print_function

import numpy as np

import numba.unittest_support as unittest
from numba.tests.support import TestCase
from numba import njit, types, errors
from numba.special import literally


class TestLiteralDispatcher(TestCase):
    def test_literal_basic(self):
        @njit
        def foo(x):
            return literally(x)

        self.assertEqual(foo(123), 123)
        self.assertEqual(foo(321), 321)

        sig1, sig2 = foo.signatures
        self.assertEqual(sig1[0].literal_value, 123)
        self.assertEqual(sig2[0].literal_value, 321)

    def test_literal_nested(self):
        @njit
        def foo(x):
            return literally(x) * 2

        @njit
        def bar(y, x):
            return foo(y) + x

        y, x = 3, 7
        self.assertEqual(bar(y, x), y * 2 + x)
        [foo_sig] = foo.signatures
        self.assertEqual(foo_sig[0], types.literal(y))
        [bar_sig] = bar.signatures
        self.assertEqual(bar_sig[0], types.literal(y))
        self.assertNotIsInstance(bar_sig[1], types.Literal)

    def test_literal_nested_multi_arg(self):
        @njit
        def foo(a, b, c):
            return inner(a, c)

        @njit
        def inner(x, y):
            return x + literally(y)

        kwargs = dict(a=1, b=2, c=3)
        got = foo(**kwargs)
        expect = (lambda a, b, c: a + c)(**kwargs)
        self.assertEqual(got, expect)
        [foo_sig] = foo.signatures
        self.assertEqual(foo_sig[2], types.literal(3))

    def test_unsupported_literal_type(self):
        @njit
        def foo(a, b, c):
            return inner(a, c)

        @njit
        def inner(x, y):
            return x + literally(y)

        arr = np.arange(10)
        with self.assertRaises(errors.LiteralTypingError) as raises:
            foo(a=1, b=2, c=arr)
        self.assertIn("numpy.ndarray", str(raises.exception))

    def test_biliteral(self):
        # Test usecase with more than one literal call
        @njit
        def foo(a, b, c):
            return inner(a, b) + inner(b, c)

        @njit
        def inner(x, y):
            return x + literally(y)

        kwargs = dict(a=1, b=2, c=3)
        got = foo(**kwargs)
        expect = (lambda a, b, c: a + b + b + c)(**kwargs)
        self.assertEqual(got, expect)
        [(type_a, type_b, type_c)] = foo.signatures
        self.assertNotIsInstance(type_a, types.Literal)
        self.assertIsInstance(type_b, types.Literal)
        self.assertEqual(type_b.literal_value, 2)
        self.assertIsInstance(type_c, types.Literal)
        self.assertEqual(type_c.literal_value, 3)

    def test_aliased_variable(self):
        @njit
        def foo(a, b, c):
            def closure(d):
                return literally(d) + 10 * inner(a, b)
            # The inlining of the closure will create an alias to c
            return closure(c)

        @njit
        def inner(x, y):
            return x + literally(y)

        kwargs = dict(a=1, b=2, c=3)
        got = foo(**kwargs)
        expect = (lambda a, b, c: c + 10 * (a + b))(**kwargs)
        self.assertEqual(got, expect)
        [(type_a, type_b, type_c)] = foo.signatures
        self.assertNotIsInstance(type_a, types.Literal)
        self.assertIsInstance(type_b, types.Literal)
        self.assertEqual(type_b.literal_value, 2)
        self.assertIsInstance(type_c, types.Literal)
        self.assertEqual(type_c.literal_value, 3)

    def test_marking_literal_outside(self):
        @njit
        def foo(x):
            return x

        x = 0xbeef
        litx = literally(x)
        self.assertIsInstance(litx, types.IntegerLiteral)
        self.assertEqual(litx.literal_value, x)
        r = foo(litx)
        self.assertEqual(r, x)
        self.assertEqual(foo.nopython_signatures[0].return_type, litx)


if __name__ == '__main__':
    unittest.main()
