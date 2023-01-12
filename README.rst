pymodaq_plugins_physik_instrumente (Physik Instrumente Stages)
##############################################################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_physik_instrumente.svg
   :target: https://pypi.org/project/pymodaq_plugins_physik_instrumente/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_physik_instrumente/workflows/Upload%20Python%20Package/badge.svg
    :target: https://github.com/PyMoDAQ/pymodaq_plugins_physik_instrumente

PyMoDAQ plugin for actuators from Physik Instumente (All the ones compatible with the GCS2 commands as well as the old
32bits MMC controller...)

Authors
=======

* Sebastien J. Weber

Instruments
===========
Below is the list of instruments included in this plugin

Actuators
+++++++++

* **PI**: All stages compatible with the GCS2 library. Tested on E-816, C-863 (mercury DC/Stepper), C-663, E-545
* **PI_MMC**: old controller and stages using the 32 bits MMC dll (requires 32bit python) C-862 controller