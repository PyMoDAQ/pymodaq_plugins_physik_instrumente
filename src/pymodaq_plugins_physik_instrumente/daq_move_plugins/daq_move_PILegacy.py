
from typing import Tuple
from pathlib import Path

import numpy as np
import os
from pipython import GCSDevice, GCSError
from pipython.pidevice.interfaces.gcsdll import get_gcstranslator_dir

import serial.tools.list_ports as list_ports

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main, comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo, is_64bits, find_keys_from_val
from pymodaq.utils.parameter.utils import iter_children


from pymodaq_plugins_physik_instrumente.utils import Config, get_devices_and_dlls


config = Config()
possible_dll_names = config['dll_names']
devices, devices_name, dll_names = get_devices_and_dlls(possible_dll_names)


class DAQ_Move_PILegacy(DAQ_Move_base):
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

    _controller_units = 'mm'  # dependent on the stage type so to be updated accordingly using
    # self.controller_units = new_unit


    is_multiaxes = True
    stage_names = []
    _epsilon = 0.01

    params = [
        {'title': 'Connection_type:', 'name': 'connect_type', 'type': 'list',
         'value': 'USB', 'values': ['USB', 'TCP/IP', 'RS232']},
        {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'limits': devices},
        {'title': 'Daisy Chain Options:', 'name': 'dc_options', 'type': 'group', 'children': [
            {'title': 'Use Daisy Chain:', 'name': 'is_daisy', 'type': 'bool', 'value': False},
            {'title': 'Is master?:', 'name': 'is_daisy_master', 'type': 'bool', 'value': False},
            {'title': 'Daisy Master Id:', 'name': 'daisy_id', 'type': 'int'},
            {'title': 'Daisy Devices:', 'name': 'daisy_devices', 'type': 'list'},
            {'title': 'Index in chain:', 'name': 'index_in_chain', 'type': 'int', 'enabled': True}]},
        {'title': 'Use Joystick:', 'name': 'use_joystick', 'type': 'bool', 'value': False},
        {'title': 'Closed loop?:', 'name': 'closed_loop', 'type': 'bool', 'value': True},
        {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Axis Info:', 'name': 'axis_infos', 'type': 'group', 'children': [
            {'title': 'Min:', 'name': 'min', 'type': 'float'},
            {'title': 'Max:', 'name': 'max', 'type': 'float'},
            ]},
        ] + comon_parameters_fun(is_multiaxes, stage_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: GCSDevice = None
        self.is_referencing_function = True
        self._device = None

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, device):
        self._device = device

    def commit_settings(self, param):
        """

        """
        try:
            if param.name() == 'use_joystick':
                axes = self.controller.axes
                for ind, ax in enumerate(axes):
                    try:
                        if param.value():
                            res = self.controller.JAX(1, ind + 1, ax)
                            res = self.controller.JON(ind + 1, True)
                        else:
                            self.controller.JON(ind + 1, False)
                    except Exception as e:
                        pass

                pass
            elif param.name() == 'axis' and param.name() in iter_children(self.settings.child('multiaxes')):
                self.settings.child('closed_loop').setValue(self.controller.qSVO(param.value())[param.value()])
                self.set_referencing(self.axis_name)
                self.set_axis_limits(self.get_axis_limits())

            elif param.name() == 'closed_loop':
                axe = self.axis_name
                if self.controller.qSVO(axe)[axe] != self.settings['closed_loop']:
                    self.controller.SVO(axe, param.value())

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [getLineInfo() + str(e), 'log']))

    def ini_device(self) -> GCSDevice:
        """ load the correct dll given the chosen device

        """

        try:
            self.close()
        except Exception as e:
            pass
        index = devices.index(self.settings['devices'])
        gcsdll = dll_names[index]
        if gcsdll == 'serial':
            return GCSDevice()
        else:
            return GCSDevice(gcsdll=gcsdll)

    def connect_device(self):
        if not self.settings['dc_options', 'is_daisy']:  # simple connection
            if self.settings['connect_type'] == 'USB':
                self.controller.ConnectUSB(self.device)
            elif self.settings['connect_type'] == 'TCP/IP':
                self.controller.ConnectTCPIPByDescription(self.device)
            elif self.settings['connect_type'] == 'RS232':
                self.controller.ConnectRS232(int(self.device[3:]), 19200)
                # in this case device is a COM port, and one should use 1 for COM1 for instance

        else:  # one use a daisy chain connection with a master device and slaves
            if self.settings['dc_options', 'is_daisy_master']:  # init the master

                if self.settings['connect_type'] == 'USB':
                    dev_ids = self.controller.OpenUSBDaisyChain(self.device)
                elif self.settings['connect_type'] == 'TCP/IP':
                    dev_ids = self.controller.OpenTCPIPDaisyChain(self.device)
                elif self.settings['connect_type'] == 'RS232':
                    dev_ids = self.controller.OpenRS232DaisyChain(int(self.device[
                                                                      3:]))  # in this case device is a COM port, and one should use 1 for COM1 for instance

                self.settings.child('dc_options', 'daisy_devices').setLimits(dev_ids)
                self.settings.child('dc_options', 'daisy_id').setValue(self.controller.dcid)

            self.controller.ConnectDaisyChainDevice(
                self.settings['dc_options', 'index_in_chain'] + 1,
                self.settings['dc_options', 'daisy_id'])

    def ini_stage(self, controller=None):
        """

        """
        self.ini_stage_init(old_controller=controller, new_controller=self.ini_device())
        self.device = devices_name[devices.index(self.settings['devices'])]
        if self.settings['multiaxes', 'multi_status'] == "Master":
            self.connect_device()

        self.settings.child('controller_id').setValue(self.controller.qIDN())
        self.axis_names = self.controller.axes

        self.set_referencing(self.axis_name)

        # check servo status:
        self.settings.child('closed_loop').setValue(
            self.controller.qSVO(self.controller.axes[0])[self.controller.axes[0]])

        try:
            self.set_axis_limits(self.get_axis_limits())
        except GCSError:
            # library not compatible with this set of commands
            pass
        try:
            # get units (experimental)
            if hasattr(self.controller, 'qSPA'):
                self.controller_units = \
                    self.controller.qSPA(self.controller.axes[0], 0x07000601)[self.controller.axes[0]][0x07000601]
        except GCSError:
            # library not compatible with this set of commands
            pass

        info = "connected on device:{} /".format(self.device) + self.controller.qIDN()
        initialized = True
        return info, initialized

    def get_axis_limits(self):
        if hasattr(self.controller, 'qTMN'):
            min_val = self.controller.qTMN(self.axis_name)[self.axis_name]
        else:
            min_val = np.NaN
        if hasattr(self.controller, 'qTMX'):
            max_val = self.controller.qTMX(self.axis_name)[self.axis_name]
        else:
            max_val = np.NaN
        return min_val, max_val

    def set_axis_limits(self, limits: Tuple[float]):
        self.settings.child('axis_infos', 'min').setValue(limits[0])
        self.settings.child('axis_infos', 'max').setValue(limits[1])

    def is_referenced(self, axe):
        """
            Return the referencement statement from the hardware device.

            ============== ========== ============================================
            **Parameters**  **Type**   **Description**

             *axe*          string     Representing a connected axe on controller
            ============== ========== ============================================

            Returns
            -------
            ???

        """
        try:
            if self.controller.HasqFRF():
                return self.controller.qFRF(axe)[axe]
            else:
                return False
        except:
            return False

    def set_referencing(self, axes):
        """
            Set the referencement statement into the hardware device.

            ============== ============== ===========================================
            **Parameters**    **Type**      **Description**
             *axes*           string list  Representing connected axes on controller
            ============== ============== ===========================================
        """
        try:
            if not isinstance(axes, list):
                axes = [axes]
            for axe in axes:
                # set referencing mode
                if isinstance(axe, str):
                    if self.is_referenced(axe):
                        if self.controller.HasRON():
                            self.controller.RON(axe, True)
                        self.controller.FRF(axe)
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',
                                           [getLineInfo() + str(e) + " / Referencing not enabled with this dll",
                                            'log']))

    def close(self):
        """
            close the current instance of PI_GCS2 instrument.
        """
        if not self.settings.child('dc_options', 'is_daisy').value():  # simple connection
            self.controller.CloseConnection()
        else:
            self.controller.CloseDaisyChain()

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.controller.StopAll()
        self.move_done()

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the PI_GCS2 instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.controller.qPOS(self.axis_name)[self.axis_name]
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """

        """
        position = self.check_bound(position)
        self.target_position = position
        position = self.set_position_with_scaling(position)
        out = self.controller.MOV(self.axis_name, position)

    def move_rel(self, position):
        """

        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position

        position = self.set_position_relative_with_scaling(position)

        if self.controller.HasMVR():
            out = self.controller.MVR(self.axis_name, position)
        else:
            self.move_abs(self.target_position)

    def move_home(self):
        """

            See Also
            --------
            DAQ_Move_PI.set_referencing, DAQ_Move_base.poll_moving
        """
        self.set_referencing(self.axis_name)
        if self.controller.HasGOH():
            self.controller.GOH(self.axis_name)
        elif self.controller.HasFRF():
            self.controller.FRF(self.axis_name)
        else:
            self.move_abs(0)


if __name__ == '__main__':
    main(__file__, init=False)

