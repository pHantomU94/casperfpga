import struct
import katcp
import pytest

from casperfpga import transport_katcp as katcp_module
from casperfpga import transport_tapcp as tapcp_module
from casperfpga.transport_katcp import KatcpTransport
from casperfpga.transport_tapcp import (
    FLASH_SECTOR_SIZE,
    TapcpTransport,
    decode_csl,
    decode_csl_pl,
    get_core_info_payload,
)

from tests._helpers import FakeInform, FakeReply, FakeTftpClient, FakeTftpyModule


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

    def exception(self, msg):
        self.messages.append(('exception', msg))


def make_katcp_transport():
    transport = KatcpTransport.__new__(KatcpTransport)
    transport.host = 'fake-host'
    transport._timeout = 1
    transport.logger = FakeLogger()
    transport.prog_info = {'last_uploaded': '', 'last_programmed': ''}
    transport.system_info = {}
    transport.bitstream = 'design.fpg'
    transport.unhandled_inform_handler = None
    transport._bindaddr = ('0.0.0.0', 7147)
    transport._connected = True
    transport._unsubscribe_all_taps = lambda: None
    transport.katcp_calls = []
    transport.katcp_responses = {}

    def fake_katcprequest(name, **kwargs):
        transport.katcp_calls.append((name, kwargs))
        response = transport.katcp_responses[name]
        if callable(response):
            return response(name, **kwargs)
        return response

    transport.katcprequest = fake_katcprequest
    transport.is_connected = lambda: transport._connected
    return transport


def make_tapcp_transport():
    transport = TapcpTransport.__new__(TapcpTransport)
    transport.host = 'fake-host'
    transport.timeout = 1
    transport.server_timeout = 0
    transport.retries = 3
    transport.logger = FakeLogger()
    transport.platform = 'snap'
    transport.t = FakeTftpClient()
    return transport


def encode_csl(entries):
    payload_size = 9
    result = bytearray([0, 0, payload_size])
    prev = b''
    for idx, (name, payload) in enumerate(entries):
        name_b = name if isinstance(name, bytes) else name.encode()
        shared = 0
        while shared < min(len(prev), len(name_b)) and prev[shared] == name_b[shared]:
            shared += 1
        suffix = name_b[shared:]
        if idx != 0:
            result.append(shared)
        result.append(len(suffix))
        result.extend(suffix)
        result.extend(payload)
        prev = name_b
    result.extend([0, 0])
    return bytes(result)


def test_tapcp_coreinfo_and_csl_decoding():
    payload = struct.pack('>LLB', 0x1234567B, 0x20, 5)
    parsed = get_core_info_payload(payload)
    assert parsed == {'rw': 3, 'addr': 0x1234567A, 'size': 0x20, 'typenum': 5}

    blob = encode_csl([
        ('devA', payload),
        ('devAB', struct.pack('>LLB', 0x10, 0x8, 1)),
    ])
    decoded = decode_csl_pl(blob)
    assert b'devA' in decoded
    assert b'devAB' in decoded
    assert decode_csl(blob) == [b'devA', b'devAB']


def test_tapcp_listdev_read_and_blindwrite():
    transport = make_tapcp_transport()
    transport.t.queue_download_result(encode_csl([(b'devA', struct.pack('>LLB', 0, 4, 1))]))
    assert transport.listdev() == ['devA']
    transport.t.queue_download_result(encode_csl([(b'devA', struct.pack('>LLB', 0, 4, 1))]))
    assert transport.listdev_pl() == ['devA']

    transport.t.queue_download_result(b'data')
    assert transport.read('reg', 16, offset=8) == b'data'
    assert transport.t.downloads[-1][0] == 'reg.2.4'

    transport.blindwrite('reg', b'abcd', offset=8)
    assert transport.t.uploads[-1][0] == 'reg.2.0'


def test_tapcp_update_metadata_and_flash_info(monkeypatch):
    transport = make_tapcp_transport()
    writes = []
    monkeypatch.setattr(transport, 'blindwrite', lambda device, data, offset=0: writes.append((device, data, offset)))
    head_loc, prog_loc = transport._update_metadata('/tmp/design.fpg', 1024, 4096, 'deadbeef')
    assert head_loc == transport.get_user_flash_loc() + FLASH_SECTOR_SIZE
    assert prog_loc == head_loc + 1024
    assert writes[-1][0] == '/flash'
    assert b'?md5sum\tdeadbeef' in writes[-1][1]


def test_tapcp_get_system_information_from_transport(monkeypatch):
    transport = make_tapcp_transport()
    monkeypatch.setattr(transport, 'get_metadata', lambda: {'header_length': '10', 'header_start': '0'})
    monkeypatch.setattr(transport, 'read', lambda device, size, offset=0: b'header-data')
    monkeypatch.setattr(tapcp_module, 'parse_fpg', lambda buf, isbuf=True: ({'dev': {}}, {'mem': {}}))
    filename, info = transport.get_system_information_from_transport()
    assert filename is None
    assert info == ({'dev': {}}, {'mem': {}})


def test_tapcp_progdev_temp_connectivity_and_wishbone(monkeypatch):
    transport = make_tapcp_transport()
    transport.progdev(addr=0x123400)
    assert transport.t.uploads[-1][0] == '/progdev'
    assert transport.t.uploads[-1][1] == struct.pack('>L', 0x123400 >> 8)

    transport.platform = 'snap2'
    transport.progdev(addr=0x123400)
    assert transport.t.uploads[-1][1] == struct.pack('>L', 0x123400)

    transport.t.queue_download_result(struct.pack('>f', 12.5))
    assert transport.get_temp() == pytest.approx(12.5)

    monkeypatch.setattr(transport, 'read', lambda device, size, offset=0, use_bulk=True: b'1234')
    assert transport.is_connected() is True
    monkeypatch.setattr(transport, 'read', lambda device, size, offset=0, use_bulk=True: (_ for _ in ()).throw(RuntimeError('boom')))
    assert transport.is_connected() is False
    transport.is_connected = lambda: True
    assert transport.is_running() is True

    calls = []
    monkeypatch.setattr(transport, 'blindwrite', lambda device, data, offset=0, use_bulk=True: calls.append((device, data, offset)))
    transport.write_wishbone(0x10, 0x12345678)
    assert calls == [('/fpga', struct.pack('>I', 0x12345678), 0x10)]

    monkeypatch.setattr(transport, 'read', lambda device, size, offset=0, use_bulk=True: struct.pack('>I', 0xAABBCCDD))
    assert transport.read_wishbone(0x20) == 0xAABBCCDD


def test_tapcp_extract_bitstream_and_user_flash_locations(tmp_path):
    transport = make_tapcp_transport()
    header = b'header\n?quit\n'
    payload = b'payload-data'

    filename = tmp_path / 'design.fpg'
    import gzip
    with gzip.open(tmp_path / 'payload.gz', 'wb') as fh:
        fh.write(payload)
    gz_bytes = (tmp_path / 'payload.gz').read_bytes()
    filename.write_bytes(header + gz_bytes)

    extracted_header, prog, md5 = transport._extract_bitstream(str(filename))
    assert extracted_header.startswith(header)
    assert len(extracted_header) % 1024 == 0
    assert prog == payload
    assert len(md5) == 32

    assert transport.get_user_flash_loc() == 0x800000
    transport.platform = 'snap2'
    assert transport.get_user_flash_loc() == 0xC00000


def test_tapcp_get_metadata_reads_until_end(monkeypatch):
    transport = make_tapcp_transport()
    pages = []

    def fake_read(device, size, offset=0, use_bulk=True):
        pages.append((device, size, offset))
        if len(pages) == 1:
            return b'?header_start\t0' + b'0' * (1024 - len(b'?header_start\t0'))
        return b'?header_length\t10?end' + b'0' * (1024 - len(b'?header_length\t10?end'))

    monkeypatch.setattr(transport, 'read', fake_read)
    meta = transport.get_metadata()
    assert meta['header_start'].startswith('0')
    assert meta['header_length'] == '10'
    assert pages[0] == ('/flash', 1024, transport.get_user_flash_loc())
    assert pages[1][2] == transport.get_user_flash_loc() + 1024


def test_tapcp_get_metadata_returns_none_after_max_search(monkeypatch):
    transport = make_tapcp_transport()
    monkeypatch.setattr(transport, 'read', lambda device, size, offset=0, use_bulk=True: b'0' * 1024)
    assert transport.get_metadata() is None


def test_tapcp_read_and_write_retry_behaviour(monkeypatch):
    transport = make_tapcp_transport()
    monkeypatch.setattr(tapcp_module, 'TFTPY', FakeTftpyModule(), raising=False)
    sleep_calls = []
    monkeypatch.setattr(tapcp_module.time, 'sleep', lambda value: sleep_calls.append(value))

    transport.t.queue_download_result(RuntimeError('retry'))
    transport.t.queue_download_result(b'okay')
    assert transport.read('reg', 16, offset=8) == b'okay'
    assert sleep_calls == [transport.server_timeout]

    transport.t.queue_download_result(FakeTftpyModule.TftpShared.TftpFileNotFoundError('missing'))
    transport.t.queue_download_result(FakeTftpyModule.TftpShared.TftpFileNotFoundError('missing'))
    with pytest.raises(RuntimeError):
        transport.read('missing', 16, offset=0)

    transport.t.queue_upload_result(RuntimeError('retry'))
    transport.t.queue_upload_result(None)
    transport.blindwrite('reg', b'abcd', offset=0)

    transport.t.queue_upload_result(RuntimeError('one'))
    transport.t.queue_upload_result(RuntimeError('two'))
    transport.t.queue_upload_result(RuntimeError('three'))
    with pytest.raises(RuntimeError):
        transport.blindwrite('reg', b'abcd', offset=0)


def test_tapcp_write_to_flash_and_programming_paths(monkeypatch, tmp_path):
    transport = make_tapcp_transport()

    class DummyProgressBar(object):
        def __call__(self, iterable):
            return iterable

    monkeypatch.setattr(tapcp_module.progressbar, 'ProgressBar', lambda: DummyProgressBar())

    writes = []
    readbacks = {}

    def fake_blindwrite(device, data, offset=0, use_bulk=True):
        writes.append((device, data, offset))
        readbacks[offset] = data

    def fake_read(device, size, offset=0, use_bulk=True):
        return readbacks.get(offset, b'\x00' * size)

    monkeypatch.setattr(transport, 'blindwrite', fake_blindwrite)
    monkeypatch.setattr(transport, 'read', fake_read)

    payload = (b'A' * FLASH_SECTOR_SIZE) + b'BEEF'
    next_loc = transport.write_to_flash(payload, 0x2000)
    assert next_loc == 0x2000 + (2 * FLASH_SECTOR_SIZE)
    assert writes[0][2] == 0x2000
    assert writes[1][2] == 0x2000 + FLASH_SECTOR_SIZE
    assert transport.timeout == 1

    monkeypatch.setattr(transport, 'get_metadata', lambda: {'md5sum': 'same', 'prog_bitstream_start': '4096', 'filename': 'old.fpg'})
    monkeypatch.setattr(transport, '_extract_bitstream', lambda filename: (b'H' * 1024, b'P' * 1024, 'same'))
    progdev_calls = []
    monkeypatch.setattr(transport, 'progdev', lambda addr=0: progdev_calls.append(addr))
    transport.upload_to_ram_and_program('design.fpg')
    assert progdev_calls == [4096]
    assert transport.timeout == 1

    update_calls = []
    monkeypatch.setattr(transport, 'get_metadata', lambda: None)
    monkeypatch.setattr(transport, '_extract_bitstream', lambda filename: (b'H' * 1024, b'P' * 2048, 'newmd5'))
    monkeypatch.setattr(transport, '_update_metadata', lambda filename, hlen, plen, md5: (update_calls.append((filename, hlen, plen, md5)) or (0x900000, 0x910000)))
    writes[:] = []
    readbacks.clear()
    progdev_calls[:] = []
    transport.upload_to_ram_and_program('design.fpg')
    assert update_calls == [('design.fpg', FLASH_SECTOR_SIZE, 2048, 'newmd5')]
    assert writes[0][2] == 0x900000
    assert progdev_calls == [0x910000]

    raw_file = tmp_path / 'image.bin'
    raw_file.write_bytes((b'Z' * FLASH_SECTOR_SIZE) + b'LAST')
    writes[:] = []
    readbacks.clear()
    progdev_calls[:] = []
    transport.upload_to_ram_and_program(str(raw_file))
    assert writes[0][2] == transport.get_user_flash_loc()
    assert writes[1][2] == transport.get_user_flash_loc() + FLASH_SECTOR_SIZE
    assert progdev_calls == [transport.get_user_flash_loc()]


def test_katcp_listdev_ping_read_and_blindwrite():
    transport = make_katcp_transport()
    transport.katcp_responses['listdev'] = (FakeReply(katcp.Message.OK), [FakeInform('inform', b'dev0')])
    assert transport.listdev() == ['dev0']

    transport.katcp_responses['watchdog'] = (FakeReply(katcp.Message.OK), [])
    assert transport.ping() is True

    transport.katcp_responses['read'] = (FakeReply(katcp.Message.OK, b'abcd'), [])
    assert transport.read('reg', 4, 8) == b'abcd'

    transport.katcp_responses['write'] = (FakeReply(katcp.Message.OK), [])
    transport.blindwrite('reg', b'abcd', 4)
    assert transport.katcp_calls[-1][0] == 'write'


def test_katcp_read_design_and_coreinfo(monkeypatch):
    transport = make_katcp_transport()
    transport.katcp_responses['meta'] = (
        FakeReply(katcp.Message.OK),
        [
            FakeInform('meta', b'dev/name', b'tag:kind', b'param', b'value'),
            FakeInform('meta', b'77777_git', b'rcs', b'repo', b'abcdef'),
        ],
    )
    meta = transport._read_design_info_from_host()
    assert meta['dev_name']['param'] == 'value'
    assert any(name.startswith('77777_git_') for name in meta.keys())

    transport.katcp_responses['listdev'] = lambda name, **kwargs: (
        (FakeReply(katcp.Message.OK), [FakeInform('listdev', b'reg0', b'4:0')])
        if kwargs['request_args'] == ('size',)
        else (FakeReply(katcp.Message.OK), [FakeInform('listdev', b'reg0', b'0x10:0')])
    )
    core = transport._read_coreinfo_from_host()
    assert core == {'reg0': {'address': 0x10, 'bytes': 4}}


def test_katcp_get_system_information_from_transport_and_upload(monkeypatch):
    transport = make_katcp_transport()
    transport.is_running = lambda: True
    monkeypatch.setattr(transport, '_read_design_info_from_host', lambda: {'dev': {'tag': 'x'}})
    monkeypatch.setattr(transport, '_read_coreinfo_from_host', lambda: {'dev': {'address': 1, 'bytes': 4}})
    assert transport.get_system_information_from_transport() == (
        'design.fpg',
        ({'dev': {'tag': 'x'}}, {'dev': {'address': 1, 'bytes': 4}})
    )

    monkeypatch.setattr(katcp_module.os.path, 'getsize', lambda filename: 123)
    monkeypatch.setattr(katcp_module.random, 'randint', lambda a, b: 2222)
    monkeypatch.setattr(transport, 'sendfile', lambda filename, host, port, result_queue, timeout=2: result_queue.put(''))
    transport.katcp_responses['progremote'] = (FakeReply(katcp.Message.OK), [])
    ready = FakeInform('fpga', b'ready')
    transport.unhandled_inform_handler = None

    original_thread = katcp_module.threading.Thread

    class ImmediateThread(object):
        def __init__(self, target, args=()):
            self.target = target
            self.args = args

        def start(self):
            self.target(*self.args)

        def join(self):
            return

    monkeypatch.setattr(katcp_module.threading, 'Thread', ImmediateThread)

    original_queue = katcp_module.queue.Queue

    class ReadyQueue(original_queue):
        instances = []

        def __init__(self, *args, **kwargs):
            super(ReadyQueue, self).__init__(*args, **kwargs)
            ReadyQueue.instances.append(self)

        def put(self, item, *args, **kwargs):
            return super(ReadyQueue, self).put(item, *args, **kwargs)

    monkeypatch.setattr(katcp_module.queue, 'Queue', ReadyQueue)

    def fake_sendfile(filename, host, port, result_queue, timeout=2):
        result_queue.put('')
        # unhandled informs queue is created after upload queue
        ReadyQueue.instances[-1].put(ready)

    monkeypatch.setattr(transport, 'sendfile', fake_sendfile)

    assert transport.upload_to_ram_and_program('firmware.fpg', timeout=1) is True
    assert transport.prog_info['last_programmed'] == 'firmware.fpg'
