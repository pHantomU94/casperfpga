import struct

import pytest

from casperfpga import casperfpga as cf_module
from casperfpga.attribute_container import AttributeContainer
from casperfpga.casperfpga import CasperFpga, UnknownTransportError


class FakeLogger(object):
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        self.messages.append(('debug', msg))

    def info(self, msg):
        self.messages.append(('info', msg))

    def warning(self, msg):
        self.messages.append(('warning', msg))

    warn = warning

    def error(self, msg):
        self.messages.append(('error', msg))

    def setLevel(self, level):
        self.level = level


class FakeTransport(object):
    def __init__(self):
        self.read_calls = []
        self.blindwrite_calls = []
        self.listdev_result = ['dev0']
        self.memory_devices = {}
        self.platform = None
        self.post_called = False
        self.upload_result = True
        self.upload_calls = []

    def read(self, device_name, size, offset=0, **kwargs):
        self.read_calls.append((device_name, size, offset, kwargs))
        return b'\x01\x02\x03\x04'

    def blindwrite(self, device_name, data, offset=0, **kwargs):
        self.blindwrite_calls.append((device_name, data, offset, kwargs))
        return 'ok'

    def listdev(self):
        return self.listdev_result

    def upload_to_ram_and_program(self, **kwargs):
        self.upload_calls.append(kwargs)
        return self.upload_result

    def post_get_system_information(self):
        self.post_called = True

    def get_system_information_from_transport(self):
        return None, None


class FakeMemoryDevice(object):
    def __init__(self, name):
        self.name = name
        self.post_update = None

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        return cls(device_name)

    def post_create_update(self, device_dict):
        self.post_update = device_dict


class FakeAdcDevice(object):
    def __init__(self, name):
        self.name = name

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, initialise=False):
        return cls(device_name)


def make_fpga():
    fpga = CasperFpga.__new__(CasperFpga)
    fpga.logger = FakeLogger()
    fpga.host = 'fake-host'
    fpga.bitstream = 'design.fpg'
    fpga.transport = FakeTransport()
    fpga.is_little_endian = False
    fpga._detect_little_endianness = lambda: False
    fpga._reset_device_info()
    return fpga


def test_choose_transport_order_and_errors(monkeypatch):
    fpga = make_fpga()
    monkeypatch.setattr(cf_module.SkarabTransport, 'test_host_type', staticmethod(lambda host: False))
    monkeypatch.setattr(cf_module.AlveoTransport, 'test_host_type', staticmethod(lambda host, port: False))
    monkeypatch.setattr(cf_module.KatcpTransport, 'test_host_type', staticmethod(lambda host: True))
    monkeypatch.setattr(cf_module.TapcpTransport, 'test_host_type', staticmethod(lambda host: False))
    assert fpga.choose_transport('roach001', 7147) is cf_module.KatcpTransport
    assert fpga.choose_transport('CasperDummy123', 7147) is cf_module.DummyTransport

    monkeypatch.setattr(cf_module.KatcpTransport, 'test_host_type', staticmethod(lambda host: False))
    with pytest.raises(UnknownTransportError):
        fpga.choose_transport('mystery-board', 7147)


def test_read_and_blindwrite_swap_endianness():
    fpga = make_fpga()
    fpga.is_little_endian = True
    assert fpga.read('reg', 4) == b'\x04\x03\x02\x01'
    fpga.blindwrite('reg', b'\x11\x22\x33\x44')
    assert fpga.transport.blindwrite_calls[-1][1] == b'\x44\x33\x22\x11'


def test_write_verifies_readback_and_raises_on_mismatch():
    fpga = make_fpga()
    fpga.blindwrite = lambda *args, **kwargs: None
    fpga.read = lambda *args, **kwargs: b'\x00\x00\x00\x02'
    with pytest.raises(ValueError):
        fpga.write('reg', b'\x00\x00\x00\x01')


def test_create_memory_devices_and_fallback_registers(monkeypatch):
    fpga = make_fpga()
    monkeypatch.setitem(cf_module.CASPER_MEMORY_DEVICES, 'fake:mem', {'class': FakeMemoryDevice, 'container': 'sbrams'})
    device_dict = {'known': {'tag': 'fake:mem'}}
    memory_map = {'known': {'address': 0x10, 'bytes': 4}, 'loose': {'address': 0x20, 'bytes': 8}}
    fpga._create_memory_devices(device_dict, memory_map)
    assert 'known' in fpga.memory_devices
    assert 'loose' in fpga.memory_devices
    assert getattr(fpga.sbrams, 'known').name == 'known'
    assert fpga.memory_devices['known'].post_update == device_dict


def test_create_other_and_adc_devices(monkeypatch):
    fpga = make_fpga()
    monkeypatch.setitem(cf_module.CASPER_ADC_DEVICES, 'fake:adc', {'class': FakeAdcDevice, 'container': 'adcs'})
    device_dict = {'other': {'tag': 'casper:fft'}, 'adc0': {'tag': 'fake:adc'}}
    fpga._create_other_devices(device_dict)
    fpga._create_casper_adc_devices(device_dict, initialise=True)
    assert fpga.other_devices['other']['tag'] == 'casper:fft'
    assert fpga.adc_devices['adc0'].name == 'adc0'


def test_get_system_information_from_tuple(monkeypatch):
    fpga = make_fpga()
    monkeypatch.setattr(fpga, '_add_sys_registers', lambda: {})
    monkeypatch.setattr(fpga, '_detect_little_endianness', lambda: False)
    monkeypatch.setattr(fpga, '_create_memory_devices', lambda device_dict, memorymap_dict, **kwargs: fpga.memory_devices.update({'ok': object()}))
    monkeypatch.setattr(fpga, '_create_other_devices', lambda device_dict, **kwargs: fpga.other_devices.update({'other': {}}))
    monkeypatch.setattr(fpga, '_create_casper_adc_devices', lambda device_dict, **kwargs: fpga.adc_devices.update({'adc': object()}))
    monkeypatch.setattr(fpga, '_create_casper_device_by_regname', lambda device_dict: setattr(fpga, 'sensors', 'done'))
    fpg_info = (
        {'77777': {'system': 'testsys'}, '77777_git': {'tag': 'rcs', 'rev': 'abc'}, 'dev': {'tag': 'ignored'}},
        {'dev': {'address': 1, 'bytes': 4}},
    )
    fpga.transport.get_system_information_from_transport = lambda: (None, fpg_info)
    fpga.get_system_information(filename=None, fpg_info=fpg_info)
    assert fpga.system_info['system'] == 'testsys'
    assert fpga.rcs_info['git']['rev'] == 'abc'
    assert fpga.transport.memory_devices == fpga.memory_devices
    assert fpga.transport.post_called is True


def test_upload_to_ram_and_program_refreshes_system_info(monkeypatch):
    fpga = make_fpga()
    called = {}
    monkeypatch.setattr(fpga, 'get_system_information', lambda filename, **kwargs: called.setdefault('filename', filename))
    monkeypatch.setattr(fpga, '_detect_little_endianness', lambda: True)
    assert fpga.upload_to_ram_and_program(filename='newdesign.fpg', wait_complete=True) is True
    assert called['filename'] == 'newdesign.fpg'
    assert fpga.transport.upload_calls[-1]['filename'] == 'newdesign.fpg'
