import copy
import itertools
from .NetworkException import NetworkException
from .Node import Node
from .Logger import WranglerLogger

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
FIRSTBOARD_TYPES = ['non-transit']
##BOARDING_MODEPAIRS
##XFER_MODEPAIRS

class Fare(object):
    """
    Fare. Behaves like a dictionary of attributes.
    """
    
    def __init__(self, name=None, template=None):
        self.attr = {}


    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other): return cmp(self.name,other)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = ''
        return s

    def __str__(self):
        s = ''
        return s

class ODFare(Fare):
    def __init__(self, name=None, from_station=None, to_station=None, cost=None, tod=None, start_time=None, stop_time=None, template=None):
        Fare.__init__(self, name, template)
        self.fr     = from_station
        self.to     = to_station
        self.cost   = cost
        self.tod    = tod

    def __repr__(self):
        pass

class BasicFare(Fare):
    def __init__(self, name=None, from_mode=None, to_mode=None, cost=None, tod=None, start_time=None, stop_time=None, template=None):
        Fare.__init__(self, name, template)
        # stuff from champ
        self.fr     = from_mode
        self.to     = to_mode
        self.fr_desc = Fare.TRN_MODE_DICT[self.fr]['desc']
        self.to_desc = Fare.TRN_MODE_DICT[self.to]['desc']
        self.fr_type = Fare.TRN_MODE_DICT[self.fr]['type']
        self.to_type = Fare.TRN_MODE_DICT[self.to]['type']
        self.cost   = cost
        self.tod    = tod

        # stuff needed for FT (fare_attributes.txt and fare_attributes_ft.txt)
        self.fare_id            = None #
        self.fare_class         = None # for _ft.txt
        self.price              = None
        self.currency_type      = None
        self.payment_method     = None # 0 = on board, 1 = before boarding
        self.transfers          = None # (0, 1, 2, empty).  Number of transfers permitted on this fare
        self.transfer_duration  = None # OPTIONAL. Leng of time in seconds before transfer expires

        # fare_rules.txt
        self.fare_id            = None
        self.route_id           = None
        self.origin_id          = None
        self.destination_id     = None
        self.contains_id        = None

        # fare_rules_ft.txt
        self.fare_id            = None
        self.fare_class         = None
        self.start_time         = None
        self.end_time           = None



    def __repr__(self):
        s = ''
        for key in self.keys:
            if self[key] != None:
                s = s + ', %s: %s' % (key, self[key])
        return s

##    def write

class TransferFare(Fare):
    def __init__(self, name=None, from_mode=None, to_mode=None, cost=None, tod=None, start_time=None, stop_time=None, template=None):
        Fare.__init__(self, name, template)
        self.fr     = from_mode
        self.to     = to_mode
        self.fr_desc = Fare.TRN_MODE_DICT[self.fr]['desc']
        self.to_desc = Fare.TRN_MODE_DICT[self.to]['desc']
        self.fr_type = Fare.TRN_MODE_DICT[self.fr]['type']
        self.to_type = Fare.TRN_MODE_DICT[self.to]['type']
        self.cost   = cost
        self.tod    = tod

        # fare_transfer_rules.txt
        self.from_fare_class    = None
        self.to_fare_class      = None
        self.is_flat_fee        = None
        self.transfer_rule      = None

        # transfers.txt
        self.from_stop_id       = None
        self.to_stop_id         = None
        self.transfer_type      = None
        self.min_transfer_time  = None

        # transfers_ft.txt
        self.from_stop_id           = None
        self.to_stop_id             = None
        self.dist                   = None
        self.from_route_id          = None
        self.to_route_id            = None
        self.schedule_precedence    = None # either 'from' or 'to'
        self.elevation_gain         = None
        self.population_density     = None
        self.retail_density         = None
        self.auto_capacity          = None
        self.indirectness           = None
        