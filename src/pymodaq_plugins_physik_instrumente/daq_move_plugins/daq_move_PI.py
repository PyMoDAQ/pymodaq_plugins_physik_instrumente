
from typing import Tuple
from pathlib import Path


from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, main, comon_parameters_fun,
    DataActuator, DataActuatorType)

from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo, is_64bits, find_keys_from_val
from pymodaq.utils.parameter.utils import iter_children


from pymodaq_plugins_physik_instrumente.utils import Config, get_devices_and_dlls
from pymodaq_plugins_physik_instrumente.hardware.pi_wrapper import PIWrapper, ConnectionEnum

config = Config()
possible_dll_names = config['dll_names']
devices, devices_name, dll_names = get_devices_and_dlls(possible_dll_names)


class DAQ_Move_PI(DAQ_Move_base):
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
    # self.axis_unit = new_unit or self.axis_units = [...] if multiple axis and multiple units

    data_actuator_type = DataActuatorType['DataActuator']
    is_multiaxes = True
    stage_names = []
    _epsilon = 0.01

    params = [
        {'title': 'Connection_type:', 'name': 'connect_type', 'type': 'list',
         'value': 'USB', 'values': ConnectionEnum.names()},
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
        ] + comon_parameters_fun(is_multiaxes, axis_names=stage_names, epsilon=_epsilon)

    def ini_attributes(self):
        self.controller: PIWrapper = None
        self.is_referencing_function = True

    def commit_settings(self, param):
        """

        """
        try:
            if param.name() == 'use_joystick':
                self.controller.use_joystick(param.value())

            elif param.name() == 'axis' and param.name() in iter_children(self.settings.child('multiaxes')):
                self.settings.child('closed_loop').setValue(self.controller.get_servo(param.value()))
                self.controller.set_referencing(self.axis_name)
                self.set_axis_limits(self.controller.get_axis_limits(self.axis_name))

            elif param.name() == 'closed_loop':
                self.controller.set_servo(self.axis_name, self.settings['closed_loop'])

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [getLineInfo() + str(e), 'log']))

    def ini_stage(self, controller=None):
        """

        """
        self.ini_stage_init(old_controller=controller, new_controller=PIWrapper())

        if self.settings['multiaxes', 'multi_status'] == "Master":
            self.controller.is_daisy = self.settings['dc_options', 'is_daisy']
            self.controller.is_daisy_master = self.settings['dc_options', 'is_daisy_master']
            self.controller.connection_type = ConnectionEnum[self.settings['connect_type']]
            self.controller.device_id = devices_name[devices.index(self.settings['devices'])]
            self.controller.connect_device()

        self.settings.child('controller_id').setValue(self.controller.identify())
        self.axis_names = self.controller.axis_names
        self.controller.set_referencing(self.axis_name)

        # check servo status:
        self.settings.child('closed_loop').setValue(self.controller.get_servo(self.axis_name))

        self.set_axis_limits(self.controller.get_axis_limits(self.axis_name))

        self.controller_units = self.controller.get_axis_units(self._controller_units)

        info = f"connected on device:{self.settings['controller_id']}"
        initialized = True
        return info, initialized

    def set_axis_limits(self, limits: Tuple[float]):
        self.settings.child('axis_infos', 'min').setValue(limits[0])
        self.settings.child('axis_infos', 'max').setValue(limits[1])

    def close(self):
        """

        """
        self.controller.close()

    def stop_motion(self):
        """

        """
        self.controller.stop()
        self.move_done()

    def get_actuator_value(self):
        """

        """
        pos = DataActuator(self.axis_name, data=self.controller.get_axis_position(self.axis_name))
        pos = self.get_position_with_scaling(pos)
        return pos

    def move_abs(self, position):
        """

        """
        position = self.check_bound(position)
        self.target_position = position
        position = self.set_position_with_scaling(position)
        out = self.controller.move_absolute(self.axis_name, position.value())

    def move_rel(self, position):
        """

        """
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position

        position = self.set_position_relative_with_scaling(position)
        self.controller.move_relative(self.axis_name, position.value())

    def move_home(self):
        """

            See Also
            --------
            DAQ_Move_PI.set_referencing, DAQ_Move_base.poll_moving
        """
        self.controller.set_referencing(self.axis_name)
        self.controller.move_home(self.axis_name)


if __name__ == '__main__':
    main(__file__, init=False)

