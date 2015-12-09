import copy
import itertools
import re
from .NetworkException import NetworkException
from .Node import Node
from .Logger import WranglerLogger
from .TransitLink import TransitLink
from .Regexes import *
from .WranglerLookups import WranglerLookups

__all__ = ['Fare']

class Fare(object):
    """
    Fare. Behaves like a dictionary of attributes.
    """
    
    def __init__(self, fare_id=None, operator=None, line=None, price=None, tod=None, transfers=None, transfer_duration=None, start_time=None, end_time=None, champ_line_name=None):
        self.attr = {}
        self.fare_id = fare_id

        # stuff needed for FT
        self.fair_id            = None          # calculated
        self.fare_class         = None          # calculated
        self.operator           = operator
        self.line               = line
        self.champ_line_name    = champ_line_name
        self.price              = int(price)    # passed by argument
        self.currency_type      = 'USD'         # default value
        self.payment_method     = 0             # 0 = on board, 1 = before boarding
        self.transfers          = transfers     # (0, 1, 2, empty).  Number of transfers permitted on this fare
        self.transfer_duration  = transfer_duration # OPTIONAL. Leng of time in seconds before transfer expires
        self.tod                = tod
        self.start_time         = start_time    # hhmmss, 000000 - 235959
        self.end_time           = end_time      # hhmmss, 000000 - 235959
        self.setFareId()
        self.setFareClass()

    def setOperatorAndLineFromChamp(self, champ_line_name=None):
        linename_dict = linename_pattern.match(name)
        if not linename_dict: raise NetworkException("INVALID LINENAME %s" % str(name))
        self.operator   = WranglerLookups.OPERATOR_ID_TO_NAME[linename_dict['operator']]
        self.line       = WranglerLookups.OPERATOR_ID_TO_NAME[linename_dict['name']]
            
    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        if fare_id:
            self.fare_id = fare_id
            return self.fare_id
        elif self.operator and self.line:
            operpart = self.operator
            linepart = self.line
        elif self.champ_line_name:
            linename_dict = linename_pattern.match(self.champ_line_name)
            if not linename_dict: raise NetworkException("INVALID LINENAME %s" % str(self.champ_line_name))
            operpart = WranglerLookups.OPERATOR_ID_TO_NAME[linename_dict['operator']]
            linepart = WranglerLookups.OPERATOR_ID_TO_NAME[linename_dict['name']]
        else:
            self.fare_id = 'generic'
            return self.fare_id
        
        self.fare_id    = '%s_%s' % (operpart, linepart)
        if suffix:
            self.fare_id = '%s_%s' % (self.fare_id, str(suffix))
            
        return self.fare_id

    def setFareClass(self, fare_class=None, style='fasttrips', suffix=None):
        if self.fare_id:
            self.fare_class = self.fare_id
        else:
            self.fare_class = self.setFareId()
        todpart1 = self.convertStringToTimePeriod(self.start_time)
        todpart2 = self.convertStringToTimePeriod(self.end_time)
        if todpart1 == todpart2:
            todpart = todpart1
        else:
            todpart = '%s_to_%s' % (todpart1, todpart2)
        self.fare_class = '%s_%s' % (self.fare_class, todpart)
        
    def convertStringToTimePeriod(self, hhmmss):
        if hhmmss == None:
            tod = 'allday'
            return tod
        
        re_hhmmss = re.compile('\d\d\d\d\d\d')
        m = re_hhmmss.match(hhmmss)
        if not m:
            raise NetworkException('Invalid timestring format for hhmmss: %s' % str(hhmmss))
        
        if hhmmss < '030000':
            tod = 'ev'
        elif hhmmss < '060000':
            tod = 'ea'
        elif hhmmss < '090000':
            tod = 'am'
        elif hhmmss < '153000':
            tod = 'md'
        elif hhmmss < '183000':
            tod = 'pm'
        elif hhmmss < '240000':
            tod = 'ev'
        else:
            new_hh = '%02d' % (int(hhmmss[:2]) - 24)
            new_hhmmss = new_hh + hhmmss[2:]
            tod = convertStringToTimePeriod(new_hhmmss)
        return tod  
            
    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other): return cmp(self.fare_id,other)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = ''
        return s

    def __str__(self):
        s = '%s, $%2f %s' % (self.fare_id if self.fare_id else "unnamed fare", float(price)/100, self.currency_type)
        return s

class ODFare(Fare):
    def __init__(self, fare_id=None, from_station=None, to_station=None, price=None, tod=None, \
                 start_time=None, end_time=None, template=None, station_lookup=None):
        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, start_time=start_time, end_time=end_time)
        self.fr     = from_station
        self.to     = to_station
        self.setFareId()
        
    def __repr__(self):
        pass

    def __str__(self):
        pass #s = '' % (

class XFFare(Fare):
    def __init__(self, fare_id=None, from_mode=None, to_mode=None, price=None, tod=None, transfers=None, \
                 transfer_duration=None, start_time=None, end_time=None):
        # stuff from champ
        self.fr_mode = int(from_mode)
        self.to_mode = int(to_mode)
        self.fr_desc = WranglerLookups.MODE_TO_MODETYPE[self.fr_mode]['desc']
        self.to_desc = WranglerLookups.MODE_TO_MODETYPE[self.to_mode]['desc']
        self.fr_type = WranglerLookups.MODE_TO_MODETYPE[self.fr_mode]['type']
        self.to_type = WranglerLookups.MODE_TO_MODETYPE[self.to_mode]['type']
        
        if self.fr_type in WranglerLookups.NONTRANSIT_TYPES and self.to_type in WranglerLookups.TRANSIT_TYPES:
            self.type = 'board'
        elif self.fr_type in WranglerLookups.NONTRANSIT_TYPES and self.to_type in WranglerLookups.NONTRANSIT_TYPES:
            WrangerLogger.warn('INVALID XFARE TYPE FROM mode %s (%d) to mode %s (%d)' % (self.fr_type, self.fr, self.to_type, self.to))
        elif self.fr_type in WranglerLookups.TRANSIT_TYPES and self.to_type in WranglerLookups.TRANSIT_TYPES:
            self.type = 'xfer'
        else:
            WranglerLogger.warn('UNKNOWN TRANSIT MODE TYPE (%d, %d)' % (self.fr, self.to))

        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, transfers=transfers, \
                              transfer_duration=transfer_duration, start_time=start_time, end_time=end_time)
        
    def setFareId(self, fare_id=None, style='fasttrips', suffix=None):
        if not suffix: suffix = ''
        if self.type == 'xfer':
            suffix = '%s_%s' % (suffix, self.fr_type.lower().strip().replace(' ','_') + \
                                '_to_' + self.to_type.lower().strip().replace(' ','_'))
        Fare.setFareId(self,fare_id,style,suffix)
        

    def isBoardType(self):
        if self.fr_type in WranglerLookups.NONTRANSIT_TYPES and self.to_type not in WranglerLookups.NONTRANSIT_TYPES:
            return True
        return False
    
    def isTransferType(self):
        if self.fr_type not in WranglerLookups.NONTRANSIT_TYPES and self.to_type not in WranglerLookups.NONTRANSIT_TYPES:
            return True
        return False

    def isExitType(self):
        if self.fr_type not in WranglerLookups.NONTRANSIT_TYPES and self.to_type in WranglerLookups.NONTRANSIT_TYPES:
            return True
        return False
    
    def __repr__(self):
        #s = '%s, %s (%d), %s (%d), %d' % (self.fare_id, self.fr_desc, self.fr, self.to_desc, self.to, self.cost)
        s = '%s, %s, %s, %d' % (self.fare_id, self.fr_desc, self.to_desc, self.price)
        return s

    def __str__(self):
        #s = '%s, %s (%d), %s (%d), %d' % (self.fare_id, self.fr_desc, self.fr, self.to_desc, self.to, self.cost)
        s = '%s, %s, %s, %d' % (self.fare_id, self.fr_desc, self.to_desc, self.price)
        return s

class FarelinksFare(Fare):
    def __init__(self, fare_id=None, links=None, modes=None, price=None, tod=None, start_time=None, end_time=None):
        if not modes:
            self.modes = [mode] if mode else []
        elif isinstance(modes, list):
            self.modes = modes
        else:
            self.modes = [modes]

        self.farelink = None
        self.mode = None
        self.farelinks = []
        
        Fare.__init__(self, fare_id=fare_id, price=price, tod=tod, start_time=start_time, end_time=end_time)
        
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
        if len(self.modes)==0:
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
                        modepart = WranglerLookups.MODE_TO_MODETYPE[int(m)]
            if i == 1:
                pass
            elif i > 1:
                modepart = 'multimode'
            elif i == 0:
                raise NetworkException('FarelinksFare HAS INVALID mode type: %s' % str(self.modes))

            todpart1 = self.convertStringToTimePeriod(self.start_time)
            todpart2 = self.convertStringToTimePeriod(self.end_time)
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
                newfare = FarelinksFare(links=l, modes=m, price=self.price, tod=self.tod, start_time=self.start_time, end_time=self.end_time)
                farelist.append(newfare)

        return farelist

    def __repr__(self):
        s = '%s, $%.2f, links:' % (self.fare_id, self.price/100)
        for link in self.farelinks:
            s += ',%s-%s' % (str(link.nodeA), str(link.nodeB))

        s += ', modes:'
        for mode in self.modes:
            s += ',%s' % str(mode)
            
        return s

    def __str__(self):
        s = '%s, $%.2f, links:' % (self.fare_id, self.price/100)
        for link in self.farelinks:
            s += ',%s-%s' % (str(link.Anode), str(link.Bnode))

        s += ', modes:'
        for mode in self.modes:
            s += ',%s' % str(mode)
            
        return s        

class FastTripsFare(Fare):
    def __init__(self,fare_id=None,operator=None,line=None,origin_id=None,destination_id=None,\
                 contains_id=None,fare_class=None,start_time=None,end_time=None,champ_line_name=None):
        
        Fare.__init__(self, fare_id=fare_id, operator=operator, line=line, price=price, tod=tod, transfers=transfers, \
                      transfer_duration=transfer_duration, start_time=start_time, end_time=end_time, \
                      champ_line_name=champ_line_name)
        self.origin_id      = origin_id
        self.destination_id = destination_id
        self.contains_id    = contains_id

    def __getitem__(self,key): return self[key]
    def __setitem__(self,key,value): self[key]=value
    def __cmp__(self,other): return cmp(self.__dict__,other.__dict__)
    