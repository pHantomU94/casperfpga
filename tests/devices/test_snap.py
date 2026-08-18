import pytest

from casperfpga.register import Register
from casperfpga.snap import Snap

from tests._helpers import FakeParent, FakeRegister, pack_u32


def test_snap_from_device_info_uses_bram_mapping():
    snap = Snap.from_device_info(
        FakeParent(),
        'snap',
        {'data_width': '16', 'nsamples': '2'},
        {'snap_bram': {'address': 0x200, 'bytes': 8}},
    )
    assert snap.address == 0x200
    assert snap.length_bytes == 8
    assert snap.width_bits == 16


def test_snap_update_from_bitsnap_populates_fields():
    snap = Snap(FakeParent(), 'snap_ss', 8, 0x0, 4, {'snap_value': 'off'})
    snap.update_from_bitsnap({
        'snap_data_width': '8',
        'snap_nsamples': '2',
        'io_names': '[a,b]',
        'io_widths': '[4,4]',
        'io_types': '[0,0]',
        'io_bps': '[0,0]',
    })
    assert list(snap.field_names()) == ['b', 'a']


def test_snap_link_control_registers_requires_critical_registers():
    snap = Snap(FakeParent(), 'snap', 32, 0x0, 4, {'snap_value': 'off'})
    with pytest.raises(RuntimeError):
        snap._link_control_registers({})


def test_snap_link_control_registers_processes_extra_value_register():
    parent = FakeParent()
    control = Register(parent, 'snap_ctrl', 0, {'names': '[reg]', 'bitwidths': '[32]', 'arith_types': '[0]', 'bin_pts': '[0]'})
    status = Register(parent, 'snap_status', 4, {'names': '[reg]', 'bitwidths': '[32]', 'arith_types': '[0]', 'bin_pts': '[0]'})
    extra = Register(parent, 'snap_val', 8, {'names': '[reg]', 'bitwidths': '[32]', 'arith_types': '[0]', 'bin_pts': '[0]'})
    parent.memory_devices = {
        'snap_ctrl': control,
        'snap_status': status,
        'snap_val': extra,
    }
    snap = Snap(parent, 'snap', 32, 0x0, 4, {'snap_value': 'on', 'value': 'on'})
    snap._link_control_registers({'snap_val': {}})
    assert extra.field_get_by_name('reg') is not None


def test_snap_arm_writes_offset_and_control_sequence():
    snap = Snap(FakeParent(), 'snap', 32, 0x0, 4, {'snap_value': 'off'})
    ctrl = FakeRegister()
    offset = FakeRegister()
    snap.control_registers['control']['register'] = ctrl
    snap.control_registers['trig_offset']['register'] = offset
    snap.arm(man_trig=True, man_valid=True, offset=7, circular_capture=True)
    assert offset.write_int_calls == [7]
    assert ctrl.write_int_calls == [14, 15]


def test_snap_read_raw_reads_bram_and_extra_value():
    parent = FakeParent()
    parent.queue_read('snap_bram', pack_u32(0x01020304))
    snap = Snap(parent, 'snap', 32, 0x0, 4, {'snap_value': 'on'})
    snap.control_registers['control']['register'] = FakeRegister()
    snap.control_registers['status']['register'] = FakeRegister([4, 4])
    snap.control_registers['extra_value']['register'] = FakeRegister(read_value={'data': {'reg': 99}, 'timestamp': 0})
    result, timestamp = snap.read_raw()
    assert result['data'] == pack_u32(0x01020304)
    assert result['extra_value'] == {'data': {'reg': 99}, 'timestamp': 0}
    assert result['length'] == 4
    assert timestamp > 0


def test_snap_read_raw_validates_kwargs():
    snap = Snap(FakeParent(), 'snap', 32, 0x0, 4, {'snap_value': 'off'})
    snap.control_registers['control']['register'] = FakeRegister()
    snap.control_registers['status']['register'] = FakeRegister([4, 4])
    with pytest.raises(RuntimeError):
        snap.read_raw(unknown=True)


def test_packetise_snapdata_uses_eof_and_dv():
    packets = Snap.packetise_snapdata(
        {'eof': [0, 1, 0, 1], 'dv': [1, 1, 0, 1], 'data': [10, 11, 12, 13]},
        dv_key='dv',
    )
    assert packets == [
        {'eof': [0, 1], 'dv': [1, 1], 'data': [10, 11]},
        {'eof': [1], 'dv': [1], 'data': [13]},
    ]


def test_packetise_snapdata_enforces_packet_length():
    with pytest.raises(Exception) as exc:
        Snap.packetise_snapdata({'eof': [0, 1], 'data': [1, 2]}, packet_length=3)
    assert 'Expected 3, got 2' in str(exc.value)
