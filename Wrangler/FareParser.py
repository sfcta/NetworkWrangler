from simpleparse.common import numbers, strings, comments
from simpleparse import generator
from simpleparse.parser import Parser
from simpleparse.dispatchprocessor import *
import re, math

from .Fare import Fare, XFFare, ODFare, FarelinksFare

__all__ = [ 'FareParser' ]

WRANGLER_FAREFILE_SUFFICES = [ "fare" ]

# PARSER DEFINITION ------------------------------------------------------------------------------
# NOTE: even though XYSPEED and TIMEFAC are node attributes here, I'm not sure that's really ok --
# Cube documentation implies TF and XYSPD are node attributes...
fare_file_def=r'''
fare_file         := ( od_fare / xf_fare / farelinks_fare)+, smcw*, whitespace*

od_fare           := whitespace?, smcw?, nodepair, whitespace?, cost, whitespace?, semicolon_comment*
xf_fare           := whitespace?, smcw?, fareblock, whitespace?, "=", whitespace?, cost, whitespace?, semicolon_comment*
farelinks_fare    := (whitespace?, smcw?, c"FARELINKS FARE", "=", whitespace?, cost, whitespace?, comma, whitespace?, "L=",
                        whitespace?, nodepairs, comma?, whitespace?, farelinks_attr*, whitespace?, semicolon_comment*)
farelinks_attr    := (farelinks_attr_name, whitespace?, "=", whitespace?, attr_values, whitespace?, comma?, whitespace?)
farelinks_attr_name := ( c"modes" / c"oneway" )
cost              := int
numseq            := int, (spaces?, ("-" / ","), spaces?, int)*
nodepairs         := nodepair, ( whitespace?, comma, whitespace?, nodepair)*
nodepair          := nodenum_a, ((spaces?, ("-" / ","), spaces?) / [\t] / ' '), nodenum_b
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
nodenum           := int
openblock         := "["
closeblock        := "]"
word_xfer         := c"XFARE"
word_mode         := c"mode"
word_modes        := c"modes"
'''


##farelinks_fare    := (whitespace?, smcw?, c"FARELINKS FARE=", whitespace?, cost, whitespace?, comma, whitespace?, "L=",
##                        whitespace?, nodepair, farelinks_attr*, whitespace?, semicolon_comment*)
class FareFileProcessor(DispatchProcessor):
    """ Class to process fare files
    """
    def __init__(self, verbosity=1):
        self.verbosity=verbosity
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

class FareParser(Parser):

    def __init__(self, filedef=fare_file_def, verbosity=1):
        Parser.__init__(self, filedef)
        self.verbosity=verbosity
        self.ffp = FareFileProcessor(self.verbosity)

    def buildProcessor(self):
        return self.ffp

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
        
        for fare in self.ffp.xf_fares:
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
        
        for fare in self.ffp.od_fares:
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
                currentFare = ODFare(from_station=nodea, to_station=nodeb, price=cost)
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
        
        for fare in self.ffp.farelinks_fares:
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