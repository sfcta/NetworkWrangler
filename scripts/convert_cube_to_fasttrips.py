import copy,datetime,getopt,logging,os,shutil,sys,time

# use Wrangler from the same directory as this build script
sys.path.insert(0, os.path.join(os.path.dirname(__file__),".."))
import Wrangler
from Wrangler.TransitNetwork import TransitNetwork
from Wrangler.TransitLink import TransitLink
from Wrangler.TransitLine import TransitLine
from Wrangler.NetworkException import NetworkException
from _static.Cube import CubeNet
sys.path.insert(0,r"Y:\champ\releases\5.0.0\lib")
import Lookups

USAGE = """

  python convert_cube_to_fasttrips.py network_specification.py

  reads in a Cube Highway and Transit Network and writes out fast-trips network files.
"""

###############################################################################
#                                                                             #
#              Define the following in an input configuration file            #
#                                                                             #
###############################################################################

TIMEPERIODS = Lookups.Lookups.TIMEPERIODS_NUM_TO_STR
CUBE_FREEFLOW = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\input_champ_network\freeflow\hwy\FREEFLOW.NET'
HWY_LOADED  = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\input_champ_network\trn'
# transit[tod].lin with dwell times, xfer_supplinks, and walk_drive_access:
TRN_LOADED  = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\input_champ_network\trn'
# .link (off-street link) and fares:
TRN_BASE    = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\input_champ_network\freeflow\trn'
FT_OUTPATH  = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\testing\fast-trips'
CHAMP_NODE_NAMES = r'Y:\champ\util\nodes.xls'

    
if __name__=='__main__':
    # set up logging
    NOW = time.strftime("%Y%b%d.%H%M%S")
    LOG_FILENAME = "convert_cube_to_fasttrips_%s.info.LOG" % NOW
    Wrangler.setupLogging(LOG_FILENAME, LOG_FILENAME.replace("info", "debug"))
    
    os.environ['CHAMP_NODE_NAMES'] = CHAMP_NODE_NAMES
    highway_networks = {}
    
    for tod in TIMEPERIODS.itervalues():
        cube_net    = os.path.join(HWY_LOADED,'LOAD%s_XFERS.NET' % tod)
        if not os.path.exists(FT_OUTPATH): os.mkdir(FT_OUTPATH)
        links_csv   = os.path.join(FT_OUTPATH,'LOAD%s_XFERS.csv' % tod)
        nodes_csv   = os.path.join(FT_OUTPATH,'LOAD%s_XFERS_nodes.csv' % tod)

        # get loaded network links w/ bus time and put it into dict highway_networks with time-of-day as the key
        # i.e. highway networks[tod] = links_dict
        (nodes_dict, links_dict) = CubeNet.import_cube_nodes_links_from_csvs(cube_net, extra_link_vars=['BUSTIME'], links_csv=links_csv, nodes_csv=nodes_csv)
        highway_networks[tod] = links_dict

    # Get transit network
    transit_network = TransitNetwork(5.0)
    transit_network.mergeDir(TRN_BASE)
    transit_network.addXY(nodes_dict)
    transit_network.addFirstDeparturesToAllLines()
    transit_network.addTravelTimes(highway_networks)

    test=True
    if test:
        print "testing"
        outfile = open(os.path.join(FT_OUTPATH,'links.csv'),'w')
        #print "NUM LINKS", len(transit_network.links)
        for link in transit_network.links:
            if isinstance(link, TransitLink):
                outfile.write('%d,%d,\"%s\"\n' % (link.Anode,link.Bnode,link.id))
            elif isinstance(link, str):
                outfile.write('%s\n' % link)
            else:
                print "Unhandled data type %s" % type(link)
                raise NetworkException("Unhandled data type %s" % type(link))
        transit_network.write(os.path.join(FT_OUTPATH,'test_champnet_out'), cubeNetFileForValidation = CUBE_FREEFLOW)
        print "Checking lines for BUSTIME"
        for line in transit_network.lines:
            if isinstance(line, TransitLine):
                for link_id, link_values in line.links.iteritems:
                    if isinstance(link_values, TransitLink):
                        if line['FREQ[1]'] != 0 and 'BUSTIME_AM' not in link_values.keys():
                            print '%s, %s: Missing BUSTIME for AM' % (line.name, link_values.id)
                        if line['FREQ[2]'] != 0 and 'BUSTIME_MD' not in link_values.keys():
                            print '%s, %s: Missing BUSTIME for MD' % (line.name, link_values.id)
                        if line['FREQ[3]'] != 0 and 'BUSTIME_PM' not in link_values.keys():
                            print '%s, %s: Missing BUSTIME for PM' % (line.name, link_values.id)
                        if line['FREQ[4]'] != 0 and 'BUSTIME_EV' not in link_values.keys():
                            print '%s, %s: Missing BUSTIME for EV' % (line.name, link_values.id)
                        if line['FREQ[5]'] != 0 and 'BUSTIME_EA' not in link_values.keys():
                            print '%s, %s: Missing BUSTIME for EA' % (line.name, link_values.id)
                    
##        for id in transit_network.line("MUN5I").links:
##            print id, transit_network.line("MUN5I")