import pytest

from casperfpga.bitfield import Bitfield, Field, clean_fields


def test_clean_fields_supports_spaces_commas_and_empty_values():
    assert clean_fields('reg', 'register', '[a, b,  ,c]') == ['a', 'b', 'c']
    assert clean_fields('reg', 'register', 'a b  c') == ['a', 'b', 'c']


def test_bitfield_adds_fields_and_auto_offsets():
    bitfield = Bitfield('ctrl', 8)
    field_a = Field('a', 0, 2, 0, -1)
    field_b = Field('b', 0, 3, 0, -1)
    bitfield.field_add(field_a, auto_offset=True)
    bitfield.field_add(field_b, auto_offset=True)
    assert field_a.offset == 0
    assert field_b.offset == 2
    assert bitfield.field_get_by_name('b') is field_b
    assert list(bitfield.field_names()) == ['a', 'b']
    assert 'ctrl(8,[' in str(bitfield)


def test_bitfield_fields_add_validates_input():
    bitfield = Bitfield('ctrl', 8)
    with pytest.raises(TypeError):
        bitfield.fields_add([])
    with pytest.raises(ValueError):
        bitfield.fields_add({})


def test_bitfield_fields_clear_resets_mapping():
    bitfield = Bitfield('ctrl', 8, {'a': Field('a', 0, 1, 0, 0)})
    bitfield.fields_clear()
    assert list(bitfield.field_names()) == []


def test_field_validates_numtype_and_name():
    with pytest.raises(TypeError):
        Field('name', '0', 1, 0, 0)
    with pytest.raises(AssertionError):
        Field('   ', 0, 1, 0, 0)
