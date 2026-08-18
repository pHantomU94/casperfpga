import struct

import pytest

from casperfpga import skarab_definitions as sd
from casperfpga.transport_skarab import (
    InvalidDeviceType,
    NonVolatileLogRetrievalError,
    SkarabInvalidResponse,
    SkarabReadFailed,
    SkarabTransport,
    SkarabUnknownDeviceError,
    SkarabWriteFailed,
)


class FakeLogger(object):
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        self.messages.append(("debug", msg))

    def info(self, msg):
        self.messages.append(("info", msg))

    def warning(self, msg):
        self.messages.append(("warning", msg))

    warn = warning

    def error(self, msg):
        self.messages.append(("error", msg))


class FakeResponse(object):
    def __init__(self, packet):
        self.packet = packet


class FakeRequest(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def make_transport():
    transport = SkarabTransport.__new__(SkarabTransport)
    transport.host = "fake-skarab"
    transport.timeout = 1
    transport.retries = 2
    transport.logger = FakeLogger()
    transport.send_packet_calls = []
    transport.send_packet_response = None

    def fake_send_packet(request, timeout=None, retries=None):
        transport.send_packet_calls.append((request, timeout, retries))
        response = transport.send_packet_response
        if callable(response):
            return response(request, timeout, retries)
        return response

    transport.send_packet = fake_send_packet
    return transport


def test_skarab_data_pack_unpack_and_reverse_byte():
    high, low = SkarabTransport.data_split_and_pack(0x12345678)
    assert high == b"\x12\x34"
    assert low == b"\x56\x78"
    assert SkarabTransport.data_unpack_and_merge(0x1234, 0x5678) == 0x12345678
    assert SkarabTransport.reverse_byte(0b01010110) == 0b01101010


def test_skarab_verify_bytes_now_success_and_failures():
    transport = make_transport()
    assert transport.verify_bytes_now([1, 2], [1, 2]) is True

    with pytest.raises(sd.SkarabProgrammingError):
        transport.verify_bytes_now([1], [1, 2])

    with pytest.raises(sd.SkarabProgrammingError):
        transport.verify_bytes_now([1, 2], [1, 3])


def test_skarab_packet_count_and_version_helpers(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "SdramReconfigureReq", FakeRequest)
    transport.send_packet_response = FakeResponse(
        {
            "num_ethernet_frames": 10,
            "num_ethernet_bad_frames": 1,
            "num_ethernet_overload_frames": 2,
        }
    )
    assert transport.check_programming_packet_count() == {
        "Ethernet Frames": 10,
        "Bad Ethernet Frames": 1,
        "Overload Ethernet Frames": 2,
    }

    transport.read_board_reg = lambda addr, timeout=None, retries=None: 0xC0010002
    assert transport.get_virtex7_firmware_version() == (1, 1, "1.2")

    transport.read_board_reg = lambda addr, timeout=None, retries=None: 0x00030004
    assert transport.get_microblaze_hardware_version() == "3.4"


def test_skarab_front_panel_led_controls_and_reset_behaviour():
    transport = make_transport()
    writes = []
    transport.write_board_reg = lambda addr, value: writes.append((addr, value))
    transport.front_panel_status_leds(True, False, True, False, True, False, True, False)
    assert writes == [
        (
            sd.C_WR_FRONT_PANEL_STAT_LED_ADDR,
            sd.FRONT_PANEL_STATUS_LED0
            | sd.FRONT_PANEL_STATUS_LED2
            | sd.FRONT_PANEL_STATUS_LED4
            | sd.FRONT_PANEL_STATUS_LED6,
        )
    ]

    transport.write_board_reg = lambda addr, value: FakeResponse({"reg_data_low": value})
    assert transport.control_front_panel_leds_write(False) is True

    transport.write_board_reg = lambda addr, value: FakeResponse({"reg_data_low": 99})
    with pytest.raises(SkarabWriteFailed):
        transport.control_front_panel_leds_write(True)

    transport.read_board_reg = lambda addr: 1
    assert transport.control_front_panel_leds_read() is None


def test_skarab_hmc_i2c_write_and_read_requests_use_bytes_payload(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "WriteHMCI2CReq", FakeRequest)
    monkeypatch.setattr(sd, "ReadHMCI2CReq", FakeRequest)

    transport.send_packet_response = FakeResponse({"write_success": True})
    assert transport.write_hmc_i2c(1, 0x10, 0x11223344, 0x55667788) is True
    request = transport.send_packet_calls[-1][0]
    assert request.args[2] == b"\x00\x11\x00\x22\x00\x33\x00\x44"
    assert request.args[3] == b"\x00\x55\x00\x66\x00\x77\x00\x88"

    transport.send_packet_response = FakeResponse(
        {"read_success": True, "read_bytes": [0x11, 0x22, 0x33, 0x44]}
    )
    assert transport.read_hmc_i2c(1, 0x10, 0xAABBCCDD) == 0x11223344
    request = transport.send_packet_calls[-1][0]
    assert request.args[2] == b"\x00\xaa\x00\xbb\x00\xcc\x00\xdd"


def test_skarab_hmc_i2c_error_paths(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "WriteHMCI2CReq", FakeRequest)
    monkeypatch.setattr(sd, "ReadHMCI2CReq", FakeRequest)

    transport.send_packet_response = None
    with pytest.raises(SkarabInvalidResponse):
        transport.write_hmc_i2c(0, 0x10, 0, 0)

    transport.send_packet_response = FakeResponse({"write_success": False})
    with pytest.raises(SkarabWriteFailed):
        transport.write_hmc_i2c(0, 0x10, 0, 0)

    transport.send_packet_response = None
    with pytest.raises(SkarabInvalidResponse):
        transport.read_hmc_i2c(0, 0x10, 0)

    transport.send_packet_response = FakeResponse({"read_success": False, "read_bytes": [0, 0, 0, 0]})
    with pytest.raises(SkarabReadFailed):
        transport.read_hmc_i2c(0, 0x10, 0)


def test_skarab_tunable_parameters_and_one_wire_decoders():
    transport = make_transport()
    transport.one_wire_ds2433_read_mem = lambda *args, **kwargs: [20, 0, 30, 0, 40, 0, 5, 60, 0]
    assert transport.get_tunable_parameters() == {
        "dhcp_init_time": 2.0,
        "dhcp_retry_rate": 3.0,
        "hmc_reconfig_timeout": 4.0,
        "hmc_reconfig_max_retries": 5,
        "link_mon_timeout": 6.0,
    }

    raw_hmc = [1, 0, 0, 0, 5, 0, 0, 0]
    transport.one_wire_ds2433_read_mem = lambda *args, **kwargs: raw_hmc
    assert transport.get_hmc_reconfigure_stats(0) == {
        "hmc_0": {
            "hmc_init_failures_recorded": 1,
            "hmc_total_init_retries_recorded": 5,
        }
    }

    transport.one_wire_ds2433_read_mem = lambda *args, **kwargs: [0xAA, 0, 0, 0, 0xBB, 0xCC, 0xDD]
    assert transport.get_mezzanine_signature(sd.MEZ_0_ONE_WIRE_PORT) == 0xAABBCCDD


def test_skarab_network_control_responses(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "ResetDHCPStateMachineReq", FakeRequest)
    monkeypatch.setattr(sd, "MulticastLeaveGroupReq", FakeRequest)
    monkeypatch.setattr(sd, "GetDHCPMonitorTimeoutReq", FakeRequest)

    transport.send_packet_response = FakeResponse({"reset_error": 0, "link_id": 1})
    assert transport.reset_dhcp_state_machine(1) is True

    transport.send_packet_response = FakeResponse({"reset_error": 2, "link_id": 1})
    with pytest.raises(SkarabUnknownDeviceError):
        transport.reset_dhcp_state_machine(1)

    transport.send_packet_response = FakeResponse({"success": True})
    assert transport.leave_multicast_group(1) is True

    transport.send_packet_response = FakeResponse({"success": False})
    assert transport.leave_multicast_group(1) is False

    transport.send_packet_response = FakeResponse({"dhcp_monitor_timeout": 250})
    assert transport.get_dhcp_link_mon_timeout() == 25.0


def test_skarab_fault_helpers_and_scaling():
    transport = make_transport()
    assert transport._sign_extend(0b11111, 5) == -1
    assert transport._check_fault_type(0, 2, sensor="voltage") == "Resequence Error"
    assert transport._check_fault_type(1, 0, sensor="current") == "IOUT Over Current Fault"
    assert transport.get_fault_timestamp(0x1234, 0x5678) == 0x12345678
    assert transport._voltage_handler_logging(100, 0, sd.P5V_VOLTAGE_MON_PAGE) == 250.0
    assert transport._current_handler_logging(100, 0, sd.P5V_CURRENT_MON_PAGE) == 500.0


def test_skarab_get_max31785_hw_logs_success_and_errors(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "GetFanControllerLogsReq", FakeRequest)

    good_log = [0, 1, 0, 0x8000] + [0] * 11
    empty_log = [0xFFFF] * 15
    transport.send_packet_response = FakeResponse(
        {
            "log_entry_success": True,
            "fan_cont_mon_logs": [good_log] + [empty_log] * 14,
        }
    )
    data = transport.get_max31785_hw_logs()
    assert data[0] == (0, "MEZZANINE_1_TEMP", "VOUT Over Voltage Fault")
    assert data[-1] == (14, None)

    transport.send_packet_response = FakeResponse(
        {
            "log_entry_success": False,
            "fan_cont_mon_logs": [],
        }
    )
    with pytest.raises(NonVolatileLogRetrievalError):
        transport.get_max31785_hw_logs()


def test_skarab_get_ucd90120a_hw_logs_and_invalid_device(monkeypatch):
    transport = make_transport()
    monkeypatch.setattr(sd, "GetVoltageLogsReq", FakeRequest)
    monkeypatch.setattr(sd, "GetCurrentLogsReq", FakeRequest)

    voltage_logs = [[1, 0, sd.P5V_VOLTAGE_MON_PAGE, 100, 0, 0x1234, 0x5678]] + [[0xFFFF] * 7] * 15
    transport.send_packet_response = FakeResponse(
        {
            "log_entry_success": 0x8000,
            "voltage_mon_logs": voltage_logs,
        }
    )
    data = transport.get_ucd90120a_hw_logs("voltage")
    assert data[0] == [16, None, "ok"]
    assert data[-1] == [1, "P5V_VOLTAGE", "VOUT Over Voltage Fault", 250.0, "fail", 0x12345678]

    current_logs = [[1, 0, sd.P5V_CURRENT_MON_PAGE, 100, 0, 0, 1]] + [[0xFFFF] * 7] * 15
    transport.send_packet_response = FakeResponse(
        {
            "log_entry_success": 0x8000,
            "current_mon_logs": current_logs,
        }
    )
    current_data = transport.get_ucd90120a_hw_logs("current")
    assert current_data[-1][2] == "IOUT Over Current Fault"
    assert current_data[-1][3] == 500.0

    with pytest.raises(InvalidDeviceType):
        transport.get_ucd90120a_hw_logs("mystery")
