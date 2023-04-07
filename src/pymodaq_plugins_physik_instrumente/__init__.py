from pathlib import Path
from pymodaq.utils.logger import set_logger, get_module_name


with open(str(Path(__file__).parent.joinpath('VERSION')), 'r') as fvers:
    __version__ = fvers.read().strip()
