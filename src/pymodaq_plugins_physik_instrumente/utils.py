# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from typing import Iterable
from pathlib import Path

from pymodaq_utils.config import BaseConfig, USER

import serial.tools.list_ports as list_ports

from pymodaq_utils.utils import is_64bits
from pipython import GCSDevice, GCSError
from pipython.pidevice.interfaces.gcsdll import get_gcstranslator_dir


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"


def get_devices_and_dlls(possible_dll_names: Iterable[str]):
    """ Get the connected devices and their corresponding dlls from a list of
    potential dlls

    Parameters
    ----------
    possible_dll_names
        an iterable of possible dlls to be used to get connected devices

    Returns
    -------
    devices: the full id of the devices including its dll
    devices_name: the name of the devices
    dll_names: the name of the dlls
    """

    dll_in_testing_order = []

    for dll_name in possible_dll_names:
        if is_64bits():
            filename = f'{dll_name}_x64.dll'
        else:
            filename = f'{dll_name}.dll'
        file_path = Path(get_gcstranslator_dir()).joinpath(filename)
        if file_path.is_file():
            dll_in_testing_order.append(filename)

    devices = []
    dll_names = []
    devices_name = []
    for _dll_name in dll_in_testing_order:
        gcs_device = GCSDevice(gcsdll=_dll_name)
        _devices = []
        _devices.extend(gcs_device.EnumerateUSB())
        _devices.extend(gcs_device.EnumerateTCPIPDevices())
        for dev in _devices:
            dll_names.append(_dll_name)
            devices.append(f'{dev}/{_dll_name}')
        devices_name.extend(_devices)

    com_ports = list(list_ports.comports())
    devices.extend([str(port.name) for port in com_ports])
    devices_name.extend([str(port.name) for port in com_ports])
    dll_names.extend(['serial' for port in com_ports])

    return devices, devices_name, dll_names