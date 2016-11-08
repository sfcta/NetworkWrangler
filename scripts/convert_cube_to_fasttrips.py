import copy,datetime,getopt,logging,os,shutil,sys,time
import getopt
from dbfpy import dbf
sys.path.insert(0, os.path.join(os.path.dirname(__file__),".."))

CUBE_FREEFLOW   = None
HWY_LOADED      = None
TRN_SUPPLINKS   = None      # transit[tod].lin with dwell times, xfer_supplinks, and walk_drive_access:
TRN_BASE        = None      # .link (off-street link) and fares:
TRANSIT_CAPACITY_DIR = None
FT_OUTPATH      = None
CHAMP_NODE_NAMES = None
MODEL_RUN_DIR   = None      # for hwy and walk skims
OVERRIDE_DIR    = None
PSUEDO_RANDOM_DEPARTURE_TIMES = None
CHAMP_DIR       = None
DEPARTURE_TIMES_OFFSET = None
SORT_OUTPUTS    = False
GTFS_SETTINGS   = None
CROSSWALK       = None

USAGE = """

  python convert_cube_to_fasttrips.py -s False -h False -f False -v False -t test config_file.py

    -s False -> don't do supplinks
    -h False -> don't do anything using highway networks (i.e. node xy coordinates, link-based travel times,
                park and rides
    -f False -> don't do fares
    -v False -> don't do vehicles
    -t test  -> run it in test mode, which produces some extra summary info at the end.  This is maybe
                obsolete now.
  reads in a Cube Highway and Transit Network and writes out fast-trips network files.
"""

###############################################################################
#                                                                             #
#              Define the following in an input configuration file            #
#                                                                             #
###############################################################################

if __name__=='__main__':
    opts, args = getopt.getopt(sys.argv[1:],"s:h:f:v:t:")
    if len(args) != 1:
        print USAGE
        sys.exit(2)
    config_file     = args[0]
    do_supplinks    = True
    do_highways     = True
    do_fares        = True
    do_vehicles     = True
    test            = False
    ask_raw_input   = False
    
    for o, a in opts:
        if o == '-s' and a == 'False':
            do_supplinks = False
        if o == '-h' and a == 'False':
            do_highways = False
        if o == '-f' and a == 'False':
            do_fares = False
        if o == '-v' and a == 'False':
            do_vehicles = False
        if o == '-t' and a == 'test':
            test = True

    execfile(config_file)

    if CHAMP_DIR:
        sys.path.append(CHAMP_DIR)
    if OVERRIDE_DIR:
        sys.path.insert(0,OVERRIDE_DIR)

    import Wrangler
    from Wrangler.Logger import WranglerLogger

    # set up logging    
    NOW = time.strftime("%Y%b%d.%H%M%S")
    FT_OUTPATH = os.path.join(FT_OUTPATH,NOW)    
    if not os.path.exists(FT_OUTPATH): os.mkdir(FT_OUTPATH)                         
    LOG_FILENAME = os.path.join(FT_OUTPATH,"convert_cube_to_fasttrips_%s.info.LOG" % NOW)
    Wrangler.setupLogging(LOG_FILENAME, LOG_FILENAME.replace("info", "debug"))

    from Wrangler.TransitNetwork import TransitNetwork
    from Wrangler.TransitLink import TransitLink
    from Wrangler.TransitLine import TransitLine
    from Wrangler.HelperFunctions import *
    from Wrangler.Fare import ODFare, XFFare, FarelinksFare
    from Wrangler.Regexes import *
    from Wrangler.WranglerLookups import *
    from Wrangler.NetworkException import NetworkException
    from _static.Cube import CubeNet
    try:
        from SkimUtil import Skim, HighwaySkim, WalkSkim
    except:
        WranglerLogger.debug("Cannot find SkimUtil. NetworkWrangler will not be able to access skim attributes for access links. Continue anyway? (y/n)")
        response = raw_input()
        WranglerLogger.debug('Response: %s' % response)
        if response.lower() not in ['y','yes','affirmative']:
            WranglerLogger.debug('Quitting.')
            sys.exit(2)
        WranglerLogger.debug('Continuing...')

    os.environ['CHAMP_NODE_NAMES'] = CHAMP_NODE_NAMES
    
    try:
        from Overrides import *
        WranglerLogger.debug("Overrides module found; importing Overrides")
    except Exception as e:
        WranglerLogger.debug("No Overrides module found; skipping import of Overrides")

    # Get transit network
    WranglerLogger.debug("Creating transit network.")
    transit_network = TransitNetwork(5.0)
    transit_network.mergeDir(TRN_BASE)
    transit_network.convertTransitLinesToFastTripsTransitLines()

    if do_vehicles:
        WranglerLogger.debug("Getting transit capacity.")
        Wrangler.TransitNetwork.capacity = Wrangler.TransitCapacity(directory=TRANSIT_CAPACITY_DIR)
        # build dict of vehicle types
        for line in transit_network.lines:
            ##transit_freqs_by_line[line.name] = line.getFreqs()
            if isinstance(line, str):
                continue
            vehicles = {}
            for tp in WranglerLookups.ALL_TIMEPERIODS:
                vehicles[tp] = Wrangler.TransitNetwork.capacity.getSystemAndVehicleType(line.name, tp)[1]
            line.setVehicleTypes(vehicles)
            
    if do_highways:
        WranglerLogger.debug("Reading highway networks to get node coordinates and link attributes")
        highway_networks = {}

        for tod in WranglerLookups.ALL_TIMEPERIODS:
            cube_net    = os.path.join(HWY_LOADED,'LOAD%s_XFERS.NET' % tod)
            if not os.path.exists(os.path.join(FT_OUTPATH,'loaded_highway_data')): os.mkdir(os.path.join(FT_OUTPATH,'loaded_highway_data'))
            links_csv   = os.path.join(FT_OUTPATH,'loaded_highway_data','LOAD%s_XFERS.csv' % tod)
            nodes_csv   = os.path.join(FT_OUTPATH,'loaded_highway_data','LOAD%s_XFERS_nodes.csv' % tod)

            # get loaded network links w/ bus time and put it into dict highway_networks with time-of-day as the key
            # i.e. highway networks[tod] = links_dict
            (nodes_dict, links_dict) = CubeNet.import_cube_nodes_links_from_csvs(cube_net, extra_link_vars=['BUSTIME'], links_csv=links_csv, nodes_csv=nodes_csv)
            highway_networks[tod] = links_dict
            
        WranglerLogger.debug("adding xy to Nodes")
        transit_network.addXY(nodes_dict)
        WranglerLogger.debug("adding travel times to all lines")
        transit_network.addTravelTimes(highway_networks)

    if do_fares:
        WranglerLogger.debug("Making FarelinksFares unique")
        transit_network.makeFarelinksUnique()
        WranglerLogger.debug("creating zone ids")
        transit_network.createFarelinksZones()
        nodeNames = getChampNodeNameDictFromFile(os.environ["CHAMP_node_names"])
        WranglerLogger.debug("Adding station names to OD Fares")
        transit_network.addStationNamestoODFares(nodeNames)
        WranglerLogger.debug("adding fares to lines")
        transit_network.addFaresToLines()
        transit_network.createFastTrips_Fares(price_conversion=0.01)
    transit_network.createFastTrips_Nodes()
    
    if do_supplinks and not TRN_SUPPLINKS:
        do_supplinks = False
        WranglerLogger.warn("Supplinks directory not defined (TRN_SUPPLINKS).  Skipping access and transfer links.")
    if do_supplinks:
        #a lot of this stuff requires a model run directory with skims, and SkimUtils, so need to do some checks to make sure these are avaiable.
        WranglerLogger.debug("Merging supplinks.")
        transit_network.mergeSupplinks(TRN_SUPPLINKS)
        WranglerLogger.debug("\tsetting up walk skims for access links.")

        # try to get walk skims
        try:
            walkskim = WalkSkim(file_dir = MODEL_RUN_DIR)
        except:
            WranglerLogger.debug("WalkSkim module or MODEL_RUN_DIR not available.  Skipping WalkSkims.  Some walk access link attributes will be blank.")
            walkskim = None

        # try to get node to taz correspondence
        try:
            nodeToTazFile = os.path.join(MODEL_RUN_DIR,"nodesToTaz.dbf")
            nodesdbf      = dbf.Dbf(nodeToTazFile, readOnly=True, new=False)
            nodeToTaz     = {}
            maxTAZ        = 0
            for rec in nodesdbf:
                nodeToTaz[rec["N"]] = rec["TAZ"]
                maxTAZ = max(maxTAZ, rec["TAZ"])
            nodesdbf.close()
        except:
            WranglerLogger.debug("nodesToTaz.dbf not found.  MODEL_RUN_DIR may be missing or unavailable.")
            nodeToTaz = None
            maxTAZ = None

        WranglerLogger.debug("\tsetting up highway skims for access links.")
        hwyskims = {}
        
        ##try:
        for tpnum,tpstr in Skim.TIMEPERIOD_NUM_TO_STR.items():
            hwyskims[tpnum] = HighwaySkim(file_dir=MODEL_RUN_DIR, timeperiod=tpstr)
##        except:
##            WranglerLogger.debug("HighwaySkim module or MODEL_RUN_DIR not available.  Skipping HighwaySkims.  Some walk access link attributes will be blank.")
##            hwyskims = None
            
        pnrTAZtoNode = {}

        try:
            pnrZonesFile = os.path.join(MODEL_RUN_DIR,"PNR_ZONES.dbf")
            indbf = dbf.Dbf(os.path.join(MODEL_RUN_DIR,"PNR_ZONES.dbf"), readOnly=True, new=False)
            for rec in indbf:
                pnrTAZtoNode[rec["PNRTAZ"]] = 'lot_' + str(rec["PNRNODE"]).strip()
            indbf.close()
            pnrNodeToTAZ = dict((v,k) for k,v in pnrTAZtoNode.iteritems())
            #maxRealTAZ = min(pnrTAZtoNode.keys())-1
        except:
            WranglerLogger.debug("PNR_ZONES.dbf not found.  MODEL_RUN_DIR may be missing or unavailable.")
            pnrNodeToTAZ = None
        
        WranglerLogger.debug("\tconverting supplinks to fasttrips format.")
        transit_network.getFastTripsSupplinks(walkskim,nodeToTaz,maxTAZ,hwyskims,pnrNodeToTAZ)
        WranglerLogger.debug("add pnrs")
        transit_network.createFastTrips_PNRs(nodes_dict)
        
    WranglerLogger.debug("adding departure times to all lines")
    if not GTFS_SETTINGS:
        transit_network.addDeparturesFromHeadways(psuedo_random=PSUEDO_RANDOM_DEPARTURE_TIMES, offset=DEPARTURE_TIMES_OFFSET)
    else:
        for agency, settings in GTFS_SETTINGS.iteritems():
            # relax criteria on low-res network
            WranglerLogger.debug('matching gtfs for %s using %s AND CROSSWALK %s ENCODING %s' % (agency, settings['path'], settings['crosswalk'], settings['gtfs_encoding']))
            #if agency == 'sf_muni': continue
            transit_network.matchLinesToGTFS2(gtfs_agency=agency,
                                              gtfs_path=settings['path'],
                                              gtfs_encoding=settings['gtfs_encoding'],
                                              stop_count_diff_threshold=settings['stop_count_diff_threshold'])
            transit_network.addDeparturesFromGTFS(agency=agency, gtfs_path=settings['path'], gtfs_encoding=settings['gtfs_encoding'])
    transit_network.gtfs_crosswalk.to_csv('gtfs_route_crosswalk.csv')
    transit_network.gtfs_node_crosswalk.to_csv('gtfs_node_crosswalk.csv')
    WranglerLogger.debug("writing agencies")
    transit_network.writeFastTrips_Agencies(path=FT_OUTPATH)
    WranglerLogger.debug("writing calendar")
    transit_network.writeFastTrips_Calendar(path=FT_OUTPATH)
    if do_vehicles:
        WranglerLogger.debug("writing vehicles")
        transit_network.writeFastTrips_Vehicles(path=FT_OUTPATH)
    WranglerLogger.debug("writing lines")
    transit_network.writeFastTrips_Shapes(path=FT_OUTPATH)
    WranglerLogger.debug("writing routes")
    try:
        transit_network.writeFastTrips_Routes(path=FT_OUTPATH)
    except Exception as e:
        WranglerLogger.debug('failed writing routes: %s' % str(e))
    transit_network.writeFastTrips_toCHAMP(path=FT_OUTPATH) # get rid of this later; it's duplicate.
    WranglerLogger.debug("writing stop times")
    transit_network.writeFastTrips_Trips(path=FT_OUTPATH)
    if do_fares:
        try:
            WranglerLogger.debug("writing fares")
            transit_network.writeFastTrips_Fares(path=FT_OUTPATH, sortFareRules=SORT_OUTPUTS)
        except Exception as e:
            WranglerLogger.debug('failed writing fairs: %s' % str(e))
    WranglerLogger.debug("writing stops")
    transit_network.writeFastTrips_Stops(path=FT_OUTPATH)
    if do_highways:
        WranglerLogger.debug("writing pnrs")
        transit_network.writeFastTrips_PNRs(path=FT_OUTPATH)
    WranglerLogger.debug("Writing supplinks")
    transit_network.writeFastTrips_Access(path=FT_OUTPATH)

    print "writing FastTrips to CHAMP route name crosswalk"
    transit_network.writeFastTrips_toCHAMP(path=FT_OUTPATH)
    
    print "copying to csv for readability"
    os.mkdir(os.path.join(FT_OUTPATH,'csvs'))
    for file in ['agency.txt','calendar.txt','drive_access_ft.txt','drive_access_points_ft.txt','fare_attributes.txt','fare_attributes_ft.txt','fare_rules.txt',
                 'fare_rules_ft.txt','fare_transfer_rules_ft.txt','routes.txt','routes_ft.txt','shapes.txt','stop_times.txt','stop_times_ft.txt','stops.txt',
                 'stops_ft.txt','transfers.txt','transfers_ft.txt','trips.txt','trips_ft.txt','vehicles_ft.txt','walk_access_ft.txt']:
        shutil.copyfile(os.path.join(FT_OUTPATH,file),os.path.join(FT_OUTPATH,'csvs',file.replace('.txt','.csv')))
        
    if test:
        print "testing"

        node_to_zone_file = 'node_to_zone_file_%s.log' % NOW
        ntz = open(node_to_zone_file,'w')
        ntz.write('node,type,zone,type\n')
        for zone, nodes in transit_network.zone_to_nodes.iteritems():
            for this_node in nodes:
                ntz.write('%s,%s,%s,%s\n' % (str(this_node),type(this_node),str(zone),type(zone)))
            overlap_list = []
            for nodes2 in transit_network.zone_to_nodes.values():
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
        transit_network.writeFastTripsFares_dumb(path=FT_OUTPATH)
        
##        for id in transit_network.line("MUN5I").links:
##            print id, transit_network.line("MUN5I")