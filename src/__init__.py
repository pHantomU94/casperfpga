"""
control and monitor fpga-based casper designs.
"""

# import all the main classes that we'll use often
try:
    from . import progska
except ImportError:
    # The optional C extension is only required for specific SKARAB upload
    # paths. Keep the package importable when it has not been built in-place.
    progska = None
from .bitfield import Bitfield, Field
from .katadc import KatAdc
from .casperfpga import CasperFpga
from .transport_katcp import KatcpTransport
from .transport_tapcp import TapcpTransport
from .transport_skarab import SkarabTransport
from .transport_itpm import ItpmTransport
from .transport_redis import RedisTapcpTransport
from .transport_localpcie import LocalPcieTransport
from .transport_remotepcie import RemotePcieTransport
from .transport_alveo import AlveoTransport
from .memory import Memory
from .network import IpAddress, Mac
from .qdr import Qdr
from .register import Register
from .sbram import Sbram
from .snap import Snap
from .snapadc import SnapAdc
from .tengbe import TenGbe
from . import skarab_fileops

from _casperfpga_version import get_runtime_version

__version__ = get_runtime_version()

name = "casperfpga"

# end
