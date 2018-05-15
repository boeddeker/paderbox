import unittest
import numpy as np
import nt.testing as tc
from nt.utils.morph import morph


T, B, F = 40, 6, 51
A = np.random.uniform(size=(T, B, F))
A2 = np.random.uniform(size=(T, 1, B, F))
A3 = np.random.uniform(size=(T*B*F,))
A4 = np.random.uniform(size=(T, 1, 1, B, 1, F))


class TestReshape(unittest.TestCase):
    def test_noop_comma(self):
        result = morph('T,B,F->T,B,F', A)
        tc.assert_equal(result.shape, (T, B, F))
        tc.assert_equal(result, A)

    def test_noop_space(self):
        result = morph('T B F->T B F', A)
        tc.assert_equal(result.shape, (T, B, F))
        tc.assert_equal(result, A)

    def test_noop_mixed(self):
        result = morph('tbf->t, b f', A)
        tc.assert_equal(result.shape, (T, B, F))
        tc.assert_equal(result, A)

    def test_transpose_comma(self):
        result = morph('T,B,F->F,T,B', A)
        tc.assert_equal(result.shape, (F, T, B))
        tc.assert_equal(result, A.transpose(2, 0, 1))

    def test_transpose_mixed(self):
        result = morph('t, b, f -> f t b', A)
        tc.assert_equal(result.shape, (F, T, B))
        tc.assert_equal(result, A.transpose(2, 0, 1))

    def test_broadcast_axis_0(self):
        result = morph('T,B,F->1,T,B,F', A)
        tc.assert_equal(result.shape, (1, T, B, F))
        tc.assert_equal(result, A[None, ...])

    def test_broadcast_axis_2(self):
        result = morph('T,B,F->T,B,1,F', A)
        tc.assert_equal(result.shape, (T, B, 1, F))
        tc.assert_equal(result, A[..., None, :])

    def test_broadcast_axis_3(self):
        result = morph('T,B,F->T,B,F,1', A)
        tc.assert_equal(result.shape, (T, B, F, 1))
        tc.assert_equal(result, A[..., None])

    def test_reshape_comma(self):
        result = morph('T,B,F->T,B*F', A)
        tc.assert_equal(result.shape, (T, B*F))
        tc.assert_equal(result, A.reshape(T, B*F))

    def test_reshape_comma_unflatten(self):
        result = morph('t*b*f->tbf', A3, t=T, b=B)
        tc.assert_equal(result.shape, (T, B, F))
        tc.assert_equal(result, A3.reshape((T, B, F)))

    def test_reshape_comma_unflatten_and_transpose_and_flatten(self):
        result = morph('t*b*f->f, t*b', A3, f=F, t=T)
        tc.assert_equal(result.shape, (F, T*B))
        tc.assert_equal(result, A3.reshape((T*B, F)).transpose((1, 0)))

    def test_reshape_comma_flat(self):
        result = morph('T,B,F->T*B*F', A)
        tc.assert_equal(result.shape, (T*B*F,))
        tc.assert_equal(result, A.ravel())

    def test_reshape_comma_with_singleton_input(self):
        result = morph('T, 1, B, F -> T*B*F', A2)
        tc.assert_equal(result.shape, (T*B*F,))
        tc.assert_equal(result, A2.ravel())

    def test_reshape_and_broadcast(self):
        tc.assert_equal(morph('T,B,F->T,1,B*F', A).shape, (T, 1, B*F))
        tc.assert_equal(morph('T,B,F->T,1,B*F', A).ravel(), A.ravel())

    def test_reshape_and_broadcast_many(self):
        result = morph('T,B,F->1,T,1,B*F,1', A)
        tc.assert_equal(result.shape, (1, T, 1, B*F, 1))

    def test_swap_and_reshape(self):
        result = morph('T,B,F->T,F*B', A)
        tc.assert_equal(result.shape, (T, F * B))
        tc.assert_equal(result, A.swapaxes(-1, -2).reshape(T, F * B))

    def test_transpose_and_reshape(self):
        result = morph('T,B,F->F,B*T', A)
        tc.assert_equal(result.shape, (F, B*T))
        tc.assert_equal(result, A.transpose(2, 1, 0).reshape(F, B*T))

    def test_all_comma(self):
        tc.assert_equal(morph('T,B,F->F,1,B*T', A).shape, (F, 1, B*T))

    def test_all_space(self):
        tc.assert_equal(morph('t b f -> f1b*t', A).shape, (F, 1, B*T))