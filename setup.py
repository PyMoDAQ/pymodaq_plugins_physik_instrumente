from setuptools import setup, find_packages
import toml
from pymodaq_plugins_physik_instrumente import version

config = toml.load('./plugin_info.toml')
PLUGIN_NAME = f"pymodaq_plugins_{config['plugin-info']['SHORT_PLUGIN_NAME']}"

with open('README.rst') as fd:
    long_description = fd.read()

setupOpts = dict(
    name=PLUGIN_NAME,
    description=config['plugin-info']['description'],
    long_description=long_description,
    license=config['plugin-info']['license'],
    url=config['plugin-info']['package-url'],
    author=config['plugin-info']['author'],
    author_email=config['plugin-info']['author-email'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: CeCILL-B Free Software License Agreement (CECILL-B)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
    ], )


setup(
    version=version.get_version(),
    packages=find_packages(),
    package_data={'': ['*.dll']},
    include_package_data=True,
    entry_points={'pymodaq.plugins': f'default = {PLUGIN_NAME}'},
    install_requires=['toml',
        'pymodaq>=2.0',
        ]+config['plugin-install']['packages-required'],
    **setupOpts
)

