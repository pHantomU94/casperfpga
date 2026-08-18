import socket

import pytest

from casperfpga.network import IpAddress, Mac


def test_mac_round_trip_and_repr():
    mac = Mac('01:23:45:67:89:ab')
    assert int(mac) == 0x0123456789AB
    assert str(mac) == '01:23:45:67:89:AB'
    assert repr(mac) == 'Mac(01:23:45:67:89:AB)'
    assert mac == '01:23:45:67:89:AB'
    assert mac == 0x0123456789AB
    assert mac.packed() == b'\x00\x00\x01#Eg\x89\xab'


def test_mac_from_int_and_existing_instance():
    original = Mac(0xFE0001020304)
    clone = Mac(original)
    assert clone == original
    assert clone.mac_str == 'FE:00:01:02:03:04'


def test_mac_str2mac_rejects_invalid_format():
    with pytest.raises(RuntimeError):
        Mac.str2mac('not-a-mac')


def test_mac_from_roach_hostname_variants():
    roach = Mac.from_roach_hostname('roach0a0b0c', 7)
    skarab = Mac.from_roach_hostname('skarab0a0b0c-01', 7)
    assert str(roach) == 'FE:00:0A:0B:0C:07'
    assert str(skarab) == 'FE:00:0A:0B:0C:07'


def test_mac_from_roach_hostname_rejects_invalid_prefix():
    with pytest.raises(RuntimeError):
        Mac.from_roach_hostname('board0a0b0c', 1)


def test_ip_address_round_trip_comparison_and_packed():
    ip = IpAddress('239.1.2.3')
    assert int(ip) == (239 << 24) + (1 << 16) + (2 << 8) + 3
    assert str(ip) == '239.1.2.3'
    assert ip.is_multicast()
    assert ip == '239.1.2.3'
    assert ip > IpAddress('239.1.2.2')
    assert ip.packed() == b'\xef\x01\x02\x03'


def test_ip_address_falls_back_to_integer_string_when_dns_lookup_fails(monkeypatch):
    def raiser(host):
        raise socket.gaierror(host)

    monkeypatch.setattr(socket, 'gethostbyname', raiser)
    ip = IpAddress('3232235777')
    assert str(ip) == '192.168.1.1'
    assert int(ip) == 3232235777


def test_ip_address_uses_dns_resolution(monkeypatch):
    monkeypatch.setattr(socket, 'gethostbyname', lambda host: '10.0.0.5')
    ip = IpAddress('fpga.local')
    assert str(ip) == '10.0.0.5'
    assert int(ip) == (10 << 24) + 5


def test_ip_str2ip_rejects_invalid_format():
    with pytest.raises(RuntimeError):
        IpAddress.str2ip('127.0.0')


def test_ip_eq_rejects_unknown_type():
    with pytest.raises(TypeError):
        IpAddress('1.2.3.4') == object()
