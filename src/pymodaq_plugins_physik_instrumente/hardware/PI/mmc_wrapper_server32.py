import sys
from ctypes import windll, create_string_buffer, POINTER, byref, pointer
from ctypes import c_uint, c_int, c_char, c_char_p, c_void_p, c_short, c_long, c_bool, c_double, c_uint64, c_uint32, Array, CFUNCTYPE, WINFUNCTYPE
from ctypes import c_ushort, c_ulong, c_float
import os
from pyvisa import ResourceManager
from bitstring import Bits
from pathlib import Path
from msl.loadlib import Server32
from enum import Enum

here = Path(__file__).parent
dll_path = here.joinpath('win32')

os.add_dll_directory(str(dll_path.absolute().resolve()))


