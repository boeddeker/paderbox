import os
import tempfile
import pytest
import paderbox.testing as tc
import numpy as np
from paderbox.io import dump_pickle, load_pickle

class TestPickle:
    @pytest.mark.parametrize("name,data,expect", [
        ('int', {'key': 1}, 1),
        ('float', {'key': 1.1}, 1.1),
        ('complex', {'key': 1.1j}, 1.1j),
        ('str', {'key': 'bla'}, 'bla'),
        ('none', {'key': None}, None),
        ('np int', {'key': int(1)}, 1),
        ('np float32', {'key': np.float32(1.1)}, np.float32(1.1)),
        ('np float64', {'key': np.float64(1.1)}, np.float64(1.1)),
        ('np complex64', {'key': np.complex64(1.1j)}, np.complex64(1.1j)),
        ('np complex128', {'key': np.complex128(1.1j)}, np.complex128(1.1j)),
        ('np float64', {'key': np.float64(1.1)}, np.float64(1.1)),
        ('list', {'key': [1, 2, 3]}, [1, 2, 3]),  # Note type is list
        ('tuple', {'key': (1, 2, 3)}, (1, 2, 3)),
        ('set', {'key': {1, 2, 3}}, {1, 2, 3}),
        ('array', {'key': np.array([1, 2, 3])}, np.array([1, 2, 3])),
        ('np nan', {'key': np.nan}, np.nan),
        ('np inf', {'key': np.inf}, np.inf),
        ('np array nan inf', {'key': np.asarray([0, 1, np.nan, np.inf])},
         np.asarray([0, 1, np.nan, np.inf])),
        ('heterogenous list', {'key': [1.2, [3, 4]]},
         [1.2, [3, 4]]),  # Note type is list
        ('large list', {'key': list(range(100, 0, -1))},
         list(range(100, 0, -1))),  # Note type is list, test if sort correct
    ])
    def test_dump_load(self,name,data,expect):
        with tempfile.TemporaryDirectory() as temp_dir:
            dump_pickle(data, os.path.join(temp_dir, 'test.pickle'))
            data_load = load_pickle(os.path.join(temp_dir, 'test.pickle'))
        print(expect, data_load['key'], type(expect), type(data_load['key']))
        assert 'key' in data_load.keys(), data_load

        assert type(expect) is type(data_load['key']), \
            (type(expect), type(data_load['key']), expect, data_load['key'])
        tc.assert_equal(expect, data_load['key'])
