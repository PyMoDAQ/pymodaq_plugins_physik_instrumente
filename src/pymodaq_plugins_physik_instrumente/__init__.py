from pathlib import Path
from .utils import Config
from pymodaq_utils.utils import get_version, PackageNotFoundError
from pymodaq_utils.logger import set_logger, get_module_name

config = Config()
try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'



