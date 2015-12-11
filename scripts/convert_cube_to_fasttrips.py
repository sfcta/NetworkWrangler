import copy,datetime,getopt,logging,os,shutil,sys,time

# use Wrangler from the same directory as this build script
sys.path.insert(0, os.path.join(os.path.dirname(__file__),".."))
import Wrangler
from Wrangler.Logger import WranglerLogger
from Wrangler.TransitNetwork import TransitNetwork
from Wrangler.TransitLink import TransitLink
from Wrangler.TransitLine import TransitLine
from Wrangler.HelperFunctions import *
#from Wrangler.FareParser import FareParser, fare_file_def  # should probably be moved into TransitNetwork.
from Wrangler.Fare import ODFare, XFFare, FarelinksFare

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
#FT_OUTPATH = os.path.curdir
CHAMP_NODE_NAMES = r'Y:\champ\util\nodes.xls'

SHAPES      = os.path.join(FT_OUTPATH,'shapes.txt')
TRIPS       = os.path.join(FT_OUTPATH,'trips.txt')
STOP_TIMES  = os.path.join(FT_OUTPATH,'stop_times.txt')
FARES       = os.path.join(FT_OUTPATH,'dumb_fares.txt')
    
if __name__=='__main__':
    test=False
    ask_raw_input=False
    # set up logging
    NOW = time.strftime("%Y%b%d.%H%M%S")
    FT_OUTPATH = os.path.join(FT_OUTPATH,NOW)
    if not os.path.exists(FT_OUTPATH): os.mkdir(FT_OUTPATH)
                                                                      
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
    WranglerLogger.debug("Making FarelinksFares unique")
    transit_network.makeFarelinksUnique()
    WranglerLogger.debug("Adding station names to OD Fares")
    nodeNames = getChampNodeNameDictFromFile(os.environ["CHAMP_node_names"])
    transit_network.addStationNamestoODFares(nodeNames)
    WranglerLogger.debug("creating zone ids")
    zone_to_nodes = transit_network.createZoneIDsFromFares()
    WranglerLogger.debug("adding xy to Nodes")
    transit_network.addXY(nodes_dict)
    WranglerLogger.debug("adding first departure times to all lines")
    transit_network.addFirstDeparturesToAllLines()
    WranglerLogger.debug("adding travel times to all lines")
    transit_network.addTravelTimes(highway_networks)
    WranglerLogger.debug("adding fares to lines")
    transit_network.addFaresToLines()
    transit_network.createLineLevelFares()
    WranglerLogger.debug("writing lines to shapes.txt")
    transit_network.writeFastTrips_Shapes(SHAPES)
    WranglerLogger.debug("writing stop times to stop_times.txt")
    transit_network.writeFastTrips_Trips(TRIPS,STOP_TIMES)
    WranglerLogger.debug("writing routes, stops, and fares")
    transit_network.writeFastTripsFares_dumb(FARES)
    #transit_network.writeFastTrips_RoutesStopsFares('stops.txt','routes.txt','routes_ft.txt','fare_rules.txt','fare_rules_ft.txt','fare_attributes.txt','fare_attributes_ft.txt','fare_transfer_rules.txt')

    if test:
        print "testing"

        node_to_zone_file = 'node_to_zone_file_%s.log' % NOW
        ntz = open(node_to_zone_file,'w')
        ntz.write('node,type,zone,type\n')
        for zone, nodes in zone_to_nodes.iteritems():
            for this_node in nodes:
                ntz.write('%s,%s\n' % (str(this_node),type(this_node),str(zone),type(zone)))
            overlap_list = []
            for nodes2 in zone_to_nodes.values():
                for n in nodes:
                    if n in nodes2 and nodes != nodes2 and n not in overlap_list: overlap_list.append(n)        
            WranglerLogger.debug("ZONE: %d HAS %d of %d NODES OVERLAP WITH OTHER ZONES" % (zone, len(overlap_list), len(nodes)))
            #WranglerLogger.debug("%s" % str(overlap_list))
        if ask_raw_input: raw_input("Reporting Fares Parsed (XFFares) press enter to proceed.")
        WranglerLogger.debug("Reporting Fares Parsed (XFFares) press enter to proceed.")
        for xf_fare in transit_network.xf_fares:
            if isinstance(xf_fare,XFFare): WranglerLogger.debug('%s' % str(xf_fare))
        if ask_raw_input: raw_input("Reporting Fares Parsed (ODFares) press enter to proceed.")
        WranglerLogger.debug("Reporting Fares Parsed (ODFares) press enter to proceed.")
        for od_fare in transit_network.od_fares:
            if isinstance(od_fare,ODFare): WranglerLogger.debug('%s' % str(od_fare))
        if ask_raw_input: raw_input("Reporting Fares Parsed (FarelinksFares) press enter to proceed.")
        WranglerLogger.debug("Reporting Fares Parsed (FarelinksFares) press enter to proceed.")
        for farelinks_fare in transit_network.farelinks_fares:
            if isinstance(farelinks_fare,FarelinksFare):
                WranglerLogger.debug('%s' % str(farelinks_fare))
        if ask_raw_input: raw_input("done reporting Fares.")


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
                for link_id, link_values in line.links.iteritems():
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