from src.daq_driver import Daq
from qcodes.instrument_drivers.stanford_research.SR860 import SR860
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes_contrib_drivers.drivers.Oxford.IPS120 import OxfordInstruments_IPS120
from src.Model_340 import Model_340
from src.ITC503 import ITC503
from src.LM510 import LM510

# To add an instrument, import the driver then add it to our instrument
# dictionary with the name as the key, and the class as the value
LOCAL_INSTRUMENTS = {'NI DAQ': Daq,
                     'IPS120': OxfordInstruments_IPS120,
                     'ITC503': ITC503,
                     'LM510': LM510,
                     'Model 340': Model_340,
                     'SR860': SR860,
                     'SR830': SR830,
                     'Keithley2450': Keithley2450}
