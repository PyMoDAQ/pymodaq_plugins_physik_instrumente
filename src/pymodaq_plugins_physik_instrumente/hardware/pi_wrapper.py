
from typing import Tuple, List, Union
from pathlib import Path

import numpy as np
import os
from pipython import GCSDevice, GCSError
from pipython.pidevice.interfaces.gcsdll import get_gcstranslator_dir


from pymodaq_utils.enums import BaseEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_data import Unit
from pint.errors import UndefinedUnitError

from pymodaq_plugins_physik_instrumente.utils import Config, get_devices_and_dlls


logger = set_logger(get_module_name(__file__))

config = Config()
possible_dll_names = config['dll_names']
devices, devices_name, dll_names = get_devices_and_dlls(possible_dll_names)


ConnectionEnum = BaseEnum('ConnectionEnum', ['RS232', 'USB', 'TCP/IP'])


class PIWrapper:
    """
    Plugin using the pipython package wrapper. It is compatible with :
    DLLDEVICES = {
    'PI_GCS2_DLL': ['C-413', 'C-663.11', 'C-863.11', 'C-867', 'C-877', 'C-884', 'C-885', 'C-887',
                    'C-891', 'E-517', 'E-518', 'E-545', 'E-709', 'E-712', 'E-723', 'E-725',
                    'E-727', 'E-753', 'E-754', 'E-755', 'E-852B0076', 'E-861', 'E-870', 'E-871',
                    'E-873', 'C-663.12'],
    'C7XX_GCS_DLL': ['C-702', ],
    'C843_GCS_DLL': ['C-843', ],
    'C848_DLL': ['C-848', ],
    'C880_DLL': ['C-880', ],
    'E816_DLL': ['E-621', 'E-625', 'E-665', 'E-816', 'E816', ],
    'E516_DLL': ['E-516', ],
    'PI_Mercury_GCS_DLL': ['C-663.10', 'C-863.10', 'MERCURY', 'MERCURY_GCS1', ],
    'PI_HydraPollux_GCS2_DLL': ['HYDRA', 'POLLUX', 'POLLUX2', 'POLLUXNT', ],
    'E7XX_GCS_DLL': ['DIGITAL PIEZO CONTROLLER', 'E-710', 'E-761', ],
    'HEX_GCS_DLL': ['HEXAPOD', 'HEXAPOD_GCS1', ],
    'PI_G_GCS2_DLL': ['UNKNOWN', ],
    """

    def __init__(self):

        self._device: GCSDevice = None
        self._is_daisy: bool = False
        self._is_daisy_master: bool = True
        self.connection_type: ConnectionEnum = None
        self._device_id: str = None  # one of the possible values in devices

        self.daisy_ids: Tuple[int] = None
        self.daisy_id: int = 0

    @property
    def device(self) -> GCSDevice:
        """ Get the instance of the GCSDevice"""
        return self._device

    @device.setter
    def device(self, dev: GCSDevice):
        self._device = dev

    @property
    def device_id(self) -> str:
        """ Get the identifier of the device as enumerated in devices_name """
        return self._device_id

    @device_id.setter
    def device_id(self, dev_id: str):
        if dev_id in devices_name:
            self._device_id = dev_id

    def identify(self) -> str:
        """ Get the device string identifier """
        return self.device.qIDN()

    @property
    def axis_names(self) -> List[str]:
        """ Get the list of axis of the controller as a list of string"""
        return self.device.axes

    def get_axis_units(self, default='mm'):
        units = default
        try:
            # get units (experimental)
            if hasattr(self.device, 'qSPA'):
                units = \
                    self.device.qSPA(self.axis_names[0], 0x07000601)[self.axis_names[0]][0x07000601]
        except GCSError:
            # library not compatible with this set of commands
            logger.info('Could not get axis units from the controller make sure you set them '
                        f'programmatically, set as default to: {default}')
        try:
            if not (Unit(units).is_compatible_with('m') or Unit(units).is_compatible_with('°')):
                units = units.lower()  # One saw units returned as MM... which is MegaMolar
                if not (Unit(units).is_compatible_with('m') or Unit(units).is_compatible_with('°')):
                    logger.info(f'The units returned from the controller: {units} is not compatible'
                                f'with either length or degree (dimensionless)')
                    units = default
        except UndefinedUnitError:
            logger.info(f'The units returned from the controller: {units} is not defined in the '
                        f'pint registry')
            units = default
        return units

    @property
    def is_daisy(self):
        return self._is_daisy

    @is_daisy.setter
    def is_daisy(self, is_daisy: bool):
        self._is_daisy = is_daisy

    @property
    def is_daisy_master(self):
        return self._is_daisy_master

    @is_daisy_master.setter
    def is_daisy_master(self, is_daisy_master: bool):
        self._is_daisy_master = is_daisy_master

    def use_joystick(self, do_use=True):
        """ Enable or not the use of a joystick

        Parameters
        ----------
        do_use: bool
        """
        for ind, ax in enumerate(self.axis_names):
            if do_use:
                res = self.device.JAX(1, ind + 1, ax)
                res = self.device.JON(ind + 1, True)
            else:
                self.device.JON(ind + 1, False)

    def get_servo(self, axis: str):
        """ Check if servo on a given axis is on or not"""
        return self.device.qSVO(axis)[axis]

    def set_servo(self, axis: str, enable_servo=True):
        """ Turns on or off the closed loop

        Parameters
        ----------
        axis: str
            reference of the axis
        enable_servo: bool
        """
        if axis in self.axis_names:
            if self.get_servo(axis) != enable_servo:
                self.device.SVO(axis, enable_servo)

    def set_referencing(self, axes: Union[str, List[str]]):
        """ Attempt a referencing of the specified axis or list of axis

        Parameters
        ----------
        axes: str or list of str
            the str should be among self.axis_names
        """
        if not isinstance(axes, list):
            axes = [axes]
        for axe in axes:
            # set referencing mode
            if isinstance(axe, str):
                if self.is_referenced(axe):
                    if self.device.HasRON():
                        self.device.RON(axe, True)
                    self.device.FRF(axe)

    def get_axis_limits(self, axis_name: str):
        """

        Parameters
        ----------
        axis_name: str
            one of self.axis_names

        Returns
        -------
        (float, float) the min and max values of the specified axis
        """
        if hasattr(self.device, 'qTMN'):
            min_val = self.device.qTMN(axis_name)[axis_name]
        else:
            min_val = np.NaN
        if hasattr(self.device, 'qTMX'):
            max_val = self.device.qTMX(axis_name)[axis_name]
        else:
            max_val = np.NaN
        return min_val, max_val

    def close(self):
        """ close the current instance of GCSDevice instrument.
        """
        if self.device is not None:
            if not self.is_daisy:
                self.device.CloseConnection()
            else:
                self.device.CloseDaisyChain()

    def ini_device(self) -> GCSDevice:
        """ load the correct dll given the chosen device

        Returns
        -------
        GCSDevice: the instance of the device
        """

        try:
            self.close()
        except Exception as e:
            pass
        index = devices_name.index(self.device_id)
        gcsdll = dll_names[index]
        if gcsdll == 'serial':
            self.device = GCSDevice()
        else:
            self.device = GCSDevice(gcsdll=gcsdll)
        return self.device

    def connect_device(self):
        if self.connection_type is not None and self.device_id is not None:
            if self.device is None:
                self.ini_device()
            if not self.is_daisy:  # simple connection
                if self.connection_type.name == 'USB':
                    self.device.ConnectUSB(self.device_id)
                elif self.connection_type.name == 'TCP/IP':
                    self.device.ConnectTCPIPByDescription(self.device_id)
                elif self.connection_type.name == 'RS232':
                    self.device.ConnectRS232(int(self.device_id[3:]), 19200)
                    # in this case device is a COM port, and one should use 1 for COM1 for instance

            else:  # one use a daisy chain connection with a master device and slaves
                if self.is_daisy_master:
                    if self.connection_type.name == 'USB':
                        dev_ids = self.device.OpenUSBDaisyChain(self.device_id)
                    elif self.connection_type.name == 'TCP/IP':
                        dev_ids = self.device.OpenTCPIPDaisyChain(self.device_id)
                    elif self.connection_type.name == 'RS232':
                        dev_ids = self.device.OpenRS232DaisyChain(int(self.device_id[3:]))
                        # in this case device is a COM port, and one should use 1 for COM1 for instance

                    self.daisy_ids = dev_ids

                if self.daisy_id in self.daisy_ids:
                    self.device.ConnectDaisyChainDevice(self.device.dcid, self.daisy_id)

    def is_referenced(self, axis_name: str):
        """ Get the referenced status of the given axis

        Parameters
        ----------
        axis_name: str
            one of self.axis_names

        Returns
        -------
        bool
        """
        if self.device.HasqFRF():
            return self.device.qFRF(axis_name)[axis_name]
        else:
            return False

    def stop(self):
        """ Stop the motion of the connected device"""
        self.device.StopAll()

    def get_axis_position(self, axis_name: str) -> float:
        """ Get the specified axis position

        Parameters
        ----------
        axis_name: str
        """
        return self.device.qPOS(axis_name)[axis_name]

    def move_absolute(self, axis_name: str, position: float):
        """ Move the specified axis to the given absolute position

        Parameters
        ----------
        axis_name: str
        position: float
        """
        self.device.MOV(axis_name, position)

    def move_relative(self, axis_name: str, position: float):
        """ Move the specified axis to the given relative position

        Parameters
        ----------
        axis_name: str
        position: float
        """
        if self.device.HasMVR():
            self.device.MVR(axis_name, position)

    def move_home(self, axis_name: str):
        """ Move the specified axis to it's home position

        Parameters
        ----------
        axis_name: str

        See Also
        --------
        set_referencing
        """
        self.set_referencing(axis_name)
        if self.device.HasGOH():
            self.device.GOH(axis_name)
        elif self.device.HasFRF():
            self.device.FRF(axis_name)
        else:
            self.move_absolute(axis_name, 0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        print("\nExecution type:", exc_type)
        print("\nExecution value:", exc_val)
        print("\nTraceback:", exc_tb)
        return True

    def set_1D_waveform(self, amplitude: float, offset=0., npts=1000,
                        axis: int = 1, rate: int = 1):
        start_point = 0
        speed_up_down = 0
        seg_length = npts + start_point + npts / 2
        wavelength = npts + npts / 2
        curve_center_point = npts
        self.device.WCL(axis)
        self.device.WAV_RAMP(axis, 0, seg_length, 'X', wavelength,
                             speed_up_down, amplitude, offset, curve_center_point)
        self.device.WSL(axis, axis)  # affect axis axis to wavetable 1
        self.device.WTR(0, rate, 1)  # set the rate (multiple of servo cycles)

    def start_waveform(self, axis: int = 1, cycles: int = 1):
        self.device.WGC(axis, cycles)  # set the number of cycles
        self.device.WGO(axis, 1)

    def stop_waveform(self, axis: int = 1):
        self.device.WGO(axis, 0)

    def get_servo_cycle_duration(self) -> float:
        """get the servo cycle duration in seconds"""
        return self.device.qSPA('1', 0x0E000200)['1'][0x0E000200]

    def set_trigger_waveform(self, points: List[int],  do: int = 1):
        # clear previous triggers
        self.device.TWC()
        # set trigger on digital output line do on the wave generator output
        self.device.CTO(do, 3, 4)
        # set the trigger position on the wave points
        self.device.TWS(do, points, [1 for _ in points])


if __name__ == '__main__':

    with PIWrapper() as pidev:
        pidev.connection_type = ConnectionEnum['USB']
        pidev.device_id = devices_name[0]

        pidev.connect_device()

        print(pidev.identify())
        print(f'Servo cycle: {pidev.get_servo_cycle_duration()}, freqency: {1/pidev.get_servo_cycle_duration()}')

        axes = pidev.axis_names
        for axis in axes:
            print(f'Axis {axis} limits are: {pidev.get_axis_limits(axis)}')
            print(f'Axis {axis} position is: {pidev.get_axis_position(axis)}')
            if not pidev.is_referenced(axis):
                pidev.set_servo(axis, True)
                pidev.set_referencing(axis)
                print(f'Axis {axis} referencing is: {pidev.is_referenced(axis)}')
        axis = 2
        pidev.set_1D_waveform(10, 0, 100, rate=200, axis=axis)
        pidev.set_trigger_waveform([1], do=1)
        pidev.start_waveform(axis, 1)

        print(f"axis 1 is at : {pidev.get_axis_position('1')}")
    pass

