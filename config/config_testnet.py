# ** VALUES FOR TESTING **

TIMEPERIODS     = {0:'PM'}
CUBE_FREEFLOW   = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\freeflow_subarea.net'
HWY_LOADED      = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test'
TRN_LOADED      = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test'
TRN_BASE        = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test'
TRANSIT_CAPACITY_DIR = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\transit_vehicles'
FT_OUTPATH  = r'Q:\Model Development\SHRP2-fasttrips\Task2\output_fasttrips_networks\testnet'
CHAMP_NODE_NAMES = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\nodes.xls'
MODEL_RUN_DIR = r'X:\Projects\TIMMA\2012_Base_v2'       # for hwy and walk skims
NODEFILES = {'PM':r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\loaded_highway_data\LOADPM_nodes.csv',}
LINKFILES = {'PM':r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\loaded_highway_data\LOADPM.csv',}
OVERRIDE_DIR = r'Q:\Model Development\SHRP2-fasttrips\Task2\input_champ_network_test\wrangler_overrides'
PSUEDO_RANDOM_DEPARTURE_TIMES = False
DEPARTURE_TIMES_OFFSET = 0
sys.path.insert(0,OVERRIDE_DIR)

##import WranglerLookups as OverrideLookups
##OVERRIDE_LOOKUPS = copy.deepcopy(OverrideLookups)
##import Regexes as OverrideRegexes
##OVERRIDE_REGEXES = copy.deepcopy(OverrideRegexes)