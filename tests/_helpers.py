import struct


class FakeParent(object):
    def __init__(self, host='fake-host'):
        self.host = host
        self.memory_devices = {}
        self.read_queue = {}
        self.read_uint_queue = {}
        self.read_calls = []
        self.write_int_calls = []

    def queue_read(self, device_name, *values):
        self.read_queue.setdefault(device_name, []).extend(values)

    def queue_read_uint(self, device_name, *values):
        self.read_uint_queue.setdefault(device_name, []).extend(values)

    def read(self, device_name, size, offset=0):
        self.read_calls.append((device_name, size, offset))
        queue = self.read_queue.get(device_name, [])
        if queue:
            return queue.pop(0)
        return b'\x00' * size

    def read_uint(self, device_name, **kwargs):
        queue = self.read_uint_queue.get(device_name, [])
        if queue:
            return queue.pop(0)
        return 0

    def write_int(self, device_name, integer, blindwrite=False, word_offset=0):
        self.write_int_calls.append(
            (device_name, integer, blindwrite, word_offset)
        )


class FakeRegister(object):
    def __init__(self, uint_values=None, read_value=None):
        self.uint_values = list(uint_values or [])
        self.read_value = {'data': {'reg': 0}, 'timestamp': 0} if read_value is None else read_value
        self.write_int_calls = []

    def read_uint(self):
        if self.uint_values:
            return self.uint_values.pop(0)
        return 0

    def write_int(self, value):
        self.write_int_calls.append(value)

    def read(self):
        return self.read_value


def pack_u32(value):
    return struct.pack('>I', value)


class FakeReply(object):
    def __init__(self, *arguments, ok=True):
        self.arguments = list(arguments)
        self._ok = ok

    def reply_ok(self):
        return self._ok


class FakeInform(object):
    def __init__(self, name, *arguments):
        self.name = name
        self.arguments = list(arguments)


class FakeTftpContext(object):
    def __init__(self):
        self.ended = 0

    def end(self):
        self.ended += 1


class FakeTftpClient(object):
    def __init__(self):
        self.context = FakeTftpContext()
        self.downloads = []
        self.uploads = []
        self.download_results = []
        self.upload_results = []

    def queue_download_result(self, value):
        self.download_results.append(value)

    def queue_upload_result(self, value):
        self.upload_results.append(value)

    def download(self, name, buf, timeout=None):
        self.downloads.append((name, timeout))
        if self.download_results:
            result = self.download_results.pop(0)
            if isinstance(result, Exception):
                raise result
            buf.write(result)
            return
        return

    def upload(self, name, buf, timeout=None):
        payload = buf.getvalue()
        self.uploads.append((name, payload, timeout))
        if self.upload_results:
            result = self.upload_results.pop(0)
            if isinstance(result, Exception):
                raise result
        return


class FakeTftpFileNotFoundError(Exception):
    pass


class FakeTftpyModule(object):
    class TftpShared(object):
        TftpFileNotFoundError = FakeTftpFileNotFoundError
