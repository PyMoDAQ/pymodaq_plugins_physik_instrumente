"""
this plugin use an old dll from PI MMC-DLL not compatible with their new GCS-command stuff
The dll is 32 bits only so should be used with a 32bits python distribution
C-862 Mercury™-DC Motor Controller
C-863 Mercury™-DC Motor Controller
C-663 Mercury™-Step Motor Controller
C-170 Redstone PILine® Controller

"""

import sys
import os
from qtpy.QtCore import QThread

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main, ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq_plugins_physik_instrumente.utils import Config
from pymodaq_plugins_physik_instrumente.hardware.PI.mmc_wrapper import MMC_Wrapper
from pymodaq_plugins_physik_instrumente.hardware.PI.mmc_wrapper_client64 import MMCWrapperClient64

is64bit = sys.maxsize > 2**32
if is64bit:
    MMC_Wrapper = MMCWrapperClient64

logger = set_logger(get_module_name(__file__))
config = Config()
ports = MMC_Wrapper.ports


class DAQ_Move_PI_MMC(DAQ_Move_base):
    """
        Wrapper object to access the Physik Instrumente fonctionnalities, similar wrapper for all controllers.

        =============== =======================
        **Attributes**   **Type**
        *GCS_path*       string
        *gcs_device*     string
        *devices*        instance of GCSDevice
        *params*         dictionnary list
        =============== =======================

        See Also
        --------
        daq_utils.ThreadCommand
    """

    _controller_units = 'mm'  # dependent on the stage type so to be updated accordingly using self.controller_units = new_unit

    com_ports = MMC_Wrapper.aliases
    controller_addresses = []
    is_multiaxes = False
    stage_names = []
    _epsilon = 0.01

    params = [{'title': 'COM Ports:', 'name': 'com_port', 'type': 'list', 'limits': com_ports,
               'value': config('mmc', 'com_port')},
              {'title': 'Controller_address:', 'name': 'controller_address', 'type': 'list',
               'limits': controller_addresses},
              {'title': 'Stages:', 'name': 'stage', 'type': 'list', 'limits': list(MMC_Wrapper.stages.keys())},
              {'title': 'Closed loop?:', 'name': 'closed_loop', 'type': 'bool', 'value': True},
              {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
              ] + comon_parameters_fun(is_multiaxes, stage_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: MMC_Wrapper = None

    def commit_settings(self, param):
        """ bActivate any parameter changes on the PI_GCS2 hardware.

         Called after a param_tree_changed signal from DAQ_Move_main.
        """
        if param.name() == 'stage':
            self.controller.stage = param.value()

        elif param.name() == 'controller_address':
            self.controller.MMC_select(param.value())
            self.get_actuator_value()

    def enumerate_devices(self):
        """
        """
        try:
            devices = self.controller.MMC_initNetwork(3)  # up to 3 controller in a row (could be 16 at max but useless)
            self.settings.child('controller_address').setOpts(limits=devices)
            return devices
        except Exception as e:
            logger.warning(str(e))

    def ini_stage(self, controller: MMC_Wrapper = None):
        """

        """

        self.ini_stage_init(controller, MMC_Wrapper(stage=self.settings['stage'],
                                                    com_port=self.settings['com_port']))

        if self.settings['multiaxes', 'multi_status'] == "Master":
            self.controller.open()
            devices = self.enumerate_devices()
            self.controller.MMC_select(devices[0])

        self.get_actuator_value()

        info = "MMC stage initialized"
        initialized = True
        return info, initialized

    def close(self):
        """
        """
        self.controller.close()

    def stop_motion(self):
        """
            See Also
            --------
            DAQ_Move_base.move_done
        """
        self.controller.stop()
        self.move_done()

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion of the PI_GCS2 instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.controller.getPos()
        pos=self.get_position_with_scaling(pos)
        self.current_position = pos
        return pos

    def move_abs(self, value: float):
        """
        """

        value = self.check_bound(value)
        self.target_value = value

        value = self.set_position_with_scaling(value)
        self.controller.moveAbs(self.settings['controller_address'], value)

    def move_rel(self, value: float):
        """ Make the hardware relative move
        """
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        position = self.set_position_relative_with_scaling(value)

        self.controller.moveRel(self.settings['controller_address'], value)

    def move_home(self):
        """

            See Also
            --------
            DAQ_Move_PI.set_referencing, DAQ_Move_base.poll_moving
        """
        self.controller.find_home()
        moving = True
        pos = self.get_actuator_value()
        while moving:
            pos_tmp = self.get_actuator_value()
            moving = abs(pos - pos_tmp) > 0.001
            QThread.msleep(100)
            pos = pos_tmp
        self.controller.MMC_sendCommand('DH')  #to define it as home
        QThread.msleep(500)
        self.get_actuator_value()


if __name__ == '__main__':
    main(__file__, init=False)
