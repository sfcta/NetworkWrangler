import os,sys,copy
from .Logger import WranglerLogger
from .HelperFunctions import *

__all__ = ['Node']

class Node(object):
    """
    Transit node. This can only exist as part of a transit line.
    
    * *num* is the string representation of the node number with stop-status (e.g. '-24322')
    * *stop* is True or False
    
    All other attributes stored as a dictionary. e.g::

        thisnode["DELAY"]="0.5"

    """
    
    # static variables for nodes.xls
    descriptions        = {}
    node_to_zone        = {}
    onstreet_nodes      = []
    offstreet_nodes     = []
    descriptions_read   = False

    def __init__(self, n, coord_dict=None, template=None):
        self.comment = None
        self.attr = {}
        
        if template: self._applyTemplate(template)
        
        if isinstance(n,int):
            self.num = str(n)
        else:
            self.num = n            
        self.stop=(self.num.find('-')<0 and True or False)

        Node.getDescriptions()  

        if isinstance(coord_dict, dict):
            (self.x,self.y) = coord_dict[abs(int(n))]
        else:
            (self.x,self.y) = (-1,-1)
        

    def addXY(self, coords):
        """
        takes an (x,y) tuple or a dict of node numbers to (x,y) tuples
        """
        n = abs(int(self.num))
        if isinstance(coords, tuple):
            (self.x, self.y) = coords
        elif isinstance(coords, dict):
            (self.x, self.y) = coords[n]
            
    def setStop(self, isStop=True):
        """
        Changes to stop-status of this node to *isStop*
        """
        n = abs(int(self.num))
        self.stop = isStop

        if not self.stop:
            n = -n

        self.num = str(n)

    def isStop(self):
        """
        Returns True if this node is a stop, False if not.
        """
        if int(self.num)>0: return True
        return False

    def boardsDisallowed(self):
        """
        Returns True if this node is a stop and boardings are disallowed (ACCESS=2)
        """
        if not self.isStop(): return False
        
        if "ACCESS" not in self.attr: return False
        
        if int(self.attr["ACCESS"]) == 2: return True
        
        return False

    def lineFileRepr(self, prependNEquals=False, lastNode=False):
        """
        String representation for line file
        """

        if prependNEquals: s=" N="
        else:              s="   "

        # node number
        if self.stop: s+= " "
        s += self.num
        # attributes
        for k,v in sorted(self.attr.items()):
            if k=="DELAY" and float(v)==0: continue  # NOP
            s +=", %s=%s" % (k,v) 
        # comma
        if not lastNode: s+= ","
        # comment
        if self.comment: s+=' %s' % (self.comment,)
        # eol
        s += "\n"
        return s

    # Dictionary methods
    def __getitem__(self,key): return self.attr[key]
    def __setitem__(self,key,value): self.attr[key]=value
    def __cmp__(self,other): return cmp(self.__dict__,other.__dict__)

    def description(self):
        """
        Returns the description of this node (a string), or None if unknown.
        """
        Node.getDescriptions()
        
        if abs(int(self.num)) in Node.descriptions:
            return Node.descriptions[abs(int(self.num))]
        
        return None

    @staticmethod
    def getDescriptions():
        # if we've already done this, do nothing
        if Node.descriptions_read: return
        
        try:
            import xlrd
            workbook = xlrd.open_workbook(filename=os.environ["CHAMP_node_names"],
                                          encoding_override='ascii')
            sheet    = workbook.sheet_by_name("equiv")
            row = 0
            while (row < sheet.nrows):
                Node.descriptions[int(sheet.cell_value(row,0))] = \
                    sheet.cell_value(row,1).encode('utf-8')
                row+=1
            
            # print "Read descriptions: " + str(Node.descriptions)
        except ImportError: 
            print "Could not import xlrd module, Node descriptions unknown"
        except:
            print "Unexpected error reading Nodes.xls:", sys.exc_info()[0]
            print sys.exc_info()
            
        Node.descriptions_read = True

    @staticmethod
    def setNodeToZone(node_to_zone):
        if not isinstance(node_to_zone, dict): raise NetworkException("INVALID NODE_TO_ZONE DICTIONARY")
        Node.node_to_zone = node_to_zone

    @staticmethod
    def addNodeToZone(node, zone):
        if node in Node.node_to_zone.keys():
            if zone != Node.node_to_zone[node]:
                WranglerLogger.warn("Overwriting Zone ID %s with %s for Node %s" % (str(zone), str(Node.node_to_zone[node]), str(node)))
        Node.node_to_zone[node] = zone

    @staticmethod
    def setOnStreetNodes(onstreet_nodes):
        if not isinstance(onstreet_nodes, list): raise NetworkException("INVALID ONSTREET_NODES LIST")
        Node.onstreet_nodes = onstreet_nodes
        
    @staticmethod
    def setOffStreetNodes(offstreet_nodes):
        if not isinstance(offstreet_nodes, list): raise NetworkException("INVALID OFFSTREET_NODES LIST")
        Node.offstreet_nodes = offstreet_nodes

    def _applyTemplate(self, template):
        self.attr   = copy.deepcopy(template.attr)
        self.x      = copy.deepcopy(template.x)
        self.y      = copy.deepcopy(template.y)
        self.num    = copy.deepcopy(template.num)
        self.comment = copy.deepcopy(template.comment)
        self.stop   = copy.deepcopy(template.stop)
        
class FastTripsNode(Node):
    '''
    FastTrips Node Class.
    '''
    def __init__(self, n, champ_coord_dict=None, stop_lat=None, stop_lon=None, template=None, isPNR=False):
        Node.__init__(self,n,champ_coord_dict,template)

        # stops.txt req'd
        self.stop_id        = abs(int(n))
        self.ispnr          = isPNR
        self.stop_name      = Node.descriptions[self.stop_id] if self.stop_id in Node.descriptions.keys() else str(self.stop_id)
        if self.ispnr:
            self.lot_id = 'lot_' + str(self.stop_id)
        self.stop_sequence  = None
        if stop_lat and stop_lon:
            self.stop_lat = stop_lat
            self.stop_lon = stop_lon
        else:
            self.stop_lon, self.stop_lat = reproject_to_wgs84(self.x,self.y,EPSG='+init=EPSG:2227')

        # stops optional
        self.stop_code              = None
        self.stop_desc              = None

        if self.stop_id in Node.node_to_zone.keys():
            self.zone_id            = Node.node_to_zone[self.stop_id]
        else:
            self.zone_id            = None
        self.location_type          = None
        self.parent_station         = None
        self.stop_timezone          = None
        self.wheelchair_boarding    = None

        # stops_ft req'd
        ## -- none --
        
        # stops_ft optional
        self.shelter                = None
        self.lighting               = None
        self.bike_parking           = None
        self.bike_share_station     = None
        self.seating                = None
        self.platform_height        = None
        self.level                  = None
        self.off_board_payment      = None

    def addXY(self, coords):
        """
        takes an (x,y) tuple or a dict of node numbers to (x,y) tuples
        """
        n = abs(int(self.num))
        if isinstance(coords, tuple):
            (self.x, self.y) = coords
        elif isinstance(coords, dict):
            (self.x, self.y) = coords[n]
        self.stop_lon, self.stop_lat = reproject_to_wgs84(self.x,self.y,EPSG='+init=EPSG:2227')

    def asList(self, columns=None):
        if columns is None:
            columns = ['stop_id','stop_name','stop_lat','stop_lon','zone_id']
        data = []
        for arg in columns:
            data.append(getattr(self,arg))
        return data
            
    def asDataFrame(self, columns=None):
        import pandas as pd
        data = self.asList(columns)        
        df = pd.DataFrame(columns=columns,data=[data])
        return df
        
