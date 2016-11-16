import copy
import itertools
import re
from .HelperFunctions import *
from .NetworkException import NetworkException
from .Node import Node
from .Logger import WranglerLogger
from .TransitLink import TransitLink
from .Regexes import *
from .WranglerLookups import WranglerLookups

try:
    from Overrides import *
    WranglerLogger.debug("Overrides module found; importing Overrides %s" % Overrides.all)
except Exception as e:
    WranglerLogger.debug("No Overrides module found; skipping import of Overrides")

__all__ = ['Fare']

class Fare(object):
    """
    Fare. Behaves like a dictionary of attributes.
    """
    
    def __init__(self, fare_id=None, operator=None, line=None, mode=None, price=None, tod=None, transfers=None, transfer_duration=None,
                 start_time=None, end_time=None, champ_line_name=None, champ_mode=None, price_conversion=1.00):
        self.attr = {}
        self.fare_id = fare_id

        # stuff needed for FT
        self.fair_id            = None          # calculated
        self.fare_period         = None          # calculated
        self.operator           = operator
        self.line               = line
        self.mode               = mode
        self.champ_mode         = int(champ_mode) if champ_mode else None
        if not self.mode and self.champ_mode: self.mode = WranglerLookups.MODENUM_TO_FTMODETYPE[self.champ_mode]
        self.champ_line_name    = champ_line_name
        self.price              = float(price) if price else 0   # passed by argument
        self.price              = self.price * price_conversion
        self.currency_type      = 'USD'         # default value
        self.payment_method     = 1 if self.mode in WranglerLookups.OFFBOARD_FTMODETYPES or self.operator in WranglerLookups.OFFBOARD_FTAGENCIES else 0     # 0 = on board, 1 = before boarding
        self.transfers          = transfers     # (0, 1, 2, empty).  Number of transfers permitted on this fare
        self.transfer_duration  = transfer_duration # OPTIONAL. Leng of time in seconds before transfer expires
        self.tod                = tod
        self.start_time         = start_time    # hhmmss, 000000 - 235959
        self.end_time           = end_time      # hhmmss, 000000 - 235959
        self.setFareId()
        self.setFareClass()

    def setOperatorAndLineFromChamp(self, champ_line_name=None):
        if not champ_line_name: champ_line_name = self.champ_line_name
        linename_dict = Regexes.linename_pattern.match(champ_line_name).groupdict()
        if not linename_dict: raise NetworkException("INVALID LINENAME %s" % str(name))
        self.operator   = WranglerLookups.OPERATOR_ID_TO_NAME[linename_dict['operator']]
        self.line       = linename_dict['line']
            
    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        '''
        This is a function added for fast-trips.

        regular local fare:
            fare_id: opername_modetype
            fare_period: opername_modetype_allday
        zonal fare:
            fare_id: opername_modetype_2Z (where x is number of zones crossed)
            fare_period: opername_modetype_2Z_allday
        '''
        if fare_id:
            self.fare_id = fare_id
            return self.fare_id
        elif self.operator and self.line:
            operpart = self.operator
            linepart = self.line
        elif self.champ_line_name:
            self.setOperatorAndLineFromChamp(self.champ_line_name)
            operpart = self.operator
            linepart = self.line
        else:
            self.fare_id = 'local'
            return self.fare_id
        typepart = 'local'
        self.fare_id    = '%s_%s' % (operpart, typepart)
        if suffix:
            self.fare_id = '%s_%s' % (self.fare_id, str(suffix))
            
        return self.fare_id

    def setFareClass(self, fare_period=None, style='fasttrips', suffix=None):
        if fare_period:
            self.fare_period = fare_period
            return self.fare_period
        if self.fare_id:
            self.fare_period = self.fare_id
        else:
            self.fare_period = self.setFareId()
        todpart1 = HHMMSSToCHAMPTimePeriod(self.start_time)
        todpart2 = HHMMSSToCHAMPTimePeriod(self.end_time)
        if todpart1 == todpart2:
            todpart = todpart1
        else:
            todpart = '%s_to_%s' % (todpart1, todpart2)
        self.fare_period = '%s_%s' % (self.fare_period, todpart)

    def asDataFrame(self, columns=None):
        import pandas as pd
        data = self.asList(columns)
        df = pd.DataFrame(columns=columns,data=[data])
        return df

    def asList(self, columns=None):
        if columns is None:
            columns = ['stop_id','stop_name','stop_lat','stop_lon','zone_id']
        data = []
        for arg in columns:
            data.append(getattr(self,arg))
        return data
        
    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other):
        return cmp(self.__dict__,other.__dict__)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = ''
        return s

    def __str__(self):
        s = '%s, $%.2f %s' % (self.fare_id if self.fare_id else "unnamed fare", float(price)/100, self.currency_type)
        return s

class ODFare(Fare):
    def __init__(self, fare_id=None, from_node=None, to_node=None, price=None, tod=None, \
                 start_time=None, end_time=None, template=None, station_lookup=None, price_conversion=1.00):
        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, start_time=start_time, end_time=end_time, price_conversion=price_conversion)
        self.from_node = abs(int(from_node))
        self.to_node = abs(int(to_node))
        self.from_name = None
        self.to_name = None
        
        if station_lookup: addStationNames(station_lookup)
        self.setFareId()

    def addStationNames(self, station_lookup):
        self.from_name = station_lookup[self.from_node] if self.from_node in station_lookup.keys() else str(self.from_node)
        self.to_name = station_lookup[self.to_node] if self.to_node in station_lookup.keys() else str(self.to_node)

    def hasStationNames(self):
        if self.from_name and self.to_name: return True
        return False
    
    def __repr__(self):
        s = str(self)
        return s

    def __str__(self):
        return '%s $%.2f from:%s to:%s' % (self.fare_id, float(self.price)/100, self.from_name, self.to_name)

class XFFare(Fare):
    def __init__(self, fare_id=None, from_mode=None, to_mode=None, price=None, tod=None, transfers=None, \
                 transfer_duration=None, start_time=None, end_time=None, price_conversion=1.00):
        # stuff from champ
        self.from_mode = int(from_mode)
        self.to_mode = int(to_mode)
        self.from_desc = WranglerLookups.MODE_TO_MODETYPE[self.from_mode]['desc']
        self.to_desc = WranglerLookups.MODE_TO_MODETYPE[self.to_mode]['desc']
        self.from_type = WranglerLookups.MODE_TO_MODETYPE[self.from_mode]['type']
        self.to_type = WranglerLookups.MODE_TO_MODETYPE[self.to_mode]['type']

        if self.from_mode in WranglerLookups.UNUSED_MODES or self.to_mode in WranglerLookups.UNUSED_MODES:
            self.type = 'na'
        elif self.from_mode in WranglerLookups.EGRESS_MODES or self.to_mode in WranglerLookups.EGRESS_MODES:
            self.type = 'na'
        elif self.from_mode in WranglerLookups.ACCESS_MODES and self.to_mode in WranglerLookups.TRANSIT_MODES:
            self.type = 'board'
        elif self.from_mode in WranglerLookups.TRANSIT_MODES and self.to_mode in WranglerLookups.TRANSIT_MODES:
            self.type = 'xfer'
        elif self.from_mode in WranglerLookups.TRANSFER_MODES:
            self.type = 'xfer'
        else:
            WranglerLogger.warn('UNKNOWN TRANSIT MODE TYPE (%d, %d)' % (self.from_mode, self.to_mode))
            
        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, transfers=transfers, \
                              transfer_duration=transfer_duration, start_time=start_time, end_time=end_time, price_conversion=price_conversion)

    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        if not suffix: suffix = ''
        if self.type == 'xfer':
            suffix = '%s_%s' % (suffix, self.from_type.lower().strip().replace(' ','_') + \
                                '_to_' + self.to_type.lower().strip().replace(' ','_'))
        Fare.setFareId(self,fare_id,style,suffix)
        

    def isBoardType(self):
        if self.from_type in WranglerLookups.NONTRANSIT_TYPES and self.to_type not in WranglerLookups.NONTRANSIT_TYPES:
            return True
        return False
    
    def isTransferType(self):
        if self.from_type in WranglerLookups.TRANSIT_TYPES and self.to_type in WranglerLookups.TRANSIT_TYPES:
            return True
        return False

    def isExitType(self):
        if self.from_type not in WranglerLookups.NONTRANSIT_TYPES and self.to_type in WranglerLookups.NONTRANSIT_TYPES:
            return True
        return False
    
    def __repr__(self):
        s = '%s ($%.2f) %s(%d) %s(%d)' % (self.fare_id, float(self.price)/100, self.from_desc, self.from_mode, self.to_desc, self.to_mode)
        return s

    def __str__(self):
        s = '%s $%.2f %s(%d) %s(%d)' % (self.fare_id, float(self.price)/100, self.from_desc, self.from_mode, self.to_desc, self.to_mode)
        return s

class FarelinksFare(Fare):
    def __init__(self, fare_id=None, links=None, modes=None, price=None, tod=None, start_time=None, end_time=None, oneway=True, price_conversion=1.00):
        if not modes:
            self.modes = [mode] if mode else []
        elif isinstance(modes, list):
            self.modes = modes
        else:
            self.modes = [modes]

        self.farelink = None
        self.mode = None
        self.farelinks = []
        self.oneway = oneway
        
        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, start_time=start_time, end_time=end_time, price_conversion=price_conversion)
        
        if isinstance(links, list):
            for l in links:
                if isinstance(l, TransitLink):
                    self.farelinks.append(link)
                else:
                    link = TransitLink()
                    link.setId(l)
                    self.farelinks.append(link)
        elif isinstance(links, TransitLink):
            self.farelinks.append(links)
        else:
            link = TransitLink()
            link.setId(links)
            self.farelinks.append(link)

        if len(self.farelinks)==1:
            self.farelink = self.farelinks[0]
        if len(self.modes)==1:
            self.mode = self.modes[0]

    def isUnique(self):
        if len(self.farelinks)==1 and len(self.modes)==1:
            return True
        else:
            return False

    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        if fare_id:
            self.fare_id = fare_id
        else:
            # count up transit modes
            i = 0
            for m in self.modes:
                if int(m) in WranglerLookups.MODE_TO_MODETYPE.keys():
                    if not WranglerLookups.MODE_TO_MODETYPE[int(m)] in WranglerLookups.NONTRANSIT_TYPES:
                        i+=1
                        # if it's a transit mode, grab it in case it's the only one
                        modepart = WranglerLookups.MODE_TO_MODETYPE[int(m)]['desc']
            if i == 1:
                pass
            elif i > 1:
                modepart = 'multimode'
            elif i == 0:
                raise NetworkException('FarelinksFare HAS INVALID mode type: %s' % str(self.modes))

            todpart1 = HHMMSSToCHAMPTimePeriod(self.start_time)
            todpart2 = HHMMSSToCHAMPTimePeriod(self.end_time)
            if todpart1 == todpart2:
                todpart = todpart1
            else:
                todpart = '%s_to_%s' % (todpart1, todpart2)

            if style=='fasttrips':
                self.fare_id = '%s_%s_zonefare' % (modepart, todpart)
            elif style=='CHAMP':
                self.fare_id = '%s_%s_farelink' % (modepart, todpart)
            else:
                WranglerLogger.debug("Unknown Fare style %s" % style)
                self.fare_id = '%s_%s_zonefare' % (modepart, todpart)
                
            if suffix:
                self.fare_id = '%s_%s' % (self.fare_id, suffix)
                
            return self.fare_id
        
    def uniqueFarelinksToList(self):
        '''
        Create a unique FarelinksFare for each combination of links and modes
        '''
        farelist = []
        
        for l in self.farelinks:
            for m in self.modes:
                if not self.oneway:
                    l_reverse = str(l.Bnode) + '-' + str(l.Anode)
                    newfare = FarelinksFare(links=l_reverse, modes=m, price=self.price, tod=self.tod, start_time=self.start_time, end_time=self.end_time)
                    farelist.append(newfare)
                newfare = FarelinksFare(links=l, modes=m, price=self.price, tod=self.tod, start_time=self.start_time, end_time=self.end_time)
                farelist.append(newfare)

        return farelist

    def __repr__(self):
        s = str(self)
        return s

    def __str__(self):
        s = '%s $%.2f links(%d):' % (self.fare_id, float(self.price)/100,len(self.farelinks))
        for link, i in zip(self.farelinks,range(len(self.farelinks))):
            s += '%s-%s' % (str(link.Anode), str(link.Bnode))
            if i < len(self.farelinks) - 1: s += ',' 
        s += ' modes:'
        for mode, i in zip(self.modes, range(len(self.modes))):
            s += '%s' % str(mode)
            if i < len(self.modes) - 1: s += ','
        return s        

class FastTripsFare(Fare):
    '''
    This is a class added for fast-trips.
    The fare_id is a unique identifier for a fare in fast-trips, returned by a query on route_id, origin_id, and destination_id.
    
    '''
    def __init__(self,fare_id=None,route_id=None,operator=None,line=None,origin_id=None,destination_id=None,
                 contains_id=None,price=None,fare_period=None,start_time=None,end_time=None,
                 transfers=None,transfer_duration=None,
                 champ_line_name=None, champ_mode=None,
                 zone_suffixes=False, price_conversion=1):

        if isinstance(origin_id, float): origin_id = int(origin_id)
        if isinstance(destination_id, float): destination_id = int(destination_id)
        
        self.route_id       = route_id #champ_line_name
        self.origin_id      = origin_id
        self.destination_id = destination_id
        self.contains_id    = contains_id
        self.zones          = 0
        self.zone_suffixes  = zone_suffixes
        
        Fare.__init__(self, fare_id=fare_id, operator=operator, line=line, price=price, transfers=transfers,
                      transfer_duration=transfer_duration, start_time=start_time, end_time=end_time,
                      champ_line_name=champ_line_name, champ_mode=champ_mode, price_conversion=price_conversion)

    def isZoneFare(self):
        if self.origin_id and self.destination_id:
            return True
        return False
    
    def setModeType(self, modenum):
        self.fasttrips_mode = WranglerLookups.MODENUM_TO_FTMODETYPE[modenum]
        return self.fasttrips_mode
    
    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        '''
        This is a function added for fast-trips.
        
        regular local fare:
            fare_id: opername_modetype
            fare_period: opername_modetype_allday
        zonal fare:
            fare_id: opername_modetype_2Z (where x is number of zones crossed)
            fare_period: opername_modetype_2Z_allday
        '''
        if fare_id:
            self.fare_id = fare_id
            if suffix: self.fare_id = '%s_%s' % (fare_id, suffix)
            return self.fare_id
        elif self.operator and self.line:
            operpart = self.operator.lower()
            linepart = self.line.lower()
        elif self.champ_line_name:
            self.setOperatorAndLineFromChamp(self.champ_line_name)
            operpart = self.operator.lower()
            linepart = self.line.lower()
        else:
            self.fare_id = 'basic'
            return self.fare_id

        ##modepart = 'local_bus' if not self.mode else self.mode
        # SF-specific stuff
        if operpart in ['bart','caltrain','ace']:
            self.fare_id = '%s' % operpart
        elif operpart in ['ferry','amtrak']:
            self.fare_id = '%s_%s' % (operpart,linepart)
        else:
            modepart = self.mode
            self.fare_id    = '%s_%s' % (operpart, modepart)

        if self.zone_suffixes:
            if self.origin_id and self.destination_id:
                if operpart == 'caltrain':
                    orig = str(self.origin_id).lower()[3:]
                    dest = str(self.destination_id).lower()[3:]
                elif operpart == 'bart':
                    orig = str(self.origin_id).lower().replace(' bart','')
                    dest = str(self.destination_id).lower().replace(' bart','')
                else:
                    orig = str(self.origin_id).lower()
                    dest = str(self.destination_id).lower()
                    
                self.fare_id = '%s_zone_%s_to_%s' % (self.fare_id, orig, dest)

        if suffix:
            self.fare_id = '%s_%s' % (self.fare_id, str(suffix))
            
        return self.fare_id        
    
    def __getitem__(self,key): return self[key]
    def __setitem__(self,key,value): self[key]=value
    def __cmp__(self,other):
        if not isinstance(other, FastTripsFare): return -1
        return cmp(self.__dict__,other.__dict__)

    def __str__(self):
        s = 'fare_id: %s, orig_id: %s, dest_id: %s, cont_id: %s, fare_period: %s, price: $%.2f' % (self.fare_id,self.origin_id,self.destination_id,self.contains_id,self.fare_period, float(self.price)/100)
        return s


class FastTripsTransferFare(XFFare):
    def __init__(self, from_fare_period=None, to_fare_period=None, transfer_fare_type=None,
                 from_mode=None, to_mode=None, transfer_fare=None, price_conversion=1):
        # TODO handle conditions where transfer_fare_type is not an incremental cost
        XFFare.__init__(self, from_mode=from_mode, to_mode=to_mode, price=transfer_fare, price_conversion=price_conversion)
        self.from_fare_period = from_fare_period
        self.to_fare_period = to_fare_period
        self.transfer_fare_type = transfer_fare_type if transfer_fare_type else 'transfer_free'
        self.transfer_fare = transfer_fare
        if self.transfer_fare_type == 'transfer_cost' and self.transfer_fare == 0:
            self.transfer_fare_type == 'transfer_free'
            
    def asDataFrame(self, columns):
        if columns is None:
            columns = ['from_fare_period','to_fare_period','is_flat_fee','transfer_rule']
        df = Fare.asDataFrame(self, columns)
        return df

