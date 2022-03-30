from setuptools import setup

setup(
    name='SHT3x',
    version='0.0.2',
    packages=['pySHT3x'],
    install_requires=['pyFTDI==0.54.0', 'crcengine==0.3.2'],
    url='',
    license='GNU GPLv3',
    author='Holger Adams',
    author_email='mail@dm5tt.de',
    description='Package to read out the humidity/temperature of a Sensirion SHt3x sensor using I2C via pyFTDI'
)
