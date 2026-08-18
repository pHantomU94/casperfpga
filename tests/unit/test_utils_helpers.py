from io import BytesIO

import pytest

from casperfpga import utils


class FakeFpga(object):
    def __init__(self, host, running=True):
        self.host = host
        self.running = running
        self.deprogrammed = False
        self.disconnected = False

    def is_running(self):
        return self.running

    def deprogram(self):
        self.deprogrammed = True
        return True

    def disconnect(self):
        self.disconnected = True
        return True


def test_create_meta_dictionary_and_get_helpers():
    meta = utils.create_meta_dictionary([
        ('dev', 'tag:a', 'param1', 'value1'),
        ('dev', 'tag:a', 'param2', 'value2'),
    ])
    assert meta == {'dev': {'tag': 'tag:a', 'param1': 'value1', 'param2': 'value2'}}
    assert utils.get_kwarg('field', {'field': 5}, 0) == 5
    assert utils.get_kwarg('missing', {}, 7) == 7
    assert utils.get_hostname(host='roach,design.fpg') == ('roach', 'design.fpg')


def test_create_meta_dictionary_rejects_tag_mismatch():
    with pytest.raises(ValueError):
        utils.create_meta_dictionary([
            ('dev', 'tag:a', 'param1', 'value1'),
            ('dev', 'tag:b', 'param2', 'value2'),
        ])


def test_parse_fpg_rejects_invalid_header():
    bad = BytesIO(b'not-an-fpg\n')
    with pytest.raises(RuntimeError):
        utils.parse_fpg(bad, isbuf=True)


def test_check_changing_status_success_and_failures(monkeypatch):
    counter = utils.CheckCounter('ctr', must_change=True, required=True)
    values = iter([{'ctr': 1}, {'ctr': 2}, {'ctr': 3}])
    monkeypatch.setattr(utils.time, 'sleep', lambda _: None)
    ok, message = utils.check_changing_status([counter], lambda: next(values), 0, 3)
    assert ok is True
    assert message == ''

    static_counter = utils.CheckCounter('static', must_change=False, required=True)
    values = iter([{'static': 1}, {'static': 2}])
    ok, message = utils.check_changing_status([static_counter], lambda: next(values), 0, 2)
    assert ok is False
    assert 'static changing' in message


def test_check_changing_status_validates_inputs_and_required_fields(monkeypatch):
    monkeypatch.setattr(utils.time, 'sleep', lambda _: None)
    with pytest.raises(ValueError):
        utils.check_changing_status([], lambda: {}, 0, 1)

    required = utils.CheckCounter('missing', must_change=True, required=True)
    ok, message = utils.check_changing_status([required], lambda: {}, 0, 2)
    assert ok is False
    assert message == 'required field missing not found'


def test_check_target_func_normalizes_inputs():
    assert utils._check_target_func('disconnect') == ('disconnect', (), {})
    assert utils._check_target_func((len,)) == (len, (), {})
    assert utils._check_target_func((len, (1,))) == (len, (1,), {})
    with pytest.raises(RuntimeError):
        utils._check_target_func((len, (), {}, 'extra'))


def test_threaded_fpga_function_and_operation(monkeypatch):
    monkeypatch.setattr(utils.time, 'sleep', lambda _: None)
    fpgas = [FakeFpga('a'), FakeFpga('b')]
    result = utils.threaded_fpga_function(fpgas, 1, 'is_running')
    assert result == {'a': True, 'b': True}

    def mark(fpga, suffix=''):
        return fpga.host + suffix

    result = utils.threaded_fpga_operation(fpgas, 1, (mark, ('-done',), {}), num_retries=1, retry_sleep_time=0)
    assert result == {'a': 'a-done', 'b': 'b-done'}


def test_hosts_from_dhcp_leases_and_socket_closer(tmp_path):
    leases = tmp_path / 'dnsmasq.leases'
    leases.write_text(
        '1 aa 10.0.0.1 roach001 xx\n'
        '1 bb 10.0.0.2 * xx\n'
        '1 cc 10.0.0.3 skarab001 xx\n'
        '1 dd 10.0.0.4 other xx\n'
    )
    hosts, filename = utils.hosts_from_dhcp_leases(leases_file=str(leases))
    assert hosts == ['roach001', 'skarab001']
    assert filename == str(leases)

    class FakeSocket(object):
        def __init__(self):
            self.shutdown_called = False
            self.close_called = False

        def shutdown(self, how):
            self.shutdown_called = True

        def close(self):
            self.close_called = True

    sock = FakeSocket()
    utils.socket_closer('test', sock)
    assert sock.shutdown_called is True
    assert sock.close_called is True


def test_deprogram_hosts(monkeypatch):
    fpga_a = FakeFpga('a', running=True)
    fpga_b = FakeFpga('b', running=False)
    monkeypatch.setattr(utils, 'threaded_create_fpgas_from_hosts', lambda hosts: [fpga_a, fpga_b])

    def fake_threaded_fpga_function(fpgas, timeout, target):
        if target == 'is_running':
            return {fpga.host: fpga.running for fpga in fpgas}
        if target == 'deprogram':
            for fpga in fpgas:
                fpga.deprogram()
            return {fpga.host: True for fpga in fpgas}
        if target == 'disconnect':
            for fpga in fpgas:
                fpga.disconnect()
            return {fpga.host: True for fpga in fpgas}
        raise AssertionError(target)

    monkeypatch.setattr(utils, 'threaded_fpga_function', fake_threaded_fpga_function)
    utils.deprogram_hosts(['a', 'b'])
    assert fpga_a.deprogrammed is True
    assert fpga_a.disconnected is True
    assert fpga_b.disconnected is True

    with pytest.raises(RuntimeError):
        utils.deprogram_hosts([])
