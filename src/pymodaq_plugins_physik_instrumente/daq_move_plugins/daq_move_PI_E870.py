from pipython import GCSDevice

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, main, comon_parameters_fun
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.parameter.utils import iter_children


class DAQ_Move_PI_E870(DAQ_Move_base):
    """Minimalistic plugin for the PI E870 4G controller with PiezoMike actuators.

    Use the pipython package wrapper.
    It works in open loop. There is no referencing. It considers only relative moves.
    It does not consider the daisy chain option: only one controller.
    Only USB connexion is implemented.
    Tested with PI_E870_4G: we consider 4 axes.
    """
    _controller_units = 'step'
    gcs_device = GCSDevice()
    devices = gcs_device.EnumerateUSB()  # we only look for the controllers that are plugged with USB.
    is_multiaxes = True
    axes_names = [1, 2, 3, 4]
    _epsilon = 1

    params = [
        {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'values': devices},
        {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
            ] + comon_parameters_fun(is_multiaxes, axes_names, epsilon=_epsilon)

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
        """Apply the consequences of a change of value in the parameter tree.

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user.
        """
        if param.name() == "axis" and param.name() in iter_children(self.settings.child('multiaxes')):
            self.settings.child('multiaxes', 'axis').setValue(param.value())
            if self.controller.HasOSM():
                # The controller has only one PIShift channel. The demultiplexing (selection of the correct axis) is
                # done with the MOD command (see the documentation of the controller).
                self.controller.MOD(1, 2, param.value())
            else:
                self.emit_status(ThreadCommand('Update_Status', ['The controller cannot use the OSM command.']))
                pass
        else:
            pass

    def ini_device(self):
        """Load the correct dll given the chosen device.

            See Also
            --------
            DAQ_Move_base.close
        """
        try:
            self.close()
        except:
            pass
        return GCSDevice()

    def ini_stage(self, controller=None):
        """Actuator communication initialization.

        This method is triggered by the "Initialization" button of the DAQ_Move UI.

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_stage_init(old_controller=controller, new_controller=self.ini_device())
        self.device = self.settings['devices']
        if self.settings['multiaxes', 'multi_status'] == "Master":
            self.controller.ConnectUSB(self.device)

        self.settings.child('controller_id').setValue(self.controller.qIDN())

        info = "connected on device:{} /".format(self.device) + self.controller.qIDN()
        initialized = True
        return info, initialized

    def close(self):
        """Terminate the communication protocol."""
        self.controller.CloseConnection()

    def stop_motion(self):
        """Stop the actuator and emits move_done signal."""
        self.controller.StopAll()
        self.move_done()

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        This plugin considers only open-loop operation so there is no value for the actuator position. We return 0.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        self.emit_status(ThreadCommand('Update_Status', [
            'This plugin considers only open-loop operation so there is no value for the actuator position. We return'
            ' 0.']))
        return 0.

    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by value.

        This plugin considers only relative moves, thus this method is not implemented.

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """
        self.emit_status(ThreadCommand('Update_Status', [
            'This plugin considers only relative moves, the method "move_abs" is not implemented.']))
        pass

    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value defined by value.

        Parameters
        ----------
        value: (float) value in steps of the relative move.
        """
        if self.controller.HasOSM():
            # the first parameter of the OSM method is the channel value. For the E-870, there is only one channel (see
            # documentation of the controller). The action of this channel is distributed towards the correct axis by
            # the demultiplexer. The selection of the axis is done with the MOD command (see the method commit_settings
            # of this plugin).
            self.controller.OSM(1, value)
        else:
            self.emit_status(ThreadCommand('Update_Status', ['The controller cannot use the OSM command.']))
            pass

    def move_home(self):
        """Call the reference method of the controller."""
        self.emit_status(ThreadCommand('Update_Status', [
            'The plugin does not consider a reference method of the actuators. The "move_home" method is not'
            'implemented.']))
        pass


if __name__ == '__main__':
    main(__file__, init=False)
