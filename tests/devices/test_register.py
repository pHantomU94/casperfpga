import pytest

from casperfpga.register import Register

from tests._helpers import FakeParent, pack_u32


def make_register(parent=None, device_info=None):
    info = device_info or {
        'names': '[flag,value]',
        'bitwidths': '[1,3]',
        'arith_types': '[0,0]',
        'bin_pts': '[0,0]',
    }
    return Register(parent or FakeParent(), 'reg', 0x10, device_info=info)


def test_register_from_device_info_finds_address():
    reg = Register.from_device_info(
        FakeParent(),
        'reg',
        {'names': '[reg]', 'bitwidths': '[32]', 'arith_types': '[0]', 'bin_pts': '[0]'},
        {'reg': {'address': 0x40, 'bytes': 4}},
    )
    assert reg.address == 0x40


def test_register_from_device_info_raises_when_missing():
    with pytest.raises(RuntimeError):
        Register.from_device_info(FakeParent(), 'reg', {}, {})


def test_register_read_flattens_memory_values(fake_parent):
    fake_parent.queue_read('reg', pack_u32(9))
    reg = make_register(fake_parent, {
        'names': '[value]',
        'bitwidths': '[32]',
        'arith_types': '[0]',
        'bin_pts': '[0]',
    })
    result = reg.read()
    assert result['data'] == {'value': 9}


def test_register_write_common_packs_bitfields():
    reg = make_register()
    fixed_int, pulse = reg._write_common(flag=1, value=5)
    assert fixed_int == 13
    assert pulse == {}


def test_register_write_common_uses_existing_values_for_toggle_and_pulse(monkeypatch):
    reg = make_register()
    monkeypatch.setattr(reg, 'read', lambda: {'data': {'value': 1, 'flag': 0}})
    fixed_int, pulse = reg._write_common(flag='pulse', value='toggle')
    assert fixed_int == 8
    assert pulse == {'flag': 0}


def test_register_write_replays_pulse(fake_parent, monkeypatch):
    reg = make_register(fake_parent)
    monkeypatch.setattr(reg, 'read', lambda: {'data': {'value': 1, 'flag': 0}})
    reg.write(flag='pulse', value=3)
    assert fake_parent.write_int_calls == [
        ('reg', 11, False, 0),
        ('reg', 1, False, 0),
    ]


def test_register_blindwrite_uses_blind_flag(fake_parent):
    reg = make_register(fake_parent)
    reg.blindwrite(flag=1, value=2)
    assert fake_parent.write_int_calls == [('reg', 10, True, 0)]


def test_register_write_common_rejects_unknown_field():
    reg = make_register()
    with pytest.raises(ValueError):
        reg._write_common(missing=1)
