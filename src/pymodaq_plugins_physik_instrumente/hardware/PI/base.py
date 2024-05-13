from abc import ABC, abstractmethod
from pyvisa import ResourceManager


class MMCBase(ABC):
    """
    Wrapper to the MMC dll from Physik Instrumente

    """
    stages = {'M521DG': dict(cts_units_num=2458624, cts_units_denom=81, units="mm")}
    VISA_rm = ResourceManager()
    ress = VISA_rm.list_resources_info()
    aliases = []
    ports = []
    for key in ress.keys():
        if ress[key].alias is not None:
            if 'COM' in ress[key].alias:
                aliases.append(ress[key].alias)
                ports.append(ress[key].interface_board_number)

    baudrates = [9600, 19200]

    def __init__(self, stage='M521DG', com_port='COM1', baud_rate=9600):

        if stage not in self.stages.keys():
            raise Exception('not valid stage')
        if com_port not in self.aliases:
            raise IOError('invalid com port')
        if baud_rate not in self.baudrates:
            raise IOError('invalid baudrate')
        self.stage = stage
        self._comport = com_port
        self._baudrate = baud_rate

    @property
    def comport(self):
        return self._comport

    @comport.setter
    def comport(self,port):
        if not isinstance(port, str):
            raise TypeError("not a valid port type, should be a string: 'COM6'")
        if port not in self.ports:
            raise IOError('{} is an invalid COM port'.format(port))
        self._comport = port

    @property
    def baudrate(self):
        return self._comport

    @baudrate.setter
    def baudrate(self,rate):
        if not isinstance(rate, int):
            raise TypeError("not a valid baudrate")
        if rate not in self.baudrates:
            raise IOError('{} is an invalid baudrate'.format(rate))
        self._baudrate = rate

    def counts_to_units(self,counts):
        return counts*1/(self.stages[self.stage]['cts_units_num']/self.stages[self.stage]['cts_units_denom'])

    def units_to_counts(self,units):
        return int(units/(self.stages[self.stage]['cts_units_denom']/self.stages[self.stage]['cts_units_num']))

    def moveAbs(self,axis, units):
        """
        displacement in the selected stage units
        Parameters
        ----------
        units: (float)
        """
        self.MMC_moveA(axis, self.units_to_counts(units))

    def moveRel(self,axis, units):
        """
        displacement in the selected stage units
        Parameters
        ----------
        units: (float)
        """
        self.MMC_moveR(axis, self.units_to_counts(units))

    def getPos(self):
        return self.counts_to_units(self.MMC_getPos())

    def open(self):
        port = self.ports[self.aliases.index(self._comport)]
        self.MMC_COM_open(port,self._baudrate)

    def close(self):
        self.MMC_COM_close()

    def find_home(self):
        self.MMC_sendCommand('FE1')

    def moving(self):
        target = self.MMC_getVal(2)
        self.MMC_sendCommand('TE')
        st = self.MMC_getStringCR()
        if '-' in st:
            pos = -int(st.split('E:-')[1])
        else:
            pos = int(st.split('E:+')[1])
        return abs(target - pos) > 100

    @abstractmethod
    def MMC_moveA(self, axis: int = 0, position: int = 0):
        pass

    @abstractmethod
    def MMC_moveR(self, axis: int = 0, position: int = 0):
        pass

    @abstractmethod
    def MMC_getPos(self):
        pass

    @abstractmethod
    def MMC_COM_open(self, port: int, baudrate: int):
        pass

    @abstractmethod
    def MMC_COM_close(self):
        pass

    @abstractmethod
    def MMC_sendCommand(self, cmd: str):
        pass

    @abstractmethod
    def MMC_getVal(self, cmd: int):
        pass

    @abstractmethod
    def MMC_getStringCR(self) -> str:
        pass

    @abstractmethod
    def MMC_select(self, axis: int = 0):
        """
        Selects the specified axis (device) to enable communication with it.
        Unlike the MMC_setDevice function, here the registration status is checked, so this function requires that the
        MMC_initNetwork function have been called previously at the beginning of the program.
        Parameters
        ----------
        axis: (int) range 1 to 16 Device number of the controller that is to be selected for communication.
        """
        pass

    @abstractmethod
    def MMC_initNetwork(self, maxAxis: int = 16):
        """
        Searches all addresses, starting at address maxAxis down to 1 for Mercury™ devices connected.
        If a Mercury™ device (can be C-862, C-863, C-663 or C-170) is found, it is registered so as to allow access through the MMC_select() function.
        The function MMC_initNetwork is optional. If it is not used, devices can be activated anyway using the MMC_setDevice function.
        Parameters
        ----------
        maxAxis: (int) This parameter represents the highest device number from which the search is to run, continuing downwards.
                        If you have 3 Mercury™s connected at the addresses 0,1 and 2 (this equals the device numbers 1,2 and 3) you may call the function as MMC_initNetwork(3).
                        If you do no know what addresses the controllers are set to, call the function with maxAxis = 16 to find all devices connected. (Remember that valid device numbers range from 1 to 16.)
                        The range of maxAxis is 1 to 16
                        Because scanning each address takes about 0.5 seconds, it saves time to not start at device numbers higher than required.
        Returns
        -------
        list: list of integers corresponding to the connected devices
        """
        pass
