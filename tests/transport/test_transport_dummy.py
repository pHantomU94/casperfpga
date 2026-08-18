from casperfpga.transport_dummy import DummyTransport, NamedFifo


def test_named_fifo_respects_maxlen_and_named_pop():
    fifo = NamedFifo(maxlen=2)
    fifo.push('a', 1)
    fifo.push('b', 2)
    fifo.push('c', 3)
    assert len(fifo) == 2
    assert fifo.pop('b') == 2
    assert fifo.pop() == 3


def test_dummy_transport_read_write_and_wishbone():
    transport = DummyTransport(host='127.0.0.1')
    transport.blindwrite('dev', 'abcd')
    assert transport.read('dev', 4) == 'abcd'
    assert transport.read('missing', 3) == '\x00' * 3
    transport.write_wishbone(0x10, 0x99)
    assert transport.read_wishbone(0x10) == 0x99
    assert transport.read_wishbone(0x20) == 0


def test_dummy_transport_upload_and_listdev():
    transport = DummyTransport(host='127.0.0.1')
    transport.memory_devices = {'a': object()}
    assert transport.listdev() == transport.memory_devices.keys()
    assert transport.upload_to_ram_and_program('design.fpg')
    assert transport.get_system_information_from_transport() == ('design.fpg', None)
