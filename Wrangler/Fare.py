import copy
import itertools
from .NetworkException import NetworkException
from .Node import Node
from .Logger import WranglerLogger
from .TransitLink import TransitLink

__all__ = ['Fare']

TRN_MODE_DICT = {1:{'desc':"walk access", 'type':"non-transit"},
                 2:{'desc':"walk egress", 'type':"non-transit"},
                 3:{'desc':"drive access", 'type':"non-transit"},
                 4:{'desc':"drive egress", 'type':"non-transit"},
                 5:{'desc':"transfer", 'type':"non-transit"},
                 6:{'desc':"drive funnel", 'type':"non-transit"},
                 7:{'desc':"walk funnel", 'type':"non-transit"},
                 8:{'desc':"empty", 'type':""},
                 9:{'desc':"empty", 'type':""},
                 10:{'desc':"empty", 'type':""},
                 11:{'desc':"Local Muni", 'type':"local bus"},
                 12:{'desc':"Express Muni", 'type':"local bus"},
                 13:{'desc':"BRT Muni", 'type':"local bus"},
                 14:{'desc':"Muni Cable Car", 'type':"LRT"},
                 15:{'desc':"LRT Muni", 'type':"LRT"},
                 16:{'desc':"Free and Open Shuttles", 'type':"local bus"},
                 17:{'desc':"SamTrans Local", 'type':"local bus"},
                 18:{'desc':"AC Local", 'type':"local bus"},
                 19:{'desc':"Other Local MTC Buses", 'type':"local bus"},
                 20:{'desc':"Regional BRT", 'type':"BRT"},
                 21:{'desc':"VTA LRT", 'type':"LRT"},
                 22:{'desc':"AC Transbay Buses", 'type':"Premium"},
                 23:{'desc':"Golden Gate Bus", 'type':"Premium"},
                 24:{'desc':"Sam Trans Express Bus", 'type':"Premium"},
                 25:{'desc':"Other Premium Bus", 'type':"Premium"},
                 26:{'desc':"Caltrain", 'type':"Premium"},
                 27:{'desc':"SMART", 'type':"Premium"},
                 28:{'desc':"eBART", 'type':"Premium"},
                 29:{'desc':"Regional Rail/ACE/AMTRAK", 'type':"Premium"},
                 30:{'desc':"HSR", 'type':"Premium"},
                 31:{'desc':"Ferry", 'type':"Ferry"},
                 32:{'desc':"BART", 'type':"BART"},
                 }

NONTRANSIT_TYPES    = ['non-transit','']
TRANSIT_TYPES       = ['local bus', 'LRT', 'BRT', 'Premium', 'Ferry', 'BART']
OPERATOR_ID_TO_NAME = {'101': "caltrain", '102': "amtrak", '103': "amtrak", '104': "ace",
                        '105': "dumbarton", '106': "smart", '107_': "bart", '108_': "bart",
                        '100_': "bart", '10_': "west_berkeley_shuttle", '11_': "broadway_shuttle",
                        '12_': "shuttle", '13_': "shuttle", '14_': "caltrain_shuttle",
                        '15_': "shuttle", '16_': "shuttle", '17_': "shuttle", '18_': "shuttle",
                        '19_': "shuttle", '26_': "samtrans", '27_': "samtrans", '28_': "samtrans",
                        '29_': "samtrans", '30_': "samtrans", '31_': "scvta", '32_': "scvta",
                        '33_': "scvta", '34_': "scvta", '35_': "scvta",
                        '37_': "ac_transit", '38_': "ac_transit", '39_': "ac_transit", '40_': "ac_transit",
                        '42_': "lavta", '43_': "lavta", '44_': "lavta", '45_': "lavta",
                        '47_': "union_city_transit",
                        '49_': "airbart",
                        '51_': "cccta", '52_': "cccta", '54_': "tri_delta_transit",
                        '56_': "westcat", '57_': "westcat", '59_': "vallejo_transit", '60_': "vallejo_transit",
                        '62_': "fast", '63_': "fast", '64_': "fast",
                        '65_': "american_canyon", '66_': "vacaville", '68_': "benicia",
                        '70_': "vine", '71_': "vine",
                        '73_': "sonoma_county_transit", '74_': "sonoma_county_transit",
                        '76_': "santa_rosa", '78_': "petaluma",
                        '80_': "golden_gate_transit", '82_': "golden_gate_transit", '83_': "golden_gate_transit",
                        '84_': "golden_gate_transit",
                        '90_': "ferry", '91_': "ferry", '92_': "ferry", '93_': "ferry", '94_': "ferry", '95_': "ferry",
                        'EBA': "ebart", 'MUN': "sf_muni", 'PRES': "presidigo", 'SFS': "sfsu_shuttle",}
##BOARDING_MODEPAIRS
##XFER_MODEPAIRS

class Fare(object):
    """
    Fare. Behaves like a dictionary of attributes.
    """
    
    def __init__(self, name=None, price=None, tod=None, transfers=None, transfer_duration=None, start_time=None, end_time=None, template=None):
        self.attr = {}
        self.name = name

        # stuff needed for FT
        self.operator           = None
        self.fair_id            = None          # calculated
        self.fare_class         = None          # calculated
        self.price              = int(price)    # passed by argument
        self.currency_type      = 'USD'         # default value
        self.payment_method     = 0             # 0 = on board, 1 = before boarding
        self.transfers          = transfers     # (0, 1, 2, empty).  Number of transfers permitted on this fare
        self.transfer_duration  = transfer_duration # OPTIONAL. Leng of time in seconds before transfer expires
        self.tod                = tod
        self.start_time         = start_time    # hhmmss, 000000 - 235959
        self.end_time           = end_time      # hhmmss, 000000 - 235959

    def set_operator(self, champ_operator_id=None, champ_line_name=None):
        if champ_operator_id:
            if champ_operator_id in OPERATOR_ID_TO_NAME.keys():
                self.operator = OPERATOR_ID_TO_NAME[champ_operator_id]
            elif champ_operator_id + '_' in OPERATOR_ID_TO_NAME.keys():
                self.operator = OPERATOR_ID_TO_NAME[champ_operator_id + '_']
            else:
                raise NetworkException("invalid operator id")
        elif champ_line_name:
            prefix_len = champ_line_name.find('_')
        
    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other): return cmp(self.name,other)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = ''
        return s

    def __str__(self):
        s = '%s, $%2f %s' % (self.name if self.name else "unnamed fare", float(price)/100, self.currency_type)
        return s

class ODFare(Fare):
    def __init__(self, name=None, from_station=None, to_station=None, price=None, tod=None, start_time=None, end_time=None, template=None, station_lookup=None):
        Fare.__init__(self, name, price, tod, start_time, end_time, template)
        self.fr     = from_station
        self.to     = to_station
        
    def __repr__(self):
        pass

    def __str__(self):
        pass #s = '' % (

class XFFare(Fare):
    def __init__(self, name=None, from_mode=None, to_mode=None, price=None, tod=None, transfers=None, transfer_duration=None, start_time=None, end_time=None, template=None):
        
        Fare.__init__(self, name, price, tod, transfers, transfer_duration, start_time, end_time, template)
        # stuff from champ
        self.fr     = int(from_mode)
        self.to     = int(to_mode)
        self.fr_desc = TRN_MODE_DICT[self.fr]['desc']
        self.to_desc = TRN_MODE_DICT[self.to]['desc']
        self.fr_type = TRN_MODE_DICT[self.fr]['type']
        self.to_type = TRN_MODE_DICT[self.to]['type']
        
        if self.fr_type in NONTRANSIT_TYPES and self.to_type in TRANSIT_TYPES:
            self.type = 'board'
            self.fare_id = self.to_type.lower().strip().replace(' ','_')
        elif self.fr_type in NONTRANSIT_TYPES and self.to_type in NONTRANSIT_TYPES:
            WrangerLogger.warn('INVALID XFARE TYPE FROM mode %s (%d) to mode %s (%d)' % (self.fr_type, self.fr, self.to_type, self.to))
        elif self.fr_type in TRANSIT_TYPES and self.to_type in TRANSIT_TYPES:
            self.type = 'xfer'
            self.fare_id = self.fr_type.lower().strip().replace(' ','_') + '_to_' + self.to_type.lower().strip().replace(' ','_')
        else:
            WranglerLogger.warn('UNKNOWN TRANSIT MODE TYPE (%d, %d)' % (self.fr, self.to))

        # stuff needed for FT
        if tod:
            # if no start/end/tod, then assume all-day fare
            self.fare_class = self.fare_id + '_' + str(tod).lower()
        elif start_time and end_time:
            self.fare_class = self.fare_id + '_' + left(str(start_time),4)
        else:
            self.fare_class = self.fare_id + '_allday'

    def __repr__(self):
        #s = '%s, %s (%d), %s (%d), %d' % (self.name, self.fr_desc, self.fr, self.to_desc, self.to, self.cost)
        s = '%s, %s, %s, %d' % (self.fare_id, self.fr_desc, self.to_desc, self.price)
        return s

    def __str__(self):
        #s = '%s, %s (%d), %s (%d), %d' % (self.name, self.fr_desc, self.fr, self.to_desc, self.to, self.cost)
        s = '%s, %s, %s, %d' % (self.fare_id, self.fr_desc, self.to_desc, self.price)
        return s

class FarelinksFare(Fare):
    def __init__(self, name=None, links=None, modes=None, price=None, tod=None, start_time=None, end_time=None, template=None):
        Fare.__init__(self, name, price, tod, start_time, end_time, template)
        self.fare_id = 'farelink_%s_%s' % (str(links), str(modes))
        self.price = int(price)
        self.modes = modes if isinstance(modes, list) else None
        self.farelinks = []
        
        if isinstance(links, list):
            for l in links:
                link = TransitLink()
                link.setId(l)
                self.farelinks.append(link)
        else:
            link = TransitLink()
            link.setId(links)
            self.farelinks.append(link)

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
