import copy
import itertools
from .NetworkException import NetworkException
from .Node import Node, FastTripsNode
from .Logger import WranglerLogger
from .TransitLink import TransitLink
from .Fare import Fare, ODFare, XFFare, FarelinksFare, FastTripsFare
from .WranglerLookups import WranglerLookups
from .HelperFunctions import *
from .Regexes import *

print "TRANSITLINE module"
try:
    from Overrides import *
    WranglerLogger.debug("Overrides module found; importing Overrides")
except Exception as e:
    WranglerLogger.debug("No Overrides module found; skipping import of Overrides")


__all__ = ['TransitLine']

class TransitLine(object):
    """
    Transit route. Behaves like a dictionary of attributes.
    *n* is list of Node objects (see :py:class:`Node`)
    All other attributes are stored as a dictionary. e.g.::

        thisroute['MODE']='5'

    """
    def __init__(self, name=None, template=None):
        self.attr = {} # for Cube attributes that will be written to Cube *.lin files.  Not messing with it now because it's baked into the workflow.
        self.otherattr = {} # for other stuff... departure times, for instance.
        self.n = []
        self.links = {} # Links were built for supplinks, xfers, but can be extended to all links.  Including here as a way to store stop-stop travel times by time-of-day
        self.comment = None
        self.name = name
        self.board_fare = None
        self.farelinks = []
        self.od_fares = []
        self.vehicle_types = {}

        if name and name.find('"')==0:
            self.name = name[1:-1]  # Strip leading/trailing dbl-quotes

        if template:
            self._applyTemplate(template)

    def __iter__(self):
        """
        Iterator for looping through stops
        """
        self.currentStopIdx = 0
        return self

    def next(self):
        """
        Method for iterator.  Iterator usage::

            line = transitnet.line("MUN14LI")
            for stop in line:
                print stop # stop is an int
        """
        if self.currentStopIdx >= len(self.n):
            raise StopIteration

        self.currentStopIdx += 1
        return int(self.n[self.currentStopIdx-1].num)



    def setFreqs(self, freqs, timepers=None, allowDowngrades=True):
        '''Set some or all five headways (AM,MD,PM,EV,EA)
           - freqs is a list of numbers (or can be one number if only setting one headway)
             also accepts list of strings of numbers e.g. ["8","0","8","0","0"]
           - If setting fewer than 5 headways, timepers must specify the time period(s)
             for which headways are being set. Can be numbers like [1,3] or strings like ['AM','PM'].
             If setting all headways, True or 'All' may be passed.
           - allowDowngrades (optional, pass either True or False) specifies whether headways
             may be increased (i.e., whether service may be reduced) with the current action. 
        '''
        all_timepers = WranglerLookups.ALL_TIMEPERIODS
        if timepers in (None, True, 'All', 'all', 'ALL'):
            if not len(freqs)==5: raise NetworkException('Must specify all 5 frequencies or specify time periods to set')
            num_freqs = 5
            num_timepers = 5
            timepers = all_timepers[:]
        else:
            try:
                num_freqs = len(freqs)
            except TypeError:   # only single number, not list, passed
                num_freqs = 1
                freqs = [freqs]
            try:
                num_timepers = len(timepers)
            except TypeError:   # only single time period, not list, passed
                num_timepers = 1
                timepers = [timepers]
            if num_freqs <> num_timepers: raise NetworkException('Specified ' + num_freqs + ' frequencies for ' + num_timepers + ' time periods')
        for i in range(num_timepers):
            timeper = timepers[i]
            try:
                timeper_int = int(timeper)  # time period may be number (1) or string ("1")
                timepers[i] = all_timepers[timeper_int - 1]
                timeper_idx = timeper_int
            except ValueError:  # time period may be descriptive ("AM")
                timeper = timeper.upper()
                if timeper not in all_timepers: raise NetworkException('"' + timeper + '" is not a valid time period')
                timeper_idx = 1 + all_timepers.index(timeper)
            attr_set = 'FREQ[' + str(timeper_idx) + ']'
            if(allowDowngrades):
                self.attr[attr_set] = float(freqs[i])
            else:
                self.attr[attr_set] = min(float(freqs[i]),self.attr[attr_set])

    def setVehicleTypes(self, vehicles=None):
        '''
        This is a function added for fast-trips.
        vehicles is either the all-day vehicle type or a dict of time-of-day -> vehicle type
        '''
        # tod_vehicle_dict: tod_key -> vehicle type
        import re
        allday_pattern = re.compile('(ALL|all|All)[\s\-_]*(day|DAY|Day)?')

        if vehicles == None: vehicles = "unidentified"        
        if isinstance(vehicles,str):
            self.vehicle_types['allday']=vehicles
        elif isinstance(vehicles,dict):
            for key in vehicles.keys():
                m = allday_pattern.match(key)
                if m:
                    self.vehicle_types['allday'] = vehicles[key]
                else:
                    self.vehicle_types[key] = vehicles[key]
        return self.vehicle_types
                
    def getFreqs(self):
        """
        Return the frequencies for this line as a list of 5 strings representing AM,MD,PM,EV,EA.
        """
        return [self.attr['FREQ[1]'],
                self.attr['FREQ[2]'],
                self.attr['FREQ[3]'],
                self.attr['FREQ[4]'],
                self.attr['FREQ[5]']]

    def getFreq(self, timeperiod):
        """
        Returns a float version of the frequency for the given *timeperiod*, which should be one
        of ``AM``, ``MD``, ``PM``, ``EV`` or ``EA``
        """
        if timeperiod=="AM":
            return float(self.attr["FREQ[1]"])
        elif timeperiod=="MD":
            return float(self.attr["FREQ[2]"])
        elif timeperiod=="PM":
            return float(self.attr["FREQ[3]"])
        elif timeperiod=="EV":
            return float(self.attr["FREQ[4]"])
        elif timeperiod=="EA":
            return float(self.attr["FREQ[5]"])
        raise NetworkException("getFreq() received invalid timeperiod "+str(timeperiod))

    def setDistances(self, highway_networks, extra_links=None):
        pass
                
    def addFares(self, od_fares=None, xf_fares=None, farelinks_fares=None):
        '''
        This is a function added for fast-trips.
        Adds od_fares, xf_fares, and farelinks_fares that apply to this line.
        For xf_fares grabs the relevant boarding fare and saves it to self.board_fare.  There
        will be multiple due to Cube fare xfer.fare structure, so this just keeps the first one.
        Just takes the od_fares and farelinks_fares as they are.
        '''
        self.board_fare = None
        self.farelinks_fares = []
        #nodeNames = getChampNodeNameDictFromFile(os.environ["CHAMP_node_names"])
        modenum = int(self.attr['MODE'])
        nodes = self.getNodeSequenceAsInt()

        if od_fares:
            for fare in od_fares:
                if isinstance(fare,ODFare):
                    if fare.from_node in nodes and fare.to_node in nodes:
                        self.od_fares.append(fare)
                        WranglerLogger.debug("ADDED OD FARE %s TO LINE %s" % (fare,self.name))
        if xf_fares:
            for fare in xf_fares:
                if isinstance(fare,XFFare):
                    if fare.to_mode == modenum and fare.isBoardType():
                        if not self.board_fare and fare.type == 'board':
                            self.board_fare = copy.deepcopy(fare)
                            self.board_fare.setOperatorAndLineFromChamp(self.name)
                            WranglerLogger.debug("ADDED FARE %s ($%.2f) TO LINE %s for MODETYPE %s" % (self.board_fare.fare_id, float(self.board_fare.price)/100, self.name, self.getModeType()))
                        elif (type(self.board_fare) == type(fare) and self.board_fare.price == fare.price and self.board_fare.from_type == fare.from_type and self.board_fare.to_type == fare.to_type):
                            pass #WranglerLogger.debug("NOT ADDING IDENTICAL ACCESS LINK")
                        elif fare.type == 'xfer':
                            pass #WranglerLogger.debug("NOT ADDING XFER %s" % str(fare))
                        elif fare.from_type == None or fare.to_type == None:
                            pass #WranglerLogger.debug("NOT ADDING FARE WITH UNUSED TYPE %s" % str(fare))
                        elif fare.type == 'na':
                            pass #WranglerLogger.debug("NOT ADDING FARE WITH UNUSED TYPE %s" % str(fare))
                        else:
                            WranglerLogger.debug("NOT ADDING FOR UNKNOWN REASON %s" % str(fare))

        if farelinks_fares:
            for fare in farelinks_fares:
                if isinstance(fare,FarelinksFare):
                    if fare.isUnique():
                        if self.hasLink(fare.farelink.Anode, fare.farelink.Bnode) and modenum == int(fare.mode):
                            self.farelinks.append(fare)
                            WranglerLogger.debug("ADDED FARELINK %s ($%.2f) TO LINE %s" % (fare.fare_id, float(fare.price)/100, self.name))

    def hasFarelinks(self):
        '''
        This is a function added for fast-trips.
        '''
        for fare in self.farelinks:
            if isinstance(fare, FarelinksFare): return True
        return False

    def hasODFares(self):
        '''
        This is a function added for fast-trips.
        '''
        for fare in self.od_fares:
            if isinstance(fare, ODFare): return True
        return False

    def getStopList(self, style='int'):
        style = style.lower()
        stops = []
        if style not in ['int','node']: raise NetworkException("INVALID STYLE.  MUST BE 'int' OR 'node'")
        if style=='int':
            for n in self.n:
                if isinstance(n, int) or isinstance(n, str):
                    if n > 0: stops.append(int(n))
                elif isinstance(n, Node):
                    if n.isStop(): stops.append(int(n.num))
                else:
                    raise NetworkException("UNKNOWN DATA TYPE FOR NODE (%s): %s" % (type(n), str(n)))
        return stops
    
    def getNodeSequenceAsInt(self, ignoreStops=True):
        '''
        This is a function added for fast-trips.
        '''
        nodes = []
        for n in self.n:
            if isinstance(n, int) or isinstance(n, str):
                if ignoreStops:
                    nodes.append(abs(int(n)))
                else:
                    nodes.append(int(n))
            elif isinstance(n, Node):
                if ignoreStops:
                    nodes.append(abs(int(n.num)))
                else:
                    nodes.append(int(n.num))
            else:
                raise NetworkException("UNKNOWN DATA TYPE FOR NODE (%s): %s" % (type(n), str(n)))
        return nodes

    def getODFaresDict(self,od_fares=None):
        '''
        This is a function added for fast-trips.
        '''
        if not od_fares: od_fares = self.od_fares
        od_fare_dict = {}
        for fare in od_fares:
            if isinstance(fare,ODFare):
                a=fare.from_node
                b=fare.to_node
                od_fare_dict[(a,b)] = fare
        return od_fare_dict
                
    def setTravelTimes(self, highway_networks, extra_links=None):
        '''
        This is a function added for fast-trips.
        Takes a dict of links_dicts, with one links_dict for each time-of-day

            highway_networks[tod] -> tod_links_dict
            tod_links_dict[(Anode,Bnode)] -> (distance, streetname, bustime)

        Iterates over nodes in this TransitLine, adds sequential pairs to self.links
        adds travel time as an attribute for each time period.

        extra_links is an optional set of off-road links that may contain travel
        times.
        '''
        import math #, geocoder
        
        for a, b in zip(self.n[:-1],self.n[1:]):
            a_node = abs(int(a.num)) if isinstance(a, Node) else abs(int(a))
            b_node = abs(int(b.num)) if isinstance(b, Node) else abs(int(b))
            # get measured distance to check speed (because Fast-Trips checks speed this way).
            gdist = math.sqrt(math.pow((a.x-b.x),2)+math.pow((a.y-b.y),2)) / 5280 # convert measured feet-distance to miles
            
            # get node-pairs and make TransitLinks out of them
            link_id = '%s,%s' % (a_node, b_node)
            link = TransitLink()
            link.setId(link_id)
            used_method = 'none'
            for tp in WranglerLookups.ALL_TIMEPERIODS:
                try:
                    try:
                        # is it in the streets network? then get the BUSTIME (in MINUTES)
                        hwy_link_attr = highway_networks[tp][(a_node,b_node)]
                        link['BUSTIME_%s' % tp] = float(hwy_link_attr[2])
                        used_method = 'bustime'
                    except:
                        # how about the reverse link?
                        hwy_link_attr = highway_networks[tp][(b_node,a_node)]
                        link['BUSTIME_%s' % tp] = float(hwy_link_attr[2])
                        used_method = 'bustime'
                except:
                    # if it's not, then try offstreet links
                    found = False
                    xyspeed = None
                    dist = None
                    for tlink in extra_links:
                        if isinstance(tlink,TransitLink):
                            # could be smarter here and look first for (a,b) == (a,b) and then only look for (a,b) == (b,a) if the first isn't found.
                            # TIME in MINUTES, DIST in HUNDREDTHS OF MILES, SPEED in (MPH?)
                            # "time" in MINUTES, 'dist' in MILES
                            if (int(tlink.Anode) == a_node and int(tlink.Bnode) == b_node) or (int(tlink.Anode) == b_node and int(tlink.Bnode) == a_node):
                                this_link = tlink
                                upperkeys = []
                                for key in this_link.keys():
                                    upperkeys.append(key.upper())
                                timekey = this_link.keys()[upperkeys.index('TIME')] if 'TIME' in upperkeys else None
                                distkey = this_link.keys()[upperkeys.index('DIST')] if 'DIST' in upperkeys else None
                                speedkey = this_link.keys()[upperkeys.index('SPEED')] if 'SPEED' in upperkeys else None

                                if timekey:
                                    # try to get the TIME first
                                    link['BUSTIME_%s' % tp] = float(this_link[timekey])
                                    found = True
                                    used_method = 'link time'
                                else:
                                    #WranglerLogger.debug("LINE %s, LINK %s, TOD %s: OFF-STREET TRANSIT LINK HAS NO ATTRIBUTE `TIME`" % (self.name, link_id, tp))
                                    # if no TIME try to get from SPEED and DIST
                                    if speedkey: xyspeed = float(this_link[speedkey])
                                    else: WranglerLogger.debug("LINE %s, LINK %s, TOD %s: OFF-STREET TRANSIT LINK HAS NO ATTRIBUTE `SPEED`" % (self.name, link_id, tp))
                                    if distkey: dist = float(this_link[distkey]) / 100 # convert hundredths of miles to miles
                                    else: WranglerLogger.debug("LINE %s, LINK %s, TOD %s: OFF-STREET TRANSIT LINK HAS NO ATTRIBUTE `DIST`" % (self.name, link_id, tp))
                                    if speedkey and distkey:
                                        WranglerLogger.debug("LINE %s, LINK %s, TOD %s: CALCULATING TRAVEL TIME USING LINK'S DISTANCE AND SPEED" % (self.name, link_id, tp))
                                        link['BUSTIME_%s' % tp] = (60 * dist) / xyspeed
                                        found = True
                                        used_method = '60 * dist (%0.2f)/ xyspeed (%d)'
                                    else:
                                        WranglerLogger.debug(repr(this_link))
                                break
                    # no off-street link (or it's missing TIME, or SPEED + DIST), then calculate the distance between points
                    if not found:
                        WranglerLogger.debug("LINE %s, LINK %s, TOD %s: NO ON-STREET OR OFF-STREET LINK FOUND.  CALCULATING TRAVEL TIME USING MEASURED DISTANCE AND SPEED" % (self.name, link_id, tp))
##                        a_lon, a_lat = reproject_to_wgs84(a.x,a.y,EPSG='+init=EPSG:2227')
##                        b_lon, b_lat = reproject_to_wgs84(b.x,b.y,EPSG='+init=EPSG:2227')
                        if not dist:
                            dist = math.sqrt(math.pow((a.x-b.x),2)+math.pow((a.y-b.y),2)) / 5280 # convert measured feet-distance to miles
                            used_method = 'calculated distance'
                        #print a_lon, a_lat, b_lon, b_lat
##                        gdist = geocoder.distance((a_lat,a_lon),(b_lat,b_lon))
                        if not xyspeed:
                            try:
                                # if it's not a link attribute, get it from the line
                                xyspeed = int(self.attr['XYSPEED'])
                                used_method += ', xyspeed'
                            except:
                                # if no speed attribute there, then assume it's 15 mph
                                WranglerLogger.debug("LINE %s, LINK %s, TOD %s: NO XY-SPEED.  Setting XYSPEED = 15" % (self.name, link_id, tp))
                                xyspeed = 15
                                used_method += ', asserted speed 15mph'
                        link['BUSTIME_%s' % tp] = (60 * dist) / xyspeed
                        #WranglerLogger.debug('DIST %.2f, SPEED %d, TRAVELTIME %.2f' % (dist, xyspeed, link['BUSTIME_%s' % tp]))
                if link['BUSTIME_%s' % tp] == 0:
                    new_time = (60.0 * gdist) / 15.0
                    WranglerLogger.debug("LINE %s, LINK %s, TOD %s: HAS 0 BUS_TIME. SETTING BUS_TIME = %d BASED ON 15MPH (method: %s)" % (self.name, link_id, tp, new_time, used_method))
                    link['BUSTIME_%s' % tp] = new_time
                if gdist / (link['BUSTIME_%s' % tp] / 60) > 100:
                    WranglerLogger.warn('link %s has length %0.2f and travel time %0.2f for a speed of %0.2f (method: %s)' % (link_id, gdist, link['BUSTIME_%s' % tp], (60.0 * gdist) / link['BUSTIME_%s' % tp], used_method))
            self.links[(a_node,b_node)] = link
                
    def hasService(self):
        """
        Returns true if any frequency is nonzero.
        """
        if self.getFreq("AM") != 0: return True
        if self.getFreq("MD") != 0: return True
        if self.getFreq("PM") != 0: return True
        if self.getFreq("EV") != 0: return True
        if self.getFreq("EA") != 0: return True
        return False

    def setOwner(self, newOwner):
        """
        Sets the owner for the transit line
        """
        self.attr["OWNER"] = str(newOwner)

    def getModeType(self):
        """
        Returns on of the keys in MODETYPE_TO_MODES 
        (e.g. one of "Local", "BRT", "LRT", "Premium", "Ferry" or "BART")
        """
        modenum = int(self.attr['MODE'])
        for modetype,modelist in WranglerLookups.MODETYPE_TO_MODES.iteritems():
            if modenum in modelist:
                return modetype
        return None

    def isOneWay(self):
        """
        Returns a bool indicating if the line is oneway
        """
        oneway = self.attr["ONEWAY"]
        if oneway.upper() in ["N", "F"]:
            return False
        # default is true
        return True
    
    def setOneWay(self):
        """
        Turns on the oneway flag
        """
        self.attr["ONEWAY"] = "T"
        
    def hasOffstreetNodes(self):
        """
        Returns True if the line has offstreet nodes
        """
        modenum = int(self.attr['MODE'])
        return WranglerLookups.MODENUM_TO_OFFSTREET[modenum]

    def vehiclesPerPeriod(self, timeperiod):
        """
        Returns the number of vehicles (as a float) that will run for the given time period.
        E.g. for 10 minute frequencies in the AM, 3*6 = 18
        """
        freq = self.getFreq(timeperiod)
        if freq < 0.01:
            return 0.0
        
        # minutes per time period divided by frequency
        return 60.0*self.HOURS_PER_TIMEPERIOD[timeperiod]/freq
              
    def hasNode(self,nodeNumber):
        """
        Returns True if the given *nodeNumber* is a node in this line (stop or no).
        *nodeNumber* should be an integer.
        """
        for node in self.n:
            if abs(int(node.num)) == abs(nodeNumber):
                return True
        return False
                
    def hasLink(self,nodeA,nodeB):
        """
        Returns True iff *(nodeA,nodeB)* is a link in this line.
        *nodeA* and *nodeB* should be integers and this method is stop-insensitive.
        However, it does not check for *(nodeB,nodeA)* even when the line is two-way.
        """
        nodeNumPrev = -1
        for node in self.n:
            nodeNum = abs(int(node.num))
            if nodeNum == abs(nodeB) and nodeNumPrev == abs(nodeA):
                return True
            nodeNumPrev = nodeNum
        return False

    def hasSegment(self,nodeA,nodeB):
        """
        Returns True iff *nodeA* and *nodeB* appear in this line, and *nodeA* appears before *nodeB*.
        This method is stop-insensitive.  Also it does not do any special checking for two-way
        lines.
        """
        hasA=False
        for node in self.n:
            nodeNum = abs(int(node.num))
            if nodeNum == abs(nodeA):
                hasA=True
            elif nodeNum == abs(nodeB):
                if hasA: return True
                else: return False
        return False

    def hasSequence(self,list_of_node_ids):
        """
        Returns True iff the nodes indicated by list_of_node_ids appear in this line, in the exact specified order.
        This method is stop-insenstive.
        list_of_node_ids should be a list of positive integers, ordered by transit line path.
        """
        node_ids = self.listNodeIds()
        for i in range(len(node_ids)):
            if node_ids[i:i+len(list_of_node_ids)] == list_of_node_ids:
                return True
        return False

    def listNodeIds(self,ignoreStops=True):
        """
        Returns a list of integers representing the node ids that appear along this line.
        This method is stop-sensitive if called with ignoreStops=False.
        """
        node_ids = []
        for node in self.n:
            nodeNum = int(node.num)
            if(ignoreStops):
                nodeNum = abs(nodeNum)
            node_ids.append(nodeNum)
        return node_ids

        
    def numStops(self):
        """
        Counts and returns the number of stops in the line.
        """
        numStops = 0
        for node in self.n:
            if node.isStop(): numStops += 1
        return numStops

    def setNodes(self, newnodelist, coord_dict=None):
        """
        Given a list of ints representing node numbers,
        converts these to Node types uses this new list, throwing away the previous node list.
        """
        for i in range(len(newnodelist)):
            if isinstance(newnodelist[i],int): newnodelist[i] = Node(newnodelist[i],coord_dict)
        self.n = newnodelist
    
    def insertNode(self,refNodeNum,newNodeNum,stop=False,after=True):
        """
        Inserts the given *newNodeNum* into this line, as a stop if *stop* is True.
        The new node is inserted after *refNodeNum* if *after* is True, otherwise it is inserted
        before *refNodeNum*.

        *refNodeNum* and *newNodeNum* are ints.
        """
        newNode = Node(newNodeNum)
        newNode.setStop(stop)

        nodeIdx = 0
        while True:
            # out of nodes -- done
            if nodeIdx >= len(self.n): return
            
            currentNodeNum = abs(int(self.n[nodeIdx].num))
            if currentNodeNum == abs(refNodeNum):
                if after==True:
                    self.n.insert(nodeIdx+1,newNode)
                    WranglerLogger.debug("In line %s: inserted node %s after node %s" % (self.name,newNode.num,str(refNodeNum)))
                else:
                    self.n.insert(nodeIdx,newNode)
                    WranglerLogger.debug("In line %s: inserted node %s before node %s" % (self.name,newNode.num,str(refNodeNum)))
                nodeIdx += 1 # skip ahead one since we just added
            
            nodeIdx += 1
    
    def splitLink(self,nodeA,nodeB,newNodeNum,stop=False):
        """
        Checks to see if the link exists in the line (throws an exception if not)
        and then inserts the *newNodeNum* in between *nodeA* and *nodeB* (as a stop, if *stop* is True)

        *nodeA*, *nodeB* and *newNodeNum* are all ints.

        This is stop-insensitive to *nodeA* and *nodeB*.
        """
        if not self.hasLink(nodeA,nodeB):
            raise NetworkException( "Line %s Doesn't have that link - so can't split it" % (self.name))
        newNode = Node(newNodeNum)
        if stop==True: newNode.setStop(True)
        
        nodeNumPrev = -1
        for nodeIdx in range(len(self.n)):
            currentNodeNum = abs(int(self.n[nodeIdx].num))
            if currentNodeNum == abs(nodeB) and nodeNumPrev == abs(nodeA):
                self.n.insert(nodeIdx,newNode)
                WranglerLogger.debug("In line %s: inserted node %s between node %s and node %s" % (self.name,newNode.num,str(nodeA),str(nodeB)))
            nodeNumPrev = currentNodeNum
    
    def extendLine(self, oldnode, newsection, beginning=True):
        """
        Replace nodes up through **and including** *oldnode* with *newsection*.
        *newsection* can be a list of numbers; they will be converted to Nodes.

        **This is stop-sensitive!**  If *oldnode* has the wrong sign, it will throw an exception.

        If beginning, does this at the beginning; otherwise at the end.
        """
        try:
            ind = self.n.index(oldnode)
        except:
            ind = self.n.index(-oldnode)
                    
        # make the new nodes
        for i in range(len(newsection)):
            if isinstance(newsection[i],int): newsection[i] = Node(newsection[i])
        
        if beginning:
            # print self.n[:ind+1]
            self.n[:ind+1] = newsection
        else:
            self.n[ind:] = newsection
    
    def replaceSegment(self, node1, node2, newsection, preserveStopStatus=False):
        """ Replaces the section from node1 to node2 with the newsection
            Newsection can be an array of numbers; this will make nodes.
            preserveStopStatus means if node1 is a stop, make the replacement first node a stop, ditto for node2
        """
        WranglerLogger.debug("replacing segment " + str(node1) + " "+str(node2)+" with "+str(newsection)+" for "+self.name)
        try:
            ind1 = self.n.index(node1)
            stop1 = True
        except:
            ind1 = self.n.index(-node1)
            stop1 = False
            
        try:
            ind2 = self.n.index(node2)
            stop2 = True
        except:
            ind2 = self.n.index(-node2)
            stop2 = False
        
        attr1 = self.n[ind1].attr
        attr2 = self.n[ind2].attr
        
        # make the new nodes
        for i in range(len(newsection)):
            if isinstance(newsection[i],int): newsection[i] = Node(newsection[i])
        # xfer the attributes
        newsection[0].attr=attr1
        newsection[-1].attr=attr2
        
        if preserveStopStatus:
            newsection[0].setStop(stop1)
            newsection[-1].setStop(stop2)
        
        self.n[ind1:ind2+1] = newsection

    def replaceSequence(self, node_ids_to_replace, replacement_node_ids):
        """
        Replaces the sequence of nodes indicated by the positive integer list node_ids_to_replace
        with the new sequence of nodes indicated by the positive integer list replacement_node_ids
        This method removes stops from the replaced sequence; stops will have to be re-added.
        Returns true iff the sequence is successfully replaced.
        """
        if self.hasSequence(node_ids_to_replace):
            WranglerLogger.debug("replacing sequence " + str(node_ids_to_replace) + " with " + str(replacement_node_ids) + " for " + self.name)
        else:
            return False
        node_ids = self.listNodeIds()
        replaceNodesStartingAt = -1
        for i in range(len(node_ids)):
            if node_ids[i:i+len(node_ids_to_replace)] == node_ids_to_replace:
                replaceNodesStartingAt = i
                break
        if replaceNodesStartingAt < 0:
            WranglerLogger.debug("an unexpected error occurred in replaceSequence for " + self.name)
            return False

        attr1 = self.n[replaceNodesStartingAt].attr
        attr2 = self.n[replaceNodesStartingAt+len(node_ids_to_replace)].attr
        
        # make the new nodes
        replacement_nodes = list(replacement_node_ids) # copy this, we'll make them nodes
        for i in range(len(replacement_nodes)):
            if isinstance(replacement_nodes[i],int): replacement_nodes[i] = Node(replacement_nodes[i])
            # they aren't stops
            replacement_nodes[i].setStop(False)
        # xfer the attributes
        replacement_nodes[0].attr=attr1
        replacement_nodes[-1].attr=attr2

        self.n[replaceNodesStartingAt:replaceNodesStartingAt+len(node_ids_to_replace)] = replacement_nodes
        return True

    def setStop(self, nodenum, isStop=True):
        """ 
        Throws an exception if the nodenum isn't found
        """
        found = False
        for node in self.n:
            if abs(int(node.num)) == abs(nodenum):
                node.setStop(isStop)
                found = True
        if not found:
            raise NetworkException("TransitLine %s setStop called but stop %d not found" % (self.name, nodenum))

    def addStopsToSet(self, set):
        for nodeIdx in range(len(self.n)):
            if self.n[nodeIdx].isStop():
                set.add(int(self.n[nodeIdx].num))
                
    def reverse(self):
        """
        Reverses the current line -- adds a "-" to the name, and reverses the node order
        """
        # if name is 12 chars, have to drop one -- cube has a MAX of 12
        if len(self.name)>=11: self.name = self.name[:11]
        self.name = self.name + "R"
        self.n.reverse()

    def getNodeIdx(self, node):
        node_ids = self.listNodeIds()
        if isinstance(node, int):
            return node_ids.index(node)
        elif isinstance(node, Node):
            return node_ids.index(int(node.num))
        else:
            raise NetworkException("WARNING: Invalid value for node: %s" % str(node))
    
    def _applyTemplate(self, template):
        '''Copy all attributes (including nodes) from an existing transit line to this line'''
        self.attr = copy.deepcopy(template.attr)
        self.otherattr = copy.deepcopy(template.otherattr)
        self.n = copy.deepcopy(template.n)
        self.comment = template.comment
        self.board_fare = copy.deepcopy(template.board_fare)
        self.farelinks = copy.deepcopy(template.farelinks)
        self.od_fares = copy.deepcopy(template.od_fares)

    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other): return cmp(self.name,other)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = '\nLINE NAME=\"%s\",\n    ' % (self.name,)
        if self.comment: s+= self.comment

        # Line attributes
        s += ",\n    ".join(["%s=%s" % (k,v) for k,v in sorted(self.attr.items())])

        # Node list
        s += ",\n"
        prevAttr = True
        for nodeIdx in range(len(self.n)):
            s += self.n[nodeIdx].lineFileRepr(prependNEquals=prevAttr, lastNode=(nodeIdx==len(self.n)-1))
            prevAttr = len(self.n[nodeIdx].attr)>0

        return s

    def __str__(self):
        s = 'Line name \"%s\" freqs=%s' % (self.name, str(self.getFreqs()))
        return s

class FastTripsTransitLine(TransitLine):
    def __init__(self, name=None, template=None):
        TransitLine.__init__(self, name, template)
        # routes req'd
        self.route_id = None
        self.route_short_name = None
        self.route_long_name = None
        self.route_type = None

        # routes optional
        self.agency_id = None
        self.route_desc = None
        self.route_url = None
        self.route_color = None
        self.route_text_color = None

        # routes_ft req'd
        self.mode = None
        self.proof_of_payment = None

        # routes_ft optional
        self.fare_class = None

        # trips req'd
        self.service_id     = None
        self.direction_id   = None
        # info for crosswalk between SF-CHAMP and GTFS-PLUS
        self.champ_direction_id = None
        # info for crosswalk between agency published GTFS and GTFS-PLUS
        self.gtfs_vintage   = None

        self.fasttrips_fares = None

        self.setRouteInfoFromLineName()
        self.setRouteType()
        self.setMode()
        self.setProofOfPayment()
        if self.board_fare: self.setFareClass()

        self.first_departure_times = {} # tp -> psuedo-random first departure time
        self.all_departure_times = [] # just a list of departure times, used if gtfs

    # ** ATTRIBUTE SETTING / GETTING FUNCTIONS **
    def setRouteId(self, route_id=None):
        if route_id:
            self.route_id = route_id
            return self.route_id

    def setDirectionId(self, direction_id=0):
        if direction_id in (0,1):
            self.direction_id = direction_id
        else:
            raise NetworkException("direction_id must be 0 or 1.  passed %s" % str(direction_id))
        return self.direction_id
    
    def setRouteInfoFromLineName(self):
        '''
        sets GTFS-PLUS, SF-CHAMP, and other information based on the linename_pattern
        set agency_id, route_id, route_short_name, route_long_name, direction_id
        agency_id: name of the agency, human-readable
        route_id: <agency_id>_<route_number>. <agency_id> is used because the id has to be unique
        route_short_name: <operator><line>
        route_long_name: <operator><line>, could be filled in with GTFS long name
        direction_id: GTFS requires 0 or 1, but this info may not be known at the time
        champ_direction_id: store SF-CHAMP direction indication to set GTFS-PLUS direction_id later
            
        '''
        m = Regexes.linename_pattern.match(self.name)
        if not m: raise NetworkException('Failed to match linename_pattern on %s' % self.name)
        self.agency_id = WranglerLookups.OPERATOR_ID_TO_NAME[m.groupdict()['operator']]
        self.service_id = self.agency_id+'_weekday'
        self.route_id = '%s_%s' % (self.agency_id, m.groupdict()['line'])
        self.route_short_name = None #'%s%s' % (m.groupdict()['operator'], m.groupdict()['line'])
        self.route_long_name = '%s%s' % (m.groupdict()['operator'], m.groupdict()['line'])
        if m.groupdict()['direction']:
            self.champ_direction_id = m.groupdict()['direction']
        else:
            self.champ_direction_id = None
        if self.champ_direction_id in ["I","EB","SB"]:
            self.direction_id = 1
        elif self.champ_direction_id in ["O","WB","NB"]:
            self.direction_id = 0
        else:
            self.direction_id = 0

    def setRouteShortName(self, route_short_name=None):
        '''
        This will be the key that links fasttrips back to CHAMP
        '''
        if route_short_name:
            self.route_short_name = route_short_name
            return self.route_short_name
        m = Regexes.linename_pattern.match(self.name)
        self.route_short_name = '%s%s' % (m.groupdict()['operator'], m.groupdict()['line'])
        return self.route_short_name
    
    def setRouteLongName(self, route_long_name=None):
        if route_long_name:
            self.route_long_name = route_long_name
            return self.route_long_name
        m = Regexes.linename_pattern.match(self.name)
        self.route_long_name = '%s%s' % (m.groupdict()['operator'], m.groupdict()['line'])
        return self.route_long_name

    def setRouteType(self, route_type=None):
        if route_type:
            self.route_type = route_type
        else:
            self.route_type = WranglerLookups.MODENUM_TO_FTROUTETYPE[int(self.attr['MODE'])]
        return self.route_type
    
    def setAgencyId(self, agency_id=None):
        if agency_id:
            self.agency_id = agency_id
            return self.agency_id
        m = Regexes.linename_pattern.match(self.name)
        self.agency_id = m.groupdict()['operator']
        return self.agency_id

    def setMode(self, mode=None):
        if mode:
            self.mode = mode
        else:
            self.mode = WranglerLookups.MODENUM_TO_FTMODETYPE[int(self.attr['MODE'])]
        return self.mode

    def setFareClass(self, fare_class=None):
        if fare_class:
            self.fare_class = fare_class
            return self.fare_class
        if self.fasttrips_fares:
            if len(self.fasttrips_fares) == 1:
                self.fare_class = self.fasttrips_fares[0].fare_class
                return self.fare_class
        ft_fares = self.getFastTripsFares_asList()
        if len(ft_fares) == 1:
            self.fare_class = ft_fares[0].fare_class
        else:
            self.fare_class = None
        return self.fare_class

    def setProofOfPayment(self, proof_of_payment=None):
        if proof_of_payment:
            if proof_of_payment not in (0,1,True,False): raise NetworkException("Invalid proof_of_payment value %s" % str(proof_of_payment))
            self.proof_of_payment = proof_of_payment
        else:
            self.proof_of_payment = WranglerLookups.MODENUM_TO_PROOF[int(self.attr['MODE'])]

    # ** TRIP SCHEDULING FUNCTIONS **
    def setDeparturesFromHeadways(self, psuedo_random=True, offset=0):
        self.setFirstDepartures(psuedo_random, offset)
        for tp in WranglerLookups.TIME_PERIOD_TOD_ORDER:
            headway = self.getFreq(tp)
            if not headway > 0:
                continue
            departure = self.first_departure_times[tp] #self.otherattr['DEPT_%s' % tp]
            tp_end = WranglerLookups.MINUTES_PAST_MIDNIGHT[tp] + WranglerLookups.HOURS_PER_TIMEPERIOD[tp] * 60
            while departure < tp_end:
                self.all_departure_times.append(departure)
                departure += headway
            #TO-DO: if next period headway >= this period headway, schedule one more trip at current headway to avoid extra-large gap
            if len(self.all_departure_times) > 2000:
                WranglerLogger.warn('%s: has %d departure times for tp: %s' % (self.name, len(self.all_departure_times), tp))        
                #WranglerLogger.warn('%s, %s, %s, %s' % (self.all_departure_times[0], self.all_departure_times[1], self.all_departure_times[2], self.all_departure_times[3]))
                WranglerLogger.warn('%s' % str(self.all_departure_times))
                sys.exit()
        return self.all_departure_times

    def setDepartures(self, list_of_departure_times):
        for i, time in itertools.izip(range(len(list_of_departure_times)), list_of_departure_times):
            if isinstance(time, str):
                list_of_departure_times[i] = HHMMSS_to_MinutesPastMidnight(time)
        self.all_departure_times = list_of_departure_times
        
    def setFirstDepartures(self, psuedo_random=True, offset=0):
        '''
        Sets the departure time of the first run of the TransitLine for each time period.
        Optionally takes a dictionary of time periods to minutes-past-midnight.  Defaults to
        CHAMP's five time periods.
        '''                                
        if self.hasService:
            last_period_last_departure = None
            last_headway = None
            
            all_timeperiods = WranglerLookups.TIME_PERIOD_TOD_ORDER
            prev_timeperiods = copy.deepcopy(all_timeperiods)
            prev_timeperiods.insert(0,prev_timeperiods.pop())
            
            for last_tp, this_tp in zip(prev_timeperiods, all_timeperiods):
                headway = self.getFreq(this_tp)
                if headway > 0:
                    time_period_start = WranglerLookups.MINUTES_PAST_MIDNIGHT[this_tp]
                    # TO-DO: ADD IF PREV TP HAS SCHEDULED TIMES, USE THAT RATHER THAN A RANDOM NEW TIME
                    if psuedo_random:
                        self.first_departure_times[this_tp] = round(self.get_psuedo_random_departure_time(time_period_start, headway),0)
                    else:
                        self.first_departure_times[this_tp] = time_period_start + offset
        else:
            raise NetworkException("Line %s does not have service, so schedule start times cannot be set" % self.name)

    def get_psuedo_random_departure_time(self, time_period_start, headway, min_start_time = 0):
        '''
        Using a normal distribution, computes a pseudo random departure time in number of minutes based on a time window. The
        time window ranges from a default of 0 to half the headway. From this range, the mean and standard deviation are 
        calculated and then used as paramaters in the random.normalvariate function. This result is added to time_period_start, 
        and result is the departure time in number of minutes past midnight. The idea behind this methodology is that first 
        departures 1) should not all happen at the same time, 2) Indviudal routes should have a first departure time well less than 
        their headway so that their hourly frequencies are met at most stops, and 3) longer headways (less fequent service) should 
        have start times farther away from the begining of the time period compared to routes with more frequent service. Item 3
        is not guaranteed but highly probable.    
        '''
        import random
        # Assume max start time is half the headway for now:
        max_start_time = headway * .5
        start_time = max_start_time
        # Make sure start_time is < max_start_time
        while start_time >= max_start_time or start_time < 0:
            mean = (max_start_time + min_start_time)/2
            # Using 3 because 3 Standard deviatons should account for 99.7% of a population in a normal distribution. 
            sd = mean/3
            start_time = random.lognormvariate(mean, sd)
        start_time = start_time + time_period_start 
        return start_time

    # ** FARE FUNCTIONS **
    def getFastTripsFares_asList(self, zone_suffixes=False, price_conversion=1):
        '''
        This is a function added for fast-trips.
        '''
        # walk the nodes
        rules = []
        rule = None
        origin_id, destination_id = None, None
        price = self.board_fare.price
        nodes = self.getNodeSequenceAsInt(ignoreStops=False)
        od_fare_dict = None

        if self.hasODFares():
            od_fare_dict = self.getODFaresDict()
            
        if self.hasFarelinks():
            last_rule = None
            stop_a = None
            stop_b = None
            for a, idx in zip(nodes[:-1],range(len(nodes[:-1]))):
                # iterate over all origins
                if a > 0:
                    # if it's a stop, get the zone and reset the stop increment.
                    stop_a          = a
                    origin_id       = Node.node_to_zone[stop_a]
                    price           = self.board_fare.price
                    cost_increment  = 0
                    stop_b          = None
                else:
                    continue # don't care about nodes that aren't stops.
                
                for _b, b in zip(nodes[idx:-1],nodes[idx+1:]):
                    # iterate over destinations.  b is the dest, (_b,b) is the link, to check for farelinks                        
                    for fare in self.farelinks:
                        if isinstance(fare, FarelinksFare):
                            # if this link is a farelink, increment the price by the cost on the farelink.
                            if (abs(_b),abs(b)) == (int(fare.farelink.Anode), int(fare.farelink.Bnode)):
                                cost_increment += fare.price
                                price = self.board_fare.price + cost_increment
                                # WranglerLogger.debug("COST INCREMENT ON LINE %s to $%.2f between %s and %s" % (self.name, float(price)/100, str(origin_id), str(destination_id)))
                                
                    if od_fare_dict:
                        od_fare = od_fare_dict[(a,b)]
                        price += od_fare.price
                        
                    if b > 0:
                        stop_b          = b
                        destination_id  = Node.node_to_zone[stop_b]
##                        if type(destination_id) == float: raise NetworkException('destination_id = %f' % destination_id)
##                        if destination_id == '33.0': raise NetworkException('destination_id = str(%s)' % destination_id)
##                        if destination_id == 33:
##                            WranglerLogger.debug('destination_id = %f, type: %s' % (destination_id, str(type(destination_id))))
##                            if type(destination_id) != int:
##                                raw_input('y/n')
                        modenum = int(self.attr['MODE'])
                        rule = FastTripsFare(route_id=self.route_id,
                                             champ_line_name=self.name,champ_mode=modenum,
                                             price=price,origin_id=origin_id,
                                             destination_id=destination_id,
                                             zone_suffixes=zone_suffixes,
                                             price_conversion=price_conversion)
                    else:
                        continue
                    if rule == last_rule: continue
                    if rule not in rules:
                        rules.append(rule)
                    last_rule = copy.deepcopy(rule)
                    
        elif self.hasODFares():
            for fare in self.od_fares:
                if isinstance(fare, ODFare):
                    modenum = int(self.attr['MODE'])
                    rule = FastTripsFare(route_id=self.route_id,
                                         champ_line_name=self.name,champ_mode=modenum,
                                         price=self.board_fare.price + fare.price,
                                         origin_id=fare.from_name,
                                         destination_id=fare.to_name,
                                         zone_suffixes=zone_suffixes,
                                         price_conversion=price_conversion)
                    ##WranglerLogger.debug('%s' % str(rule))
                    if rule not in rules:
                        rules.append(rule)
                        
        else:
            # origin_id and destination_id only matter for lines that cross farelinks.
            origin_id       = None
            destination_id  = None
            modenum = int(self.attr['MODE'])
            rule = FastTripsFare(route_id=self.route_id,
                                 champ_line_name=self.name,champ_mode=modenum,
                                 price=self.board_fare.price,
                                 origin_id=origin_id,
                                 destination_id=destination_id,
                                 zone_suffixes=zone_suffixes,
                                 price_conversion=price_conversion)
            rules.append(rule)
                
        return rules
    
    # ** FAST-TRIP FILE WRITING FUNCTIONS **
    def writeFastTrips_Trips(self, f_trips, f_trips_ft, f_stoptimes, f_stoptimes_ft, id_generator, writeHeaders=False):
        '''
        Writes fast-trips style stop_times records for this line.
        Writes a header if writeHeaders = True
        '''
        if writeHeaders:
            f_trips.write('trip_id,route_id,service_id,shape_id,direction_id\n')
            f_trips_ft.write('trip_id,vehicle_name\n')
            f_stoptimes.write('trip_id,arrival_time,departure_time,stop_id,stop_sequence\n')
            f_stoptimes_ft.write('trip_id,stop_id\n')

        for departure in self.all_departure_times:
##            for tp, (start, stop) in WranglerLookups.TIMEPERIOD_TO_MPMRANGE.iteritems():
##                if departure >= start and departure < stop:
##                    break            
            stop_time = departure
            stop_time_hhmmss = minutesPastMidnightToHHMMSS(stop_time, sep=':')
            tp = HHMMSSToCHAMPTimePeriod(stop_time_hhmmss,sep=':')
            seq = 1
            trip_id = id_generator.next()
            f_trips.write('%d,%s,%s,%s,%d\n' % (trip_id,self.route_id,self.service_id,self.name,self.direction_id))

            if tp in self.vehicle_types.keys():
                vtype = self.vehicle_types[tp]
            else:
                vtype = self.vehicle_types['allday']
            f_trips_ft.write('%d,%s\n' % (trip_id,vtype))

            for a, b in zip(self.n[:-1], self.n[1:]):
                if not isinstance(a, Node) or not isinstance(b, Node):
                    ex = "Not all nodes in line %s are type Node" % self.name
                    WranglerLogger.debug(ex)
                    raise NetworkException(ex)
                else:
                    a_node, b_node = abs(int(a.num)), abs(int(b.num))
                    ab_link = self.links[(a_node,b_node)]
                    ##try:
                    traveltime = float(ab_link['BUSTIME_%s' % tp])
                    
                    ##except:
                    ##    WranglerLogger.warn("LINE %s, LINK %s: NO BUSTIME FOUND FOR TP %s" % (self.name, ab_link.id, tp))
                    rest_time = 0
                    if a.isStop():
                        f_stoptimes.write('%d,%s,%s,%d,%d\n' % (trip_id, stop_time_hhmmss, stop_time_hhmmss, a_node, seq))
                        f_stoptimes_ft.write('%d,%d\n' % (trip_id, a_node))
                        seq += 1

                    stop_time += traveltime
                    stop_time_hhmmss = minutesPastMidnightToHHMMSS(stop_time, sep=':')
            f_stoptimes.write('%d,%s,%s,%d,%d\n' % (trip_id, stop_time_hhmmss, stop_time_hhmmss, b_node, seq))
            f_stoptimes_ft.write('%d,%d\n' % (trip_id, b_node))

    def writeFastTrips_Shape(self, f, writeHeaders=False):
        '''
        Writes fast-trips style shapes record for this line.
            shape_id, shape_pt_lat, shape_pt_long, shape_pt_sequence, shape_dist_traveled (optional)
            <string>  <float>       <float>        <integer>          <float>
        Writes a header if writeHeaders = True
        '''
        cum_dist = 0
        track_dist = True
        seq = 1
        if writeHeaders: f.write('shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n')
        
        for a, b in zip(self.n[:-1],self.n[1:]):
            if not isinstance(a, Node) or not isinstance(b, Node):
                ex = "Not all nodes in line %s are type Node" % self.name
                WranglerLogger.debug(ex)
                raise NetworkException(ex)
            else:
                a_node, b_node = abs(int(a.num)), abs(int(b.num))
                f.write('%s,%f,%f,%d\n' % (self.name, a.stop_lat ,a.stop_lon, seq))
                seq += 1
                
        # write the last node
        f.write('%s,%f,%f,%d\n' % (self.name, self.n[-1].stop_lat, self.n[-1].stop_lon, seq))

    def addFares(self, od_fares=None, xf_fares=None, farelinks_fares=None, price_conversion=1):
        TransitLine.addFares(self, od_fares,xf_fares,farelinks_fares)
        self.fasttrips_fares = self.getFastTripsFares_asList(price_conversion=price_conversion)
    
    def asList(self, columns=None):
        data = []
        if columns is None:
            columns = ['stop_id','stop_name','stop_lat','stop_lon','zone_id']
        for col in columns:
            data.append(getattr(self,col))
        return data
            
    def asDataFrame(self, columns=None):
        import pandas as pd
        data = self.asList(columns=columns)
        df = pd.DataFrame(columns=columns,data=[data])
        return df

    def stopsAsDataFrame(self, route_cols=['route_id','route_short_name','direction_id'], stop_cols=['stop_id','stop_sequence','stop_lat','stop_lon','x','y']):
        import pandas as pd
        route_data = []
        for col in route_cols:
            route_data.append(getattr(self,col))
        all_data = []
        for n in self.n:
            if n.isStop():
                stop_data = n.asList(stop_cols)
                all_data.append(route_data+stop_data)
        df = pd.DataFrame(data=all_data, columns=route_cols+stop_cols)
        return df


    def reverse(self):
        """
        Reverses the current line -- adds a "-" to the name, and reverses the node order
        """
        # if name is 12 chars, have to drop one -- cube has a MAX of 12
        if len(self.name)>=11: self.name = self.name[:11]
        self.name = self.name + "r"
        self.setDirectionId((self.direction_id+1)%2) # set the direction to reverse
        self.n.reverse()
        
    def _applyTemplate(self, template):
        TransitLine._applyTemplate(self, template)
        for n, idx in zip(self.n, range(len(self.n))):
            if isinstance(n, Node):
                new_n = FastTripsNode(int(n.num),template=n)
                self.n[idx] = new_n