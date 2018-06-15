import sys, os
# ** VALUES FOR TESTING **
# <INPUTS>
CUBE_FREEFLOW                   = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input\freeflow_subarea.net')
HWY_LOADED                      = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input')
TRN_SUPPLINKS                   = None
TRN_BASE                        = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input')
TRANSIT_CAPACITY_DIR            = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input\transit_vehicles')
CHAMP_NODE_NAMES                = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input\nodes.xls')
MODEL_RUN_DIR                   = None
OVERRIDE_DIR                    = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_input\wrangler_overrides')

# <OUTPUTS>
FT_OUTPATH                      = os.path.join(os.path.dirname(__file__),r'..\unittests\test_cube_to_fasttrips_output')

# <SETTINGS>
PSUEDO_RANDOM_DEPARTURE_TIMES   = False
SORT_OUTPUTS                    = True
DEPARTURE_TIMES_OFFSET          = 0