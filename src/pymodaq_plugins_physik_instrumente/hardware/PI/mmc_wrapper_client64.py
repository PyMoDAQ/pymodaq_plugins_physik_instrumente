import sys
import os
from pathlib import Path

from msl.loadlib import Client64
from pymodaq_plugins_physik_instrumente.hardware.PI.mmc_wrapper import MMCBase

here = Path(__file__).parent


class MMCWrapperClient64(MMCBase, Client64):
    """
    Wrapper to the MMC dll from Physik Instrumente

    """

    def __init__(self, stage='M521DG', com_port='COM1', baud_rate=9600):
        MMCBase.__init__(self, stage, com_port, baud_rate)
        Client64.__init__(self, module32='mmc_wrapper',
                          append_sys_path=str(here))

    def MMC_moveA(self, axis: int=0, position: int=0):
        return self.request32('MMC_moveA', axis, position)

    def MMC_moveR(self, axis: int=0, position: int=0):
        return self.request32('MMC_moveR', axis, position)

    def MMC_getPos(self):
        return self.request32('MMC_getPos')

    def MMC_COM_open(self, port: int, baudrate: int):
        return self.request32('MMC_COM_open', port, baudrate)

    def MMC_COM_close(self):
        return self.request32('MMC_COM_close')

    def MMC_sendCommand(self, cmd: str):
        return self.request32('MMC_sendCommand', cmd)

    def MMC_getVal(self, cmd: int):
        return self.request32('MMC_getVal', cmd)

    def MMC_getStringCR(self) -> str:
        return self.request32('MMC_getStringCR')

    def MMC_select(self, axis: int=0):
        return self.request32('MMC_select', axis)

    def MMC_initNetwork(self, maxAxis: int=16):
        return self.request32('MMC_initNetwork', maxAxis)

    def MMC_globalBreak(self):
        return self.request32('MMC_globalBreak')


if __name__ == '__main__':
    mmc = MMCWrapperClient64(com_port='COM13')
    try:
        mmc.open()
        devices = mmc.MMC_initNetwork(3)
        mmc.MMC_select(devices[0])
        print(mmc.getPos())
    except Exception as e:
        print(e)
        pass
    finally:
        mmc.close()
