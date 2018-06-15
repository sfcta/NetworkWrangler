import copy
from .NetworkException import NetworkException
from .WranglerLookups import WranglerLookups
from .Logger import WranglerLogger
try:
    from SkimUtil import Skim, HighwaySkim, WalkSkim
except:
    WranglerLogger.debug("Could not find SkimUtil.  Some Supplink features will be unavailable")

__all__ = ['Supplink']

class Supplink(dict):
    """ PNR Support Link.
       'node' property is the node-pair for this link (e.g. 24133-34133)
       'comment' is any end-of-line comment for this link including the leading semicolon
        All other attributes are stored in a dictionary (e.g. thislink['MODE']='1,2')
    """
    MODES = {1:"WALK_ACCESS",
             2:"WALK_EGRESS",
             3:"DRIVE_ACCESS",
             4:"DRIVE_EGRESS",
             5:"TRANSIT_TRANSFER",
             6:"DRIVE_FUNNEL",
             7:"WALK_FUNNEL"}
    MODES_INV = dict((v,k) for k,v in MODES.iteritems())
    
    def __init__(self, template=None):
        dict.__init__(self)
        self.id=''  # string, e.g. "1-7719"
        self.comment=None
        
        # components of ID, ints
        self.Anode = None
        self.Bnode = None
        self.mode  = None
        self.support_flag = False
        self.zone_id = None
        if template:
            self._applyTemplate(template)

    def __repr__(self):
        s = "SUPPLINK N=%5s-%5s " % (self.Anode,self.Bnode)

        # Deal w/all link attributes
        fields = []
        for k in sorted(self.keys()):
            fields.append('%s=%s' % (k,self[k]))

        s += " ".join(fields)
        if self.comment:
            s = "%-80s %s" % (s, self.comment)

        return s

    def _applyTemplate(self, template):
        self.id = copy.deepcopy(template.id)
        self.comment = copy.deepcopy(template.comment)
        self.Anode = copy.deepcopy(template.Anode)
        self.Bnode = copy.deepcopy(template.Bnode)
        self.mode  = copy.deepcopy(template.mode)
        self.zone_id = copy.deepcopy(template.zone_id)
        for key in template.keys():
            self[key] = copy.deepcopy(template[key])
            
    def setId(self, id):
        self.id = id
        
        nodeList=self.id.split('-')
        self.Anode = int(nodeList[0])
        self.Bnode = int(nodeList[1])

    def setZone(self, zone):
        self.zone_id = int(zone)
        
    def setSupportFlag(self, flag=True):
        self.support_flag = flag
        
    def setMode(self, newmode=None):
        """
        If newmode is passed, then uses that.
        Otherwise, figure out the mode from the text in the dictionary.
        """
        if newmode==None and self.mode: return
        
        # find it in my dictionary
        for k,v in self.items():
            if k.lower() == "mode":
                if newmode:
                    self.mode = newmode
                    self[k] = str(self.mode)
                else:
                    self.mode = int(v)
        
        # it wasn't in the dictionary
        if newmode and not self.mode:
            self.mode = newmode
            self["MODE"] = str(self.mode)
        
        if not self.mode:
            raise NetworkException("Supplink mode not set: " + str(self))

    def isWalkAccess(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="WALK_ACCESS")
    
    def isWalkEgress(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="WALK_EGRESS")
    
    def isDriveAccess(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="DRIVE_ACCESS")

    def isDriveEgress(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="DRIVE_EGRESS")

    def isTransitTransfer(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="TRANSIT_TRANSFER")
    
    def isWalkFunnel(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="WALK_FUNNEL")

    def isDriveFunnel(self):
        self.setMode()
        return (Supplink.MODES[self.mode]=="DRIVE_FUNNEL")
    
    def isOneWay(self):
        for k,v in self.items():
            if k.upper() == "ONEWAY": return v.upper() in ["Y", "YES", "1", "T", "TRUE"]
        # Cube says default is False
        return False
    
    def reverse(self):
        # not one-way; nothing to do
        if not self.isOneWay(): return
        
        temp = self.Anode
        self.Anode = self.Bnode
        self.Bnode = temp
        
        self.id = "%d-%d" % (self.Anode, self.Bnode)
        if   self.isWalkAccess(): self.setMode(Supplink.MODES_INV["WALK_EGRESS"])
        elif self.isWalkEgress(): self.setMode(Supplink.MODES_INV["WALK_ACCESS"])
        elif self.isDriveAccess(): self.setMode(Supplink.MODES_INV["DRIVE_EGRESS"])
        elif self.isDriveEgress(): self.setMode(Supplink.MODES_INV["DRIVE_ACCESS"])

    def asList(self, columns=None):
        data = []
        if not isinstance(columns, list): raise NetworkException("Supplink.asList() requires columns argument as a list")
        for col in columns:
            data.append(getattr(self,col))
        return data
        
    def asDataFrame(self, columns=None):
        import pandas as pd
        if columns is None: columns = ['Anode','Bnode','mode']
        data = self.asList(columns)
        df = pd.DataFrame(columns=columns,data=[data])
        return df
    
        
class FastTripsWalkSupplink(Supplink):
    def __init__(self, walkskims=None, nodeToTaz=None, maxTaz=None, template=None):
        Supplink.__init__(self,template)
        # walk_access req'd
        self.setDirection()
        if self.isWalkEgress():
            self.taz = self.Bnode
            self.stop_id = self.Anode
        elif self.isWalkAccess():
            self.taz = self.Anode
            self.stop_id = self.Bnode
        elif self.isTransitTransfer():
            pass
        elif self.isDriveFunnel() or self.isWalkFunnel():
            self.setSupportFlag(True)
            #WranglerLogger.warn("invalid supplink type %s for supplink (%d, %d)" % (self.mode, self.Anode, self.Bnode))
        self.dist = float(self['DIST'])*0.01 if 'DIST' in self.keys() else None
        
        # walk_access optional
        if walkskims and nodeToTaz and maxTaz:
            self.setAttributes(walkskims,nodeToTaz,maxTaz)
        else:            
            self.elevation_gain = None
            self.population_density = None
            self.retail_density = None
            self.employment_density = None
            self.auto_capacity = None
            self.indirectness = None
            # these enable reversing the supplink without having to pass walkskims again.  
            # Reverse all the attributes in case the reverse path is a different route.
            self._reverse_dist = self.dist
            self._reverse_elevation_gain = None
            self._reverse_population_density = None
            self._reverse_retail_density = None
            self._reverse_auto_capacity = None
            self._reverse_indirectness = None
            self._reverse_direction = 'egress' if self.direction == 'access' else 'access'
        
    def asDataFrame(self, columns=None):
        if columns is None:
            columns = ['taz','stop_id','direction','dist','elevation_gain','population_density',
                       'employment_density','retail_density','auto_capacity','indirectness']
        result = Supplink.asDataFrame(self, columns)
        return result

    def asList(self, columns=None):
        if columns is None:
            columns = ['taz','stop_id','direction','dist','elevation_gain','population_density',
                       'employment_density','retail_density','auto_capacity','indirectness']
        result = Supplink.asList(self, columns)
        return result

    def setDirection(self):
        if self.isWalkAccess():
            self.direction = 'access' # 'access' or 'egress'
        elif self.isWalkEgress():
            self.direction = 'egress'
        else:
            self.direction = None
            
    def setAttributes(self, walkskims, nodeToTaz, maxTaz):
        if isinstance(walkskims, str):
            walkskims = WalkSkim(file_dir = walkskims)
        elif not isinstance(walkskims, WalkSkim):
            raise NetworkException("Unknown skim type %s" % str(walkskims))

        if self.Anode <= maxTaz:
            oTaz = self.Anode
        elif self.Anode in nodeToTaz:
            oTaz = nodeToTaz[self.Anode]
        else:
            #print nodeToTaz
            WranglerLogger.warn("Counldn't find TAZ for node %d in (%d, %d)" % (self.Anode,self.Anode,self.Bnode))
            return
            #raise NetworkException("Counldn't find TAZ for node %d in (%d, %d)" % (self.Anode,self.Anode,self.Bnode))

        if self.Bnode <= maxTaz:
            dTaz = self.Bnode
        elif self.Bnode in nodeToTaz:
            dTaz = nodeToTaz[self.Bnode]
        else:
            WranglerLogger.warn("Counldn't find TAZ for node %d in (%d, %d)" % (self.Bnode,self.Anode,self.Bnode))
            return
            #raise NetworkException("Counldn't find TAZ for node %d in (%d, %d)" % (self.Bnode,self.Anode,self.Bnode))
        
        self.dist               = walkskims.getWalkSkimAttribute(oTaz,dTaz,"DISTANCE") if self.dist == None else self.dist  # link sum (miles).  Keep the original distance if it's available.
        #self.dist = max(self.dist, 0.01)
        self.population_density = walkskims.getWalkSkimAttribute(oTaz,dTaz,"AVGPOPDEN")  # average pop/acre
        self.employment_density = walkskims.getWalkSkimAttribute(oTaz,dTaz,"AVGEMPDEN")  # average employment/acre
        self.retail_density     = None #walkSkim.getWalkSkimAttribute(oTaz,dTaz,"AVGRETDEN")  # average retail/acre
        self.auto_capacity      = walkskims.getWalkSkimAttribute(oTaz,dTaz,"AVGCAP")     # average road capacity (vph)
        self.elevation_gain     = walkskims.getWalkSkimAttribute(oTaz,dTaz,"ABS_RISE")   # link sum when rise > 0 (feet)
        self.indirectness       = max(walkskims.getWalkSkimAttribute(oTaz,dTaz,"INDIRECTNESS"),1) # distance divided by rock dove distance, force to be 1 if the skim distance is less than straight-line
        
        self._reverse_dist               = walkskims.getWalkSkimAttribute(dTaz,oTaz,"DISTANCE") if self.dist == None else self.dist  # link sum (miles).  Keep the original distance if it's available.
        #self.dist = max(self.dist, 0.01)
        self._reverse_population_density = walkskims.getWalkSkimAttribute(dTaz,oTaz,"AVGPOPDEN")  # average pop/acre
        self._reverse_employment_density = walkskims.getWalkSkimAttribute(dTaz,oTaz,"AVGEMPDEN")  # average employment/acre
        self._reverse_retail_density     = None #walkSkim.getWalkSkimAttribute(oTaz,dTaz,"AVGRETDEN")  # average retail/acre
        self._reverse_auto_capacity      = walkskims.getWalkSkimAttribute(dTaz,oTaz,"AVGCAP")     # average road capacity (vph)
        self._reverse_elevation_gain     = walkskims.getWalkSkimAttribute(dTaz,oTaz,"ABS_RISE")   # link sum when rise > 0 (feet)
        self._reverse_indirectness       = max(walkskims.getWalkSkimAttribute(dTaz,oTaz,"INDIRECTNESS"),1) # distance divided by rock dove distance, force to be 1 if the skim distance is less than straight-line
        self._reverse_direction = 'egress' if self.direction == 'access' else 'access'
        
    def reverse(self):
        Supplink.reverse(self)
        dist = self.dist
        population_density                  = self.population_density
        employment_density                  = self.employment_density
        retail_density                      = self.retail_density
        auto_capacity                       = self.auto_capacity
        elevation_gain                      = self.elevation_gain
        indirectness                        = self.indirectness
        direction                           = self.direction
        
        self.dist                           = self._reverse_dist
        self.population_density             = self._reverse_population_density
        self.employment_density             = self._reverse_employment_density
        self.retail_density                 = self._reverse_retail_density
        self.auto_capacity                  = self._reverse_auto_capacity
        self.elevation_gain                 = self._reverse_elevation_gain
        self.indirectness                   = self._reverse_indirectness
        self.direction                      = self._reverse_direction
        
        self._reverse_dist                  = dist
        self._reverse_population_density    = population_density
        self._reverse_employment_density    = employment_density
        self._reverse_retail_density        = retail_density
        self._reverse_auto_capacity         = auto_capacity
        self._reverse_elevation_gain        = elevation_gain
        self._reverse_indirectness          = indirectness
        self._reverse_direction             = direction
    
class FastTripsDriveSupplink(Supplink):
    def __init__(self, hwyskims=None, pnrNodeToTaz=None, nodeToTaz=None, tp=None, template=None):
        Supplink.__init__(self,template)
        # drive_access req'd
        if self.isDriveAccess():
            self.taz = self.Anode
            self.lot_id = 'lot_' + str(self.Bnode) 
        elif self.isDriveEgress():
            self.taz = self.Bnode
            self.lot_id = 'lot_' + str(self.Anode)
        self.setDirection()
        self.dist = None        # float, miles
        self.cost = None        # integer, cents
        self.travel_time = None # float, minutes
        self.start_time = None  # hhmmss or blank
        self.end_time = None    # hhmmss or blank
        #self.zone_id = None

        if hwyskims and tp and pnrNodeToTaz:
            self.getSupplinkAttributes(hwyskims, pnrNodeToTaz, tp, nodeToTaz)
        elif tp:
            self.setStartTimeEndTimeFromTimePeriod(tp)
        
    def setDirection(self):
        if self.isDriveAccess():
            self.direction = 'access' # 'access' or 'egress'
        elif self.isDriveEgress():
            self.direction = 'egress'
        else:
            self.direction = None

    def setStartTimeEndTimeFromTimePeriod(self, tp):
        '''
        Uses the timeperiods from WranglerLookups to set time range in HHMMSS format
        '''
        if tp not in WranglerLookups.TIMEPERIOD_TO_TIMERANGE.keys():
            raise NetworkException("Invalid time period %s" % tp)
        self.start_time = WranglerLookups.TIMEPERIOD_TO_TIMERANGE[tp][0]
        self.end_time = WranglerLookups.TIMEPERIOD_TO_TIMERANGE[tp][1]

    def getSupplinkAttributes(self, hwyskims, pnrNodeToTaz, tp, nodeToTaz):
        if isinstance(tp, str):
            TIMEPERIOD_STR_TO_NUM = {}
            for k, v in Skim.TIMEPERIOD_NUM_TO_STR.iteritems():
                TIMEPERIOD_STR_TO_NUM[v] = k
            tpnum = TIMEPERIOD_STR_TO_NUM[tp]
            tpstr = tp
        elif isinstance(tp, int):
            tpnum = tp
            tpstr = Skim.TIMEPERIOD_NUM_TO_STR[tp]
        else:
            raise NetworkException("Unknown type for tp %s" % str(tp))

        self.setDirection()
        if self.direction == 'access':
            if self.zone_id:
                (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                hwyskims[tpnum].getHwySkimAttributes(origtaz=self.taz, desttaz=self.zone_id, mode=HighwaySkim.MODE_STR_TO_NUM["DA"], segdir = 1)
            else:
                (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                hwyskims[tpnum].getHwySkimAttributes(origtaz=self.taz, desttaz=pnrNodeToTaz[self.lot_id], mode=HighwaySkim.MODE_STR_TO_NUM["DA"], segdir = 1)
            cost = btoll + vtoll
            if dist < 0.01:        
                # no access -- try toll
                if self.zone_id:
                    (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                    hwyskims[tpnum].getHwySkimAttributes(origtaz=self.taz, desttaz=self.zone_id, mode=HighwaySkim.MODE_STR_TO_NUM["TollDA"],segdir = 1)
                else:
                    (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                    hwyskims[tpnum].getHwySkimAttributes(origtaz=self.taz, desttaz=pnrNodeToTaz[self.lot_id], mode=HighwaySkim.MODE_STR_TO_NUM["TollDA"],segdir = 1)
                cost = btoll + vtoll

        elif self.direction == 'egress':
            if self.zone_id:
                (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                hwyskims[tpnum].getHwySkimAttributes(origtaz=self.zone_id, desttaz=self.taz, mode=HighwaySkim.MODE_STR_TO_NUM["DA"], segdir = 1)
            else:
                (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                hwyskims[tpnum].getHwySkimAttributes(origtaz=pnrNodeToTaz[self.lot_id], desttaz=self.taz, mode=HighwaySkim.MODE_STR_TO_NUM["DA"], segdir = 1)
            cost = btoll + vtoll
                            
            if dist > 0.01: # no access - try toll
                if self.zone_id:
                    (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                    hwyskims[tpnum].getHwySkimAttributes(origtaz=self.zone_id, desttaz=self.taz, mode=HighwaySkim.MODE_STR_TO_NUM["TollDA"], segdir = 1)
                else:
                    (time,term,dist,btoll,vtoll,dummy,dummy,dummy) = \
                    hwyskims[tpnum].getHwySkimAttributes(origtaz=pnrNodeToTaz[self.lot_id], desttaz=self.taz, mode=HighwaySkim.MODE_STR_TO_NUM["TollDA"], segdir = 1)
                cost = btoll + vtoll

        self.dist = dist
        self.cost = cost * 0.01
        self.travel_time = time
        self.setStartTimeEndTimeFromTimePeriod(tpstr)

class FastTripsTransferSupplink(FastTripsWalkSupplink):
    def __init__(self,walkskims=None, nodeToTaz=None, maxTaz=None, transfer_type=None, min_transfer_time=None,
                 from_route_id=None, to_route_id=None, schedule_precedence=None, template=None):
        FastTripsWalkSupplink.__init__(self, walkskims, nodeToTaz, maxTaz, template)
        # transfer req'd
        self.from_stop_id = self.Anode
        self.to_stop_id = self.Bnode
        self.transfer_type = None       # 0-whatev,1-timed transfer,2-min xfer time,3-not possible
        self.min_transfer_time = None   # float, minutes
        # transfer_ft req'd
        self.from_route_id = from_route_id
        self.to_route_id = to_route_id
        self.schedule_precedence = None # 'from' or 'to'
    
    def setFromStopID(self, stopid):
        self.from_stop_id = stopid
    
    def setToStopID(self, stopid):
        self.to_stop_id = stopid

    def reverse(self):
        FastTripsWalkSupplink.reverse(self)
        temp = self.from_route_id
        self.from_stop_id = self.Anode
        self.to_stop_id = self.Bnode
        self.from_route_id = self.to_route_id
        self.to_route_id = temp
        if self.schedule_precedence == 'from': self.schedule_precedence = 'to'
        if self.schedule_precedence == 'to': self.schedule_precedence = 'from'