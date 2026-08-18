import pytest

from casperfpga.attribute_container import AttributeContainer
from casperfpga.sbram import Sbram
from casperfpga.sysmon import Sysmon
from casperfpga.wishbonedevice import WishBoneDevice
from casperfpga.xgpio import XGpio, XGpio_Config

from tests._helpers import FakeParent, pack_u32


class SingleWriteValue(object):
    def __init__(self):
        self.values = []

    def write_single(self, value):
        self.values.append(value)


class FakeInterface(object):
    def __init__(self):
        self.host = 'fake-host'
        self.write_calls = []
        self.read_int_calls = []
        self.read_calls = []

    def write_int(self, name, data, blindwrite=False, word_offset=0):
        self.write_calls.append((name, data, blindwrite, word_offset))

    def read_int(self, name, word_offset=0):
        self.read_int_calls.append((name, word_offset))
        return 123

    def read(self, name, size, offset=0):
        self.read_calls.append((name, size, offset))
        return b'abcd'


def test_attribute_container_supports_iteration_reassignment_rules():
    container = AttributeContainer()
    item = object()
    container.item = item
    assert container['item'] is item
    assert list(container) == [item]
    assert container.names() == ['item']
    assert len(container) == 1
    with pytest.raises(AttributeError):
        container.item = object()
    container.remove_attribute('item')
    assert len(container) == 0


def test_attribute_container_uses_write_single_shortcut():
    container = AttributeContainer()
    writer = SingleWriteValue()
    container.writer = writer
    container.writer = 5
    assert writer.values == [5]


def test_sbram_from_device_info_and_read(fake_parent):
    fake_parent.queue_read('bram', b'\x00\x01\x00\x02')
    sbram = Sbram.from_device_info(
        fake_parent,
        'bram',
        {'data_width': '16'},
        {'bram': {'address': 0x20, 'bytes': 4}},
    )
    assert repr(sbram) == 'Sbram:bram'
    assert sbram.read()['data'] == (1, 2)


def test_wishbone_device_read_and_write_paths():
    interface = FakeInterface()
    device = WishBoneDevice(interface, 'wb')
    device._write(55, addr=2)
    assert interface.write_calls == [('wb', 55, True, 2)]
    assert device._read(addr=1, size=4) == 123
    assert device._read(addr=8, size=8) == b'abcd'
    with pytest.raises(ValueError):
        device._read(size=3)


def test_xgpio_reads_and_writes_through_parent():
    parent = FakeInterface()
    gpio = XGpio(parent, 'gpio')
    config = XGpio_Config(InterruptPresent=1, IsDual=1)
    assert gpio.XGpio_CfgInitialize(config) == 0
    gpio.XGpio_SetDataDirection(2, 0xF0)
    gpio.XGpio_DiscreteWrite(1, 0xAA)
    assert parent.write_calls == [
        ('gpio', 0xF0, True, 3),
        ('gpio', 0xAA, True, 0),
    ]
    assert gpio.XGpio_GetDataDirection(1) == 123
    assert gpio.XGpio_DiscreteRead(2) == 123


def test_sysmon_sensor_conversions():
    class SysmonParent(object):
        def __init__(self):
            self.values = {
                0: 64 * 300,
                1: 64 * 512,
                2: 64 * 256,
                6: 64 * 128,
            }

        def read_int(self, reg, word_offset=0):
            assert reg == 'sysmon'
            return self.values[word_offset]

    sysmon = Sysmon(SysmonParent())
    sensors = sysmon.get_all_sensors()
    assert round(sensors['temp'], 3) == round((300 * 501.3743 / 1024.0) - 273.6777, 3)
    assert sensors['vccint'] == 1.5
    assert sensors['vccaux'] == 0.75
    assert sensors['vccbram'] == 0.375
