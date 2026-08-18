import pytest

from casperfpga.bitfield import Field
from casperfpga.memory import Memory, bin2fp, cast_fixed, fp2fixed, fp2fixed_int


class RawMemory(Memory):
    def __init__(self, rawdata, timestamp=123.0):
        super(RawMemory, self).__init__('mem', 16, 0x100, len(rawdata))
        self.rawdata = rawdata
        self.timestamp = timestamp

    def read_raw(self, **kwargs):
        return self.rawdata, self.timestamp


def test_bin2fp_signed_and_fractional():
    assert bin2fp(0b1111, 4, 0, True) == -1
    assert bin2fp(0b0110, 4, 1, False) == 3.0
    assert bin2fp(0b0011, 4, 2, False) == 0.75


def test_fp2fixed_validates_and_clamps():
    with pytest.raises(ValueError):
        fp2fixed(1, 4, 5, False)
    with pytest.raises(ValueError):
        fp2fixed(1, 4, -1, False)
    with pytest.raises(ValueError):
        fp2fixed(-1, 4, 0, False)
    assert fp2fixed(100, 4, 0, False) == 15.0
    assert fp2fixed(-100, 4, 0, True) == -8.0


def test_cast_fixed_and_fp2fixed_int():
    assert cast_fixed(-1.5, 4, 1) == 13
    assert fp2fixed_int(-1.5, 4, 1, True) == 13
    assert fp2fixed_int(1.5, 4, 1, False) == 3


def test_memory_length_and_process_data():
    memory = RawMemory(b'\x12\x34\x56\x78')
    memory.field_add(Field('low', 0, 8, 0, 0))
    memory.field_add(Field('high', 0, 8, 0, 8))
    result = memory.read()
    assert memory.length_in_words() == 2
    assert result['timestamp'] == 123.0
    assert result['data'] == {'low': [0x34, 0x78], 'high': [0x12, 0x56]}


def test_memory_process_data_rejects_non_bytes():
    memory = RawMemory(b'\x00\x01')
    with pytest.raises(TypeError):
        memory._process_data('bad-data')
