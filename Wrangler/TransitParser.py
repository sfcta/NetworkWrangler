from simpleparse.common import numbers, strings, comments
from simpleparse import generator
from simpleparse.parser import Parser
from simpleparse.dispatchprocessor import *
import re

from .Linki import Linki
from .Logger import WranglerLogger
from .Node import Node
from .PNRLink import PNRLink
from .Supplink import Supplink
from .TransitLine import TransitLine
from .TransitLink import TransitLink
from .ZACLink import ZACLink
from .Fare import Fare, XFFare, ODFare, FarelinksFare

__all__ = [ 'TransitParser' ]

WRANGLER_FILE_SUFFICES = [ "lin", "link", "pnr", "zac", "access", "xfer", "fare" ]

# PARSER DEFINITION ------------------------------------------------------------------------------
# NOTE: even though XYSPEED and TIMEFAC are node attributes here, I'm not sure that's really ok --
# Cube documentation implies TF and XYSPD are node attributes...
transit_file_def=r'''
transit_file      := ( accessli / line / link / pnr / zac / supplink )+, smcw*, whitespace*
fare_file         := ( od_fare / xf_fare / farelinks_fare )+, smcw*, whitespace*

line              := whitespace?, smcw?, c"LINE", whitespace, lin_attr*, lin_node*, whitespace?
lin_attr          := ( lin_attr_name, whitespace?, "=", whitespace?, attr_value, whitespace?,
                       comma, whitespace?, semicolon_comment* )
lin_nodeattr      := ( lin_nodeattr_name, whitespace?, "=", whitespace?, attr_value, whitespace?, comma?, whitespace?, semicolon_comment* )
lin_attr_name     := c"allstops" / c"color" / (c"freq",'[',[1-5],']') / c"mode" / c"name" / c"oneway" / c"owner" / c"runtime" / c"timefac" / c"xyspeed" / c"longname"
lin_nodeattr_name := c"access_c" / c"access" / c"delay" /  c"xyspeed" / c"timefac" 
lin_node          := lin_nodestart?, whitespace?, nodenum, spaces*, comma?, spaces*, semicolon_comment?, whitespace?, lin_nodeattr*
lin_nodestart     := (whitespace?, "N", whitespace?, "=")

link              := whitespace?, smcw?, c"LINK", whitespace, link_attr*, whitespace?, semicolon_comment*
link_attr         := (( (link_attr_name, whitespace?, "=", whitespace?,  attr_value) /
                        (word_nodes, whitespace?, "=", whitespace?, nodepair) /
                        (word_modes, whitespace?, "=", whitespace?, numseq) ),
                      whitespace?, comma?, whitespace?)
link_attr_name    := c"dist" / c"speed" / c"time" / c"oneway"

pnr               := whitespace?, smcw?, c"PNR", whitespace, pnr_attr*, whitespace?
pnr_attr          := (( (pnr_attr_name, whitespace?, "=", whitespace?, attr_value) /
                        (word_node, whitespace?, "=", whitespace?, ( nodepair / nodenum )) /
                        (word_zones, whitespace?, "=", whitespace?, numseq )),
                       whitespace?, comma?, whitespace?, semicolon_comment*)
pnr_attr_name     := c"time" / c"maxtime" / c"distfac" / c"cost"

zac               := whitespace?, smcw?, c"ZONEACCESS", whitespace, zac_attr*, whitespace?, semicolon_comment*
zac_attr          := (( (c"link", whitespace?, "=", whitespace?, nodepair) /
                        (zac_attr_name, whitespace?, "=", whitespace?, attr_value) ),
                      whitespace?, comma?, whitespace?)
zac_attr_name     := c"mode"

supplink          := whitespace?, smcw?, c"SUPPLINK", whitespace, supplink_attr*, whitespace?, semicolon_comment*
supplink_attr     := (( (supplink_attr_name, whitespace?, "=", whitespace?, attr_value) /
                        (c"n", whitespace?, "=", whitespace?, nodepair )),
                       whitespace?, comma?, whitespace?)
supplink_attr_name:= c"mode" / c"dist" / c"speed" / c"oneway" / c"time"
                       
accessli          := whitespace?, smcw?, nodenumA, spaces?, nodenumB, spaces?, accesstag?, spaces?, (float/int)?, spaces?, semicolon_comment?
accesstag         := c"wnr" / c"pnr"

od_fare           := whitespace?, smcw?, nodepair, whitespace?, cost, whitespace?, semicolon_comment*
xf_fare           := whitespace?, smcw?, fareblock, whitespace?, "=", whitespace?, cost, whitespace?, semicolon_comment*
farelinks_fare    := (whitespace?, smcw?, c"FARELINKS FARE", "=", whitespace?, cost, whitespace?, comma, whitespace?, "L=",
                        whitespace?, nodepairs, comma?, whitespace?, farelinks_attr*, whitespace?, semicolon_comment*)
farelinks_attr    := (farelinks_attr_name, whitespace?, "=", whitespace?, attr_values, whitespace?, comma?, whitespace?)
farelinks_attr_name := ( c"modes" / c"oneway" )

cost              := int
word_nodes        := c"nodes"
word_node         := c"node"
word_modes        := c"modes"
word_zones        := c"zones"
numseq            := int, (spaces?, ("-" / ","), spaces?, int)*
nodepairs         := nodepair, ( whitespace?, comma, whitespace?, nodepair)*
nodepair          := nodenum_a, ((spaces?, ("-" / ","), spaces?) / [\t] / ' '), nodenum_b
nodenumA          := nodenum
nodenumB          := nodenum
nodenum           := int
attr_values       := attr_value, (whitespace?, comma, whitespace?, attr_value)*
attr_value        := alphanums / string_single_quote / string_double_quote
alphanums         := [a-zA-Z0-9\.]+
<comma>           := [,]
<whitespace>      := [ \t\r\n]+
<spaces>          := [ \t]+
smcw              := whitespace?, (semicolon_comment / c_comment, whitespace?)+
fareblock         := word_xfer, openblock, modenum_a, closeblock, openblock, modenum_b, closeblock
modenum_a         := modenum
modenum_b         := modenum
modenum           := int
nodenum_a         := nodenum
nodenum_b         := nodenum
openblock         := "["
closeblock        := "]"
word_xfer         := c"XFARE"
'''

class TransitFileProcessor(DispatchProcessor):
    """ Class to process transit files
    """
    def __init__(self, verbosity=1):
        self.verbosity=verbosity
        self.lines = []
        self.links = []
        self.pnrs   = []
        self.zacs   = []
        self.accesslis = []
        self.xferlis   = []
        self.liType    = ''
        self.supplinks = []
        self.xf_fares = []
        self.od_fares = []
        self.farelinks_fares = []
      
        self.endcomments = []

    def crackTags(self, leaf, buffer):
        tag = leaf[0]
        text = buffer[leaf[1]:leaf[2]]
        subtags = leaf[3]

        b = []

        if subtags:
            for leaf in subtags:
                b.append(self.crackTags(leaf, buffer))

        return (tag,text,b)

    def line(self, (tag,start,stop,subtags), buffer):
        # this is the whole line
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this line
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.lines.append(xxx)

        if self.verbosity==2:
            # lines are composed of smcw (semicolon-comment / whitespace), line_attr and lin_node
            for linepart in subtags:
                print "  ",linepart[0], " -> [ ",
                for partpart in linepart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]],")",
                print " ]"

    def link(self, (tag,start,stop,subtags), buffer):
        # this is the whole link
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this link
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.links.append(xxx)

        if self.verbosity==2:
            # links are composed of smcw and link_attr
            for linkpart in subtags:
                print "  ",linkpart[0], " -> [ ",
                for partpart in linkpart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]], ")",
                print " ]"

    def pnr(self, (tag,start,stop,subtags), buffer):
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this link
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.pnrs.append(xxx)

        if self.verbosity==2:
            # pnrs are composed of smcw and pnr_attr
            for pnrpart in subtags:
                print " ",pnrpart[0], " -> [ ",
                for partpart in pnrpart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]], ")",
                print " ]"

    def zac(self, (tag,start,stop,subtags), buffer):
        if self.verbosity>=1:
            print tag, start, stop

        if self.verbosity==2:
            # zacs are composed of smcw and zac_attr
            for zacpart in subtags:
                print " ",zacpart[0], " -> [ ",
                for partpart in zacpart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]], ")",
                print " ]"

        # Append list items for this link
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.zacs.append(xxx)

    def supplink(self, (tag,start,stop,subtags), buffer):
        if self.verbosity>=1:
            print tag, start, stop

        if self.verbosity==2:
            # supplinks are composed of smcw and zac_attr
            for supplinkpart in subtags:
                print " ",supplinkpart[0], " -> [ ",
                for partpart in supplinkpart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]], ")",
                print " ]"
        
        # Append list items for this link
        # TODO: make the others more like this -- let the list separate the parse structures!
        supplink = []
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            supplink.append(xxx)
        self.supplinks.append(supplink)


    def od_fare(self, (tag,start,stop,subtags), buffer):
        # this is the whole line
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this line
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.od_fares.append(xxx)

        if self.verbosity==2:
            # lines are composed of smcw (semicolon-comment / whitespace), line_attr and lin_node
            for farepart in subtags:
                print "  ",farepart[0], " -> [ ",
                for partpart in farepart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]],")",
                print " ]"

    def xf_fare(self, (tag,start,stop,subtags), buffer):
        # this is the whole line
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this line
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.xf_fares.append(xxx)

        if self.verbosity==2:
            # lines are composed of smcw (semicolon-comment / whitespace), line_attr and lin_node
            for farepart in subtags:
                print "  ",farepart[0], " -> [ ",
                for partpart in farepart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]],")",
                print " ]"

    def farelinks_fare(self, (tag,start,stop,subtags), buffer):
        # this is the whole line
        if self.verbosity>=1:
            print tag, start, stop

        # Append list items for this line
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.farelinks_fares.append(xxx)

        if self.verbosity==2:
            # lines are composed of smcw (semicolon-comment / whitespace), line_attr and lin_node
            for farepart in subtags:
                print "  ",farepart[0], " -> [ ",
                for partpart in farepart[3]:
                    print partpart[0], "(", buffer[partpart[1]:partpart[2]],")",
                print " ]"
                
    def smcw(self, (tag,start,stop,subtags), buffer):
        """ Semicolon comment whitespace
        """
        if self.verbosity>=1:
            print tag, start, stop
        
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            self.endcomments.append(xxx)
            
    def accessli(self, (tag,start,stop,subtags), buffer):
        if self.verbosity>=1:
            print tag, start, stop
        
        for leaf in subtags:
            xxx = self.crackTags(leaf,buffer)
            if self.liType=="access":
                self.accesslis.append(xxx)
            elif self.liType=="xfer":
                self.xferlis.append(xxx)
            else:
                raise NetworkException("Found access or xfer link without classification")

class TransitParser(Parser):

    def __init__(self, filedef=transit_file_def, verbosity=1):
        Parser.__init__(self, filedef)
        self.verbosity=verbosity
        self.tfp = TransitFileProcessor(self.verbosity)

    def buildProcessor(self):
        return self.tfp

    def convertLineData(self):
        """ Convert the parsed tree of data into a usable python list of transit lines
            returns list of comments and transit line objects
        """
        rows = []
        currentRoute = None

        for line in self.tfp.lines:
            # Each line is a 3-tuple:  key, value, list-of-children.

            # Add comments as simple strings
            if line[0] == 'smcw':
                cmt = line[1].strip()
                if not cmt==';;<<Trnbuild>>;;':
                    rows.append(cmt)
                continue

            # Handle Line attributes
            if line[0] == 'lin_attr':
                key = None
                value = None
                comment = None
                # Pay attention only to the children of lin_attr elements
                kids = line[2]
                for child in kids:
                    if child[0]=='lin_attr_name': key=child[1]
                    if child[0]=='attr_value': value=child[1]
                    if child[0]=='semicolon_comment': comment=child[1].strip()

                # If this is a NAME attribute, we need to start a new TransitLine!
                if key=='NAME':
                    if currentRoute:
                        rows.append(currentRoute)
                    currentRoute = TransitLine(name=value)
                else:
                    currentRoute[key] = value  # Just store all other attributes

                # And save line comment if there is one
                if comment: currentRoute.comment = comment
                continue

            # Handle Node list
            if line[0] == "lin_node":
                # Pay attention only to the children of lin_attr elements
                kids = line[2]
                node = None
                for child in kids:
                    if child[0]=='nodenum':
                        node = Node(child[1])
                    if child[0]=='lin_nodeattr':
                        key = None
                        value = None
                        for nodechild in child[2]:
                            if nodechild[0]=='lin_nodeattr_name': key = nodechild[1]
                            if nodechild[0]=='attr_value': value = nodechild[1]
                            if nodechild[0]=='semicolon_comment': comment=nodechild[1].strip()
                        node[key] = value
                        if comment: node.comment = comment
                currentRoute.n.append(node)
                continue

            # Got something other than lin_node, lin_attr, or smcw:
            WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (line[0], line[1]))

        # End of tree; store final route and return
        if currentRoute: rows.append(currentRoute)
        return rows

    def convertLinkData(self):
        """ Convert the parsed tree of data into a usable python list of transit lines
            returns list of comments and transit line objects
        """
        rows = []
        currentLink = None
        key = None
        value = None
        comment = None

        for link in self.tfp.links:
            # Each link is a 3-tuple:  key, value, list-of-children.

            # Add comments as simple strings:
            if link[0] in ('smcw','semicolon_comment'):
                if currentLink:
                    currentLink.comment = " "+link[1].strip()  # Link comment
                    rows.append(currentLink)
                    currentLink = None
                else:
                    rows.append(link[1].strip())  # Line comment
                continue

            # Link records
            if link[0] == 'link_attr':
                # Pay attention only to the children of lin_attr elements
                kids = link[2]
                for child in kids:
                    if child[0] in ('link_attr_name','word_nodes','word_modes'):
                        key = child[1]
                        # If this is a NAME attribute, we need to start a new TransitLink.
                        if key in ('nodes','NODES'):
                            if currentLink: rows.append(currentLink)
                            currentLink = TransitLink() # Create new dictionary for this transit support link

                    if child[0]=='nodepair':
                        currentLink.setId(child[1])

                    if child[0] in ('attr_value','numseq'):
                        currentLink[key] = child[1]
                continue

            # Got something unexpected:
            WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (link[0], link[1]))

        # Save last link too
        if currentLink: rows.append(currentLink)
        return rows

    def convertPNRData(self):
        """ Convert the parsed tree of data into a usable python list of PNR objects
            returns list of strings and PNR objects
        """
        rows = []
        currentPNR = None
        key = None
        value = None

        for pnr in self.tfp.pnrs:
            # Each pnr is a 3-tuple:  key, value, list-of-children.
            # Add comments as simple strings

            # Textline Comments
            if pnr[0] =='smcw':
                # Line comment; thus existing PNR must be finished.
                if currentPNR:
                    rows.append(currentPNR)
                    currentPNR = None

                rows.append(pnr[1].strip())  # Append line-comment
                continue

            # PNR records
            if pnr[0] == 'pnr_attr':
                # Pay attention only to the children of attr elements
                kids = pnr[2]
                for child in kids:
                    if child[0] in ('pnr_attr_name','word_node','word_zones'):
                        key = child[1]
                        # If this is a NAME attribute, we need to start a new PNR.
                        if key in ('node','NODE'):
                            if currentPNR:
                                rows.append(currentPNR)
                            currentPNR = PNRLink() # Create new dictionary for this PNR

                    if child[0]=='nodepair' or child[0]=='nodenum':
                        #print "child[0]/[1]",child[0],child[1]
                        currentPNR.id = child[1]
                        currentPNR.parseID()

                    if child[0] in ('attr_value','numseq'):
                        currentPNR[key.upper()] = child[1]

                    if child[0]=='semicolon_comment':
                        currentPNR.comment = ' '+child[1].strip()

                continue

            # Got something unexpected:
            WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (pnr[0], pnr[1]))

        # Save last link too
        if currentPNR: rows.append(currentPNR)
        return rows

    def convertZACData(self):
        """ Convert the parsed tree of data into a usable python list of ZAC objects
            returns list of strings and ZAC objects
        """
        rows = []
        currentZAC = None
        key = None
        value = None

        for zac in self.tfp.zacs:
            # Each zac is a 3-tuple:  key, value, list-of-children.
            # Add comments as simple strings

            # Textline Comments
            if zac[0] in ('smcw','semicolon_comment'):
                if currentZAC:
                    currentZAC.comment = ' '+zac[1].strip()
                    rows.append(currentZAC)
                    currentZAC = None
                else:
                    rows.append(zac[1].strip())  # Append value

                continue

            # Link records
            if zac[0] == 'zac_attr':
                # Pay attention only to the children of lin_attr elements
                kids = zac[2]
                for child in kids:
                    if child[0]=='nodepair':
                        # Save old ZAC
                        if currentZAC: rows.append(currentZAC)
                        # Start new ZAC
                        currentZAC = ZACLink() # Create new dictionary for this ZAC.
                        currentZAC.id=child[1]

                    if child[0] =='zac_attr_name':
                        key = child[1]

                    if child[0]=='attr_value':
                        currentZAC[key] = child[1]

                continue

            # Got something unexpected:
            WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (zac[0], zac[1]))

        # Save last link too
        if currentZAC: rows.append(currentZAC)
        return rows

    def convertLinkiData(self, linktype):
        """ Convert the parsed tree of data into a usable python list of ZAC objects
            returns list of strings and ZAC objects
        """
        rows = []
        currentLinki = None
        key = None
        value = None

        linkis = []
        if linktype=="access":
            linkis=self.tfp.accesslis
        elif linktype=="xfer": 
            linkis=self.tfp.xferlis
        else:
            raise NetworkException("ConvertLinkiData with invalid linktype")
        
        for accessli in linkis:
            # whitespace?, smcw?, nodenumA, spaces?, nodenumB, spaces?, (float/int)?, spaces?, semicolon_comment?
            if accessli[0]=='smcw':
                rows.append(accessli[1].strip())
            elif accessli[0]=='nodenumA':
                currentLinki = Linki()
                rows.append(currentLinki)
                currentLinki.A = accessli[1].strip()
            elif accessli[0]=='nodenumB':
                currentLinki.B = accessli[1].strip()
            elif accessli[0]=='float':
                currentLinki.distance = accessli[1].strip()
            elif accessli[0]=='int':
                currentLinki.xferTime = accessli[1].strip()
            elif accessli[0]=='semicolon_comment':
                currentLinki.comment = accessli[1].strip()
            elif accessli[0]=='accesstag':
                currentLinki.accessType = accessli[1].strip()
            else:
                # Got something unexpected:
                WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (accessli[0], accessli[1]))

        return rows
    
    def convertSupplinksData(self):
        """ Convert the parsed tree of data into a usable python list of Supplink objects
            returns list of strings and Supplink objects
        """
        rows = []
        currentSupplink = None
        key = None
        value = None

        for supplink in self.tfp.supplinks:

            # Supplink records are lists            
            if currentSupplink: rows.append(currentSupplink)
            currentSupplink = Supplink() # Create new dictionary for this PNR
                    
            for supplink_attr in supplink:
                if supplink_attr[0] == 'supplink_attr':
                    if supplink_attr[2][0][0]=='supplink_attr_name':
                        currentSupplink[supplink_attr[2][0][1]] = supplink_attr[2][1][1]
                    elif supplink_attr[2][0][0]=='nodepair':
                        currentSupplink.setId(supplink_attr[2][0][1])
                    else:
                        WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (supplink[0], supplink[1]))
                        raise
                elif supplink_attr[0] == "semicolon_comment":
                    currentSupplink.comment = supplink_attr[1].strip()
                elif supplink_attr[0] == 'smcw':
                    currentSupplink.comment = supplink_attr[1].strip()
                else:
                    WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (supplink[0], supplink[1]))
                    raise
 
        # Save last link too
        if currentSupplink: rows.append(currentSupplink)
        return rows

    def convertXFFareData(self):
        """ Convert the parsed tree of data into a usable python list of fares
            returns list of comments and fare objects
        """
        rows = []
        currentFare = None
        key = None
        value = None
        comment = None
        modea, modeb, cost = None, None, None
        
        for fare in self.tfp.xf_fares:
            # add comments as simple strings:
            if fare[0] in ('smcw','semicolon_comment'):
                if currentFare:
                    currentFare.comment = " "+fare[1].strip()  # fare comment
                    rows.append(currentFare)
                    currentFare = None
                else:
                    rows.append(fare[1].strip())
                continue
            if fare[0] == 'fareblock':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                for kid in fare[2]:
                    if kid[0] == 'modenum_a': modea = kid[1]
                    if kid[0] == 'modenum_b': modeb = kid[1]
            if fare[0] == 'cost':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                cost = fare[1]

            if modea and modeb and cost:
                currentFare = XFFare(from_mode=modea, to_mode=modeb, price=cost)
                ##print "Current Fare: ", str(currentFare)
                modea, modeb, cost = None, None, None

        if currentFare: rows.append(currentFare)
        return rows
    
    def convertODFareData(self):
        """ Convert the parsed tree of data into a usable python list of fares
            returns list of comments and fare objects
        """
        rows = []
        currentFare = None
        key = None
        value = None
        comment = None
        nodea, nodeb, cost = None, None, None
        
        for fare in self.tfp.od_fares:
            # add comments as simple strings:
            if fare[0] in ('smcw','semicolon_comment'):
                if currentFare:
                    currentFare.comment = " "+fare[1].strip()  # fare comment
                    rows.append(currentFare)
                    currentFare = None
                else:
                    rows.append(fare[1].strip())
                continue
            if fare[0] == 'nodepair':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                for kid in fare[2]:
                    if kid[0] == 'nodenum_a': nodea = kid[1]
                    if kid[0] == 'nodenum_b': nodeb = kid[1]
            if fare[0] == 'cost':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                cost = fare[1]

            if nodea and nodeb and cost:
                currentFare = ODFare(from_node=nodea, to_node=nodeb, price=cost)
                ##print "Current Fare: ", str(currentFare)
                nodea, nodeb, cost = None, None, None

        if currentFare: rows.append(currentFare)
        return rows

    def convertFarelinksFareData(self):
        """ Convert the parsed tree of data into a usable python list of fares
            returns list of comments and fare objects
        """
        rows = []
        currentFare = None
        key = None
        value = None
        comment = None
        cost, modes, nodepairs = None, [], []
        
        for fare in self.tfp.farelinks_fares:
            # add comments as simple strings:
            if fare[0] in ('smcw','semicolon_comment'):
                if currentFare:
                    currentFare.comment = " "+fare[1].strip()  # fare comment
                    rows.append(currentFare)
                    currentFare = None
                else:
                    rows.append(fare[1].strip())
                continue
            if fare[0] == 'nodepairs':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                for kid in fare[2]:
                    if kid[0] == 'nodepair': nodepairs.append(kid[1])
            if fare[0] == 'farelinks_attr':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                for kid in fare[2]:
                    if kid[0]=='farelinks_attr_name': key=kid[1]
                    if kid[0]=='attr_values':
                        for kidkid in kid[2]:
                            if kidkid[0]=='attr_value': value = kidkid[1]
                            if key=='modes': modes.append(value)
                    if kid[0]=='semicolon_comment': comment = kid[1].strip()
            if fare[0] == 'cost':
                if currentFare:
                    rows.append(currentFare)
                    currentFare = None
                cost = fare[1]

            if len(nodepairs) > 0 and len(modes) > 0 and cost:
                currentFare = FarelinksFare(links=nodepairs, modes=modes, price=cost)
                #print "Current Fare: ", str(currentFare)
                cost, modes, nodepairs = None, [], []

        if currentFare: rows.append(currentFare)
        return rows     