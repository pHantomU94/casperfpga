import zlib
import hashlib
import logging
import time
import os
import subprocess
import glob
import re
from mmap import mmap, PROT_READ, PROT_WRITE, MAP_SHARED

MEM_DEV = '/dev/mem'
# Size of AXI-lite memory to map
MAP_SIZE    = 0x20000000 # 512 MiB
AXIL_OFFSET = 0xA0000000

from .transport import Transport
from .utils import parse_fpg

__author__ = 'jackh'
__date__ = 'June 2023'

class LocalMemTransport(Transport):
    """
    The transport interface for a locally-connected PCIe FPGA card.
    """

    def __init__(self, **kwargs):
        """
        :param host: The host-device identifier string (see `getXdmaIdFromTarget`)
        :param parent_fpga: Instance of parent_fpga
        :param fpgfile: filepath to fpg image, setting the fpg template
            restriction
        """
        Transport.__init__(self, **kwargs)

        try:
            # Entry point is always via casperfpga.CasperFpga
            self.parent = kwargs['parent_fpga']
            self.logger = self.parent.logger
        except KeyError:
            errmsg = 'parent_fpga argument not supplied when creating transport'
            # Pointless trying to log to a logger
            raise RuntimeError(errmsg)

        # Local char devices for comms
        self._mem_dev = MEM_DEV
        
        new_connection_msg = '*** NEW CONNECTION MADE TO {} ***'.format(self.host)
        self.logger.debug(new_connection_msg)
        self.fd = os.open(self._mem_dev, os.O_RDWR | os.O_SYNC)
        self.axil_mm = mmap(self.fd, MAP_SIZE, offset=AXIL_OFFSET, flags=MAP_SHARED, prot=PROT_READ | PROT_WRITE)

    def __del__(self):
        self.axil_mm.close()
        os.close(self.fd)
        
    def is_connected(self,
                     timeout=None,
                     retries=None):
        """
        'ping' the board to see if it is connected and running.
        Tries to read a register

        :return: Boolean - True/False - Success/Fail
        """

        try:
            data = self.read(0, 4)
            return True
        except:
            return False
    
    def is_running(self):
        """
        Is the FPGA programmed and running a toolflow image?
        
        *** Not yet implemented ***

        :return: True or False
        """
        return True

    def _get_device_address(self, device_name):
        # map device name to address, if can't find, bail
        if self.memory_devices and (device_name in self.memory_devices):
            return self.memory_devices[device_name].address - AXIL_OFFSET
        errmsg = 'Could not find device: %s' % device_name
        self.logger.error(errmsg)
        raise ValueError(errmsg)

    def read(self, device_name, size, offset=0):
        """
        Read size-bytes of binary data.

        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :return: binary data string
        """
        addr = self._get_device_address(device_name) + offset
        return self.axil_mm[addr : addr + size]


    def blindwrite(self, device_name, data, offset=0):
        """
        Unchecked data write.

        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        """

        size = len(data)
        assert (type(data) == bytes), 'Must supply binary data'
        assert (size % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'

        addr = self._get_device_address(device_name) + offset
        self.axil_mm[addr : addr + size] = data
