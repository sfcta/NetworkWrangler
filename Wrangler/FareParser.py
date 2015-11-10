from simpleparse.common import numbers, strings, comments
from simpleparse import generator
from simpleparse.parser import Parser
from simpleparse.dispatchprocessor import *
import re, math

from .Fare import Fare, BasicFare, TransferFare

__all__ = [ 'FareParser' ]

WRANGLER_FAREFILE_SUFFICES = [ "fare" ]

# PARSER DEFINITION ------------------------------------------------------------------------------
# NOTE: even though XYSPEED and TIMEFAC are node attributes here, I'm not sure that's really ok --
# Cube documentation implies TF and XYSPD are node attributes...
fare_file_def=r'''
fare_file         := ( od_fare / xf_fare )+, smcw*, whitespace*

od_fare           := whitespace?, smcw?, nodepair, whitespace?, cost, whitespace?, semicolon_comment*
xf_fare           := whitespace?, smcw?, fareblock, whitespace?, "=", whitespace?, cost, whitespace?, semicolon_comment*

nodenum           := int
cost              := int
numseq            := int, (spaces?, ("-" / ","), spaces?, int)*
nodepair          := nodenum, ((spaces?, ("-" / ","), spaces?) / [\t]), nodenum
attr_value        := alphanums / string_single_quote / string_double_quote
alphanums         := [a-zA-Z0-9\.]+
<comma>           := [,]
<whitespace>      := [ \t\r\n]+
<spaces>          := [ \t]+
smcw              := whitespace?, (semicolon_comment / c_comment, whitespace?)+
fareblock         := word_xfer, modeblock_a, modeblock_b
modeblock_a       := openblock, modenum, closeblock
modeblock_b       := openblock, modenum, closeblock
modenum           := int
openblock         := "["
closeblock        := "]"
word_xfer         := c"XFARE"
'''

class FareFileProcessor(DispatchProcessor):
    """ Class to process fare files
    """
    def __init__(self, verbosity=1):
        self.verbosity=verbosity
        self.fares = []
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
            self.fares.append(xxx)

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
            self.fares.append(xxx)

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

    def convertFareData(self):
        """ Convert the parsed tree of data into a usable python list of fares
            returns list of comments and fare objects
        """
        rows = []
        currentFare = None
        key = None
        value = None
        comment = None

        for fare in self.ffp.fares:
            # each link is a (key, value) tuple
            
            # add comments as simple strings:
            if fare[0] in ('smcw','semicolon_comment'):
                if currentFare:
                    currentFare.comment = " "+fare[1].strip()  # fare comment
                    rows.append(currentFare)
                    currentFare = None
                else:
                    rows.append(fare[1].strip())
                continue
            if fare[0] == 'xf_fare':
                if currentFare:
                    rows.append(currentFare)
                    #currentFare = BasicFare(
##        rows = []
##        currentLink = None
##        key = None
##        value = None
##        comment = None
##
##        for link in self.tfp.links:
##            # Each link is a 3-tuple:  key, value, list-of-children.
##
##            # Add comments as simple strings:
##            if link[0] in ('smcw','semicolon_comment'):
##                if currentLink:
##                    currentLink.comment = " "+link[1].strip()  # Link comment
##                    rows.append(currentLink)
##                    currentLink = None
##                else:
##                    rows.append(link[1].strip())  # Line comment
##                continue
##
##            # Link records
##            if link[0] == 'link_attr':
##                # Pay attention only to the children of lin_attr elements
##                kids = link[2]
##                for child in kids:
##                    if child[0] in ('link_attr_name','word_nodes','word_modes'):
##                        key = child[1]
##                        # If this is a NAME attribute, we need to start a new TransitLink.
##                        if key in ('nodes','NODES'):
##                            if currentLink: rows.append(currentLink)
##                            currentLink = TransitLink() # Create new dictionary for this transit support link
##
##                    if child[0]=='nodepair':
##                        currentLink.setId(child[1])
##
##                    if child[0] in ('attr_value','numseq'):
##                        currentLink[key] = child[1]
##                continue
##
##            # Got something unexpected:
##            WranglerLogger.critical("** SHOULD NOT BE HERE: %s (%s)" % (link[0], link[1]))
##
##        # Save last link too
##        if currentLink: rows.append(currentLink)
##        return rows
