import json
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import _SafeEncoder


def test_safe_encoder_numpy_int():
    encoder = _SafeEncoder()
    result = encoder.default(np.int32(42))
    assert result == 42
    assert isinstance(result, int)


def test_safe_encoder_numpy_float():
    encoder = _SafeEncoder()
    result = encoder.default(np.float64(3.14))
    assert result == pytest.approx(3.14)
    assert isinstance(result, float)


def test_safe_encoder_numpy_array():
    encoder = _SafeEncoder()
    arr = np.array([1, 2, 3])
    result = encoder.default(arr)
    assert result == [1, 2, 3]


def test_safe_encoder_json_serialize():
    data = {
        'name': 'test',
        'values': [np.float32(1.5), np.int32(10)],
        'matrix': np.eye(2),
    }
    dumped = json.dumps(data, cls=_SafeEncoder)
    parsed = json.loads(dumped)
    assert parsed['name'] == 'test'
    assert parsed['values'] == [1.5, 10]
    assert parsed['matrix'] == [[1.0, 0.0], [0.0, 1.0]]
