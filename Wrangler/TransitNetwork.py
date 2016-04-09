import copy, glob, inspect, math, os, re, sys, xlrd
from collections import defaultdict
from .Linki import Linki
from .Logger import WranglerLogger
from .Network import Network
from .NetworkException import NetworkException
from .Node import Node, FastTripsNode
from .PNRLink import PNRLink
from .Regexes import * #nodepair_pattern
from .TransitAssignmentData import TransitAssignmentData, TransitAssignmentDataException
from .TransitCapacity import TransitCapacity
from .TransitLine import TransitLine, FastTripsTransitLine
from .TransitLink import TransitLink
from .TransitParser import TransitParser, transit_file_def
from .Fare import ODFare, XFFare, FarelinksFare, FastTripsFare, FastTripsTransferFare
from .ZACLink import ZACLink
from .Supplink import Supplink, FastTripsWalkSupplink, FastTripsDriveSupplink, FastTripsTransferSupplink
from .HelperFunctions import *
from .WranglerLookups import *
import pandas as pd
import numpy as np
try:
    from Overrides import *
    WranglerLogger.debug("Overrides module found; importing Overrides %s" % Overrides.all)
except Exception as e:
    WranglerLogger.debug("No Overrides module found; skipping import of Overrides")

__all__ = ['TransitNetwork']

class TransitNetwork(Network):
    """
    Full Cube representation of a transit network (all components)
    """
    FARE_FILES = ["caltrain.fare",
                  "smart.fare",
                  "ebart.fare",
                  "amtrak.fare",
                  "hsr.fare",
                  "ferry.fare",
                  "bart.fare",
                  "xfer.fare",
                  "farelinks.fare"]

    # Static reference to a TransitCapacity instance
    capacity = None

    def __init__(self, champVersion, basenetworkpath=None, networkBaseDir=None, networkProjectSubdir=None,
                 networkSeedSubdir=None, networkPlanSubdir=None, isTiered=False, networkName=None):
        """
        If *basenetworkpath* is passed and *isTiered* is True, then start by reading the files
        named *networkName*.* in the *basenetworkpath*
        """
        Network.__init__(self, champVersion, networkBaseDir, networkProjectSubdir, networkSeedSubdir,
                         networkPlanSubdir, networkName)
        
        self.lines              = []
        self.links              = []    # note self.links is transit support links, i.e. stuff in muni.link, caltrain.link, etc.
        self.pnrs               = []
        self.zacs               = []
        self.supplinks          = {}    # tod -> supplinks
        self.accessli           = []
        self.xferli             = []
        self.farefiles          = {}    # farefile name -> [ lines in farefile ]
        self.od_fares           = []    # added for fast-trips
        self.xf_fares           = []    # added for fast-trips
        self.farelinks_fares    = []    # added for fast-trips
        self.fasttrips_fares    = []    # added for fast-trips
        self.fasttrips_transfer_fares = [] # added for fast-trips
        self.fasttrips_nodes    = {}    # added for fast-trips dict of int nodenum -> FastTripsNode
        self.fasttrips_walk_supplinks       = {}    # (Anode,Bnode,modenum) -> supplink
        self.fasttrips_drive_supplinks      = {}
        self.fasttrips_transfer_supplinks   = {}
        self.fasttrips_pnrs     = {}    # added for fast-trips dict of int nodenum -> FastTripsNode
        self.fasttrips_timezone = "US/Pacific"
        self.fasttrips_agencies = {}
        self.fasttrips_calendar = {}
        self.coord_dict = {}
        
        for farefile in TransitNetwork.FARE_FILES:
            self.farefiles[farefile] = []

        self.DELAY_VALUES = None
        self.currentLineIdx = 0

        if basenetworkpath and isTiered:
            if not networkName:
                raise NetworkException("Cannot initialize tiered TransitNetwork with basenetworkpath %s: no networkName specified" % basenetworkpath)

            for filename in glob.glob(os.path.join(basenetworkpath, networkName + ".*")):
                suffix = filename.rsplit(".")[-1].lower()
                if suffix in ["lin","link","pnr","zac","access","xfer"]:
                    self.parseFile(filename)

            # fares
            for farefile in TransitNetwork.FARE_FILES:
                fullfarefile = os.path.join(basenetworkpath, farefile)
                linecount = 0
                # WranglerLogger.debug("cwd=%s  farefile %s exists? %d" % (os.getcwd(), fullfarefile, os.path.exists(fullfarefile)))
                
                if os.path.exists(fullfarefile):
                    infile = open(fullfarefile, 'r')
                    lines = infile.readlines()
                    self.farefiles[farefile].extend(lines)
                    linecount = len(lines)
                    infile.close()
                    WranglerLogger.debug("Read %5d lines from fare file %s" % (linecount, fullfarefile))
                                    

    def __iter__(self):
        """
        Iterator for looping through lines.
        """
        self.currentLineIdx = 0
        return self

    def next(self):
        """
        Method for iterator.  Iterator usage::

            net = TransitNetwork()
            net.mergeDir("X:\some\dir\with_transit\lines")
            for line in net:
                print line

        """

        if self.currentLineIdx >= len(self.lines): # are we out of lines?
            raise StopIteration

        while not isinstance(self.lines[self.currentLineIdx],TransitLine):
            self.currentLineIdx += 1

            if self.currentLineIdx >= len(self.lines):
                raise StopIteration

        self.currentLineIdx += 1
        return self.lines[self.currentLineIdx-1]

    def __repr__(self):
        return "TransitNetwork: %s lines, %s links, %s PNRs, %s ZACs" % (len(self.lines),len(self.links),len(self.pnrs),len(self.zacs))

    def isEmpty(self):
        """
        TODO: could be smarter here and check that there are no non-comments since those
        don't really count.
        """
        if (len(self.lines) == 0 and
            len(self.links) == 0 and
            len(self.pnrs) == 0 and
            len(self.zacs) == 0 and
            len(self.accessli) == 0 and
            len(self.xferli) == 0):
            return True
        
        return False
    
    def clear(self, projectstr):
        """
        Clears out all network data to prep for a project apply, e.g. the MuniTEP project is a complete
        Muni network so clearing the existing contents beforehand makes sense.
        If it's already clear then this is a no-op but otherwise
        the user will be prompted (with the project string) so that the log will be clear.
        """
        if self.isEmpty():
            # nothing to do!
            return
        
        query = "Clearing network for %s:\n" % projectstr
        query += "   %d lines, %d links, %d pnrs, %d zacs, %d accessli, %d xferli\n" % (len(self.lines), 
            len(self.links), len(self.pnrs), len(self.zacs), len(self.accessli), len(self.xferli))
        query += "Is this ok? (y/n) "
        WranglerLogger.debug(query)
        response = raw_input("")
        
        WranglerLogger.debug("response=[%s]" % response)
        if response != "Y" and response != "y":
            exit(0)
            
        del self.lines[:]
        del self.links[:]
        del self.pnrs[:]
        del self.zacs[:]
        del self.accessli[:]
        del self.xferli[:]

    def clearLines(self):
        """
        Clears out all network **line** data to prep for a project apply, e.g. the MuniTEP project is a complete
        Muni network so clearing the existing contents beforehand makes sense.
        """
        del self.lines[:]


    def validateWnrsAndPnrs(self):
        """
        Goes through the transit lines in this network and for those that are offstreet (e.g.
        modes 4 or 9), this method will validate that the xfer/pnr/wnr relationships look ship-shape.
        Pretty verbose in the debug log.
        """
        WranglerLogger.debug("Validating Off Street Transit Node Connections")
        
        nodeInfo        = {} # lineset => { station node => { xfer node => [ walk node, pnr node ] }}
        setToModeType   = {} # lineset => list of ModeTypes ("Local", etc)
        setToOffstreet  = {} # lineset => True if has offstreet nodes
        doneNodes       = set()
        
        # For each line
        for line in self:
            if not isinstance(line,TransitLine): continue
            # print "validating", line
            
            lineset = line.name[0:3]
            if lineset not in nodeInfo:
                nodeInfo[lineset]       = {}
                setToModeType[lineset]  = []
                setToOffstreet[lineset] = False
            if line.getModeType() not in setToModeType[lineset]:
                setToModeType[lineset].append(line.getModeType())
                setToOffstreet[lineset] = (setToOffstreet[lineset] or line.hasOffstreetNodes())
            
            # for each stop
            for stopIdx in range(len(line.n)):
                if not line.n[stopIdx].isStop(): continue
                
                stopNodeStr = line.n[stopIdx].num

                wnrNodes = set()
                pnrNodes = set()
                
                if stopNodeStr in nodeInfo[lineset]: continue
                nodeInfo[lineset][stopNodeStr] = {}
                   
                #print " check if we have access to an on-street node"
                for link in self.xferli:
                    if not isinstance(link,Linki): continue
                    # This xfer links the node to the on-street network
                    if link.A == stopNodeStr:
                        nodeInfo[lineset][stopNodeStr][link.B] = ["-","-"]
                    elif link.B == stopNodeStr:
                        nodeInfo[lineset][stopNodeStr][link.A] = ["-","-"]
                    
                #print " Check for WNR"
                for zac in self.zacs:
                    if not isinstance(zac,ZACLink): continue
                    
                    m = re.match(Regexes.nodepair_pattern, zac.id)
                    if m.group(1)==stopNodeStr: wnrNodes.add(int(m.group(2)))
                    if m.group(2)==stopNodeStr: wnrNodes.add(int(m.group(1)))
                    
                #print "Check for PNR"
                for pnr in self.pnrs:
                    if not isinstance(pnr, PNRLink): continue
                    pnr.parseID()
                    if pnr.station==stopNodeStr and pnr.pnr!=PNRLink.UNNUMBERED:
                        pnrNodes.add(int(pnr.pnr))
                        
                #print "Check that our access links go from an onstreet xfer to a pnr or to a wnr"
                for link in self.accessli:
                    if not isinstance(link,Linki): continue
                    try:
                        if int(link.A) in wnrNodes:
                            nodeInfo[lineset][stopNodeStr][link.B][0] = link.A
                        elif int(link.B) in wnrNodes:
                            nodeInfo[lineset][stopNodeStr][link.A][0] = link.B
                        elif int(link.A) in pnrNodes:
                            nodeInfo[lineset][stopNodeStr][link.B][1] = link.A
                        elif int(link.B) in pnrNodes:
                            nodeInfo[lineset][stopNodeStr][link.A][1] = link.B
                    except KeyError:
                        # if it's not offstreet then that's ok
                        if not setToOffstreet[lineset]: continue
                        
                        errorstr = "Invalid access link found in %s lineset %s (incl offstreet) stopNode %s -- Missing xfer?  A=%s B=%s, xfernodes=%s wnrNodes=%s pnrNodes=%s" % \
                            (line.getModeType(), lineset, stopNodeStr, link.A, link.B, str(nodeInfo[lineset][stopNodeStr].keys()), str(wnrNodes), str(pnrNodes))
                        WranglerLogger.warning(errorstr)
                        # raise NetworkException(errorstr)

        nodeNames = getChampNodeNameDictFromFile(os.environ["CHAMP_node_names"])
        
        # print it all out
        for lineset in nodeInfo.keys():

            stops = nodeInfo[lineset].keys()
            stops.sort()
              
            WranglerLogger.debug("--------------- Line set %s %s -- hasOffstreet? %s------------------" % 
                                 (lineset, str(setToModeType[lineset]), str(setToOffstreet[lineset])))
            WranglerLogger.debug("%-30s %10s %10s %10s %10s" % ("stopname", "stop", "xfer", "wnr", "pnr"))
            for stopNodeStr in stops:
                numWnrs = 0
                stopname = "Unknown stop name"
                if int(stopNodeStr) in nodeNames: stopname = nodeNames[int(stopNodeStr)]
                for xfernode in nodeInfo[lineset][stopNodeStr].keys():
                    WranglerLogger.debug("%-30s %10s %10s %10s %10s" % 
                                 (stopname, stopNodeStr, xfernode, 
                                  nodeInfo[lineset][stopNodeStr][xfernode][0],
                                  nodeInfo[lineset][stopNodeStr][xfernode][1]))
                    if nodeInfo[lineset][stopNodeStr][xfernode][0] != "-": numWnrs += 1
                
                if numWnrs == 0 and setToOffstreet[lineset]:
                    errorstr = "Zero wnrNodes or onstreetxfers for stop %s!" % stopNodeStr
                    WranglerLogger.critical(errorstr)
                    # raise NetworkException(errorstr)
                                                              
    def line(self, name):
        """
        If a string is passed in, return the line for that name exactly (a :py:class:`TransitLine` object).
        If a regex, return all relevant lines (a list of TransitLine objects).
        If 'all', return all lines (a list of TransitLine objects).
        """
        if isinstance(name,str):
            if name in self.lines:
                return self.lines[self.lines.index(name)]

        if str(type(name))=="<type '_sre.SRE_Pattern'>":
            toret = []
            for i in range(len(self.lines)):
                if isinstance(self.lines[i],str): continue
                if name.match(self.lines[i].name): toret.append(self.lines[i])
            return toret
        if name=='all':
            allLines = []
            for i in range(len(self.lines)):
                allLines.append(self.lines[i])
            return allLines
        raise NetworkException('Line name not found: %s' % (name,))
    
    def deleteLinkForNodes(self, nodeA, nodeB, include_reverse=True):
        """
        Delete any TransitLink in self.links[] from nodeA to nodeB (these should be integers).
        If include_reverse, also delete from nodeB to nodeA.
        Returns number of links deleted.
        """
        del_idxs = []
        for idx in range(len(self.links)-1,-1,-1): # go backwards
            if not isinstance(self.links[idx],TransitLink): continue
            if self.links[idx].Anode == nodeA and self.links[idx].Bnode == nodeB:
                del_idxs.append(idx)
            elif include_reverse and self.links[idx].Anode == nodeB and self.links[idx].Bnode == nodeA:
                del_idxs.append(idx)

        for del_idx in del_idxs:
            WranglerLogger.debug("Removing link %s" % str(self.links[del_idx]))
            del self.links[del_idx]
        
        return len(del_idxs)
    
    def deleteAccessXferLinkForNode(self, nodenum, access_links=True, xfer_links=True):
        """
        Delete any Linki in self.accessli (if access_links) and/or self.xferli (if xfer_links)
        with Anode or Bnode as nodenum.
        Returns number of links deleted.
        """
        del_acc_idxs = []
        if access_links:
            for idx in range(len(self.accessli)-1,-1,-1): # go backwards
                if not isinstance(self.accessli[idx],Linki): continue
                if int(self.accessli[idx].A) == nodenum or int(self.accessli[idx].B) == nodenum:
                    del_acc_idxs.append(idx)
            
            for del_idx in del_acc_idxs:
                WranglerLogger.debug("Removing access link %s" % str(self.accessli[del_idx]))
                del self.accessli[del_idx]

        del_xfer_idxs = []
        if xfer_links:
            for idx in range(len(self.xferli)-1,-1,-1): # go backwards
                if not isinstance(self.xferli[idx],Linki): continue
                if int(self.xferli[idx].A) == nodenum or int(self.xferli[idx].B) == nodenum:
                    del_xfer_idxs.append(idx)
            
            for del_idx in del_xfer_idxs:
                WranglerLogger.debug("Removing xfere link %s" % str(self.xferli[del_idx]))
                del self.xferli[del_idx]
                
        return len(del_acc_idxs) + len(del_xfer_idxs)
                
    def splitLinkInTransitLines(self,nodeA,nodeB,newNode,stop=False):
        """
        Goes through each line and for any with links going from *nodeA* to *nodeB*, inserts
        the *newNode* in between them (as a stop if *stop* is True).
        """
        totReplacements = 0
        for line in self:
            if line.hasLink(nodeA,nodeB):
                line.splitLink(nodeA,nodeB,newNode,stop=stop)
                totReplacements+=1
        WranglerLogger.debug("Total Lines with Link %s-%s split:%d" % (str(nodeA),str(nodeB),totReplacements))
    
    def replaceSegmentInTransitLines(self,nodeA,nodeB,newNodes):
        """
        *newNodes* should include nodeA and nodeB if they are not going away
        """
        totReplacements = 0
        allExp=re.compile(".")
        newSection=newNodes # [nodeA]+newNodes+[nodeB]
        for line in self.line(allExp):
            if line.hasSegment(nodeA,nodeB):
                WranglerLogger.debug(line.name)
                line.replaceSegment(nodeA,nodeB,newSection)
                totReplacements+=1
        WranglerLogger.debug("Total Lines with Segment %s-%s replaced:%d" % (str(nodeA),str(nodeB),totReplacements))

    def setCombiFreqsForShortLine(self, shortLine, longLine, combFreqs):
        """
        Set all five headways for a short line to equal a combined 
        headway including long line. i.e. set 1-California Short frequencies
        by inputing the combined frequencies of both lines.
        
        .. note:: Make sure *longLine* frequencies are set first!
        """
        try:
            longLineInst=self.line(longLine)
        except:
            raise NetworkException('Unknown Route!  %s' % (longLine))
        try: 
            shortLineInst=self.line(shortLine)
        except:
            raise NetworkException('Unknown Route!  %s' % (shortLine))       

        [amLong,mdLong,pmLong,evLong,eaLong] = longLineInst.getFreqs()
        [amComb,mdComb,pmComb,evComb,eaComb] = combFreqs
        [amShort,mdShort,pmShort,evShort,eaShort] = [0,0,0,0,0]
        if (amLong-amComb)>0: amShort=amComb*amLong/(amLong-amComb)
        if (mdLong-mdComb)>0: mdShort=mdComb*mdLong/(mdLong-mdComb)
        if (pmLong-pmComb)>0: pmShort=pmComb*pmLong/(pmLong-pmComb)
        if (evLong-evComb)>0: evShort=evComb*evLong/(evLong-evComb)
        if (eaLong-eaComb)>0: eaShort=eaComb*eaLong/(eaLong-eaComb)
        shortLineInst.setFreqs([amShort,mdShort,pmShort,evShort,eaShort])
    
##    def setFastTripsNodes(self):
##        for line in self.lines:
##            if not isinstance(line, TransitLine):
##                continue
##            for n in line.n:
##                if not isinstance(n, Node):
##                    continue
                
    def getCombinedFreq(self, names, coverage_set=False):
        """
        Pass a regex pattern, we'll show the combined frequency.  This
        doesn't change anything, it's just a useful tool.
        """
        lines = self.line(names)
        denom = [0,0,0,0,0]
        for l in lines:
            if coverage_set: coverage_set.discard(l.name)
            freqs = l.getFreqs()
            for t in range(5):
                if float(freqs[t])>0.0:
                    denom[t] += 1/float(freqs[t])
        
        combined = [0,0,0,0,0]
        for t in range(5):
            if denom[t] > 0: combined[t] = round(1/denom[t],2)
        return combined

    def verifyTransitLineFrequencies(self, frequencies, coverage=None):
        """
        Utility function to verify the frequencies are as expected.

         * *frequencies* is a dictionary of ``label => [ regex1, regex2, [freqlist] ]``
         * *coverage* is a regex string (not compiled) that says we want to know if we verified the
           frequencies of all of these lines.  e.g. ``MUNI*``

        """
        covset = set([])
        if coverage:
            covpattern = re.compile(coverage)
            for i in range(len(self.lines)):
                if isinstance(self.lines[i],str): continue
                if covpattern.match(self.lines[i].name): covset.add(self.lines[i].name)
            # print covset
            
        labels = frequencies.keys(); labels.sort()
        for label in labels:
            logstr = "Verifying %-40s: " % label
            
            for regexnum in [0,1]:
                frequencies[label][regexnum]=frequencies[label][regexnum].strip()
                if frequencies[label][regexnum]=="": continue
                pattern = re.compile(frequencies[label][regexnum])
                freqs = self.getCombinedFreq(pattern, coverage_set=covset)
                if freqs[0]+freqs[1]+freqs[2]+freqs[3]+freqs[4]==0:
                    logstr += "-- Found no matching lines for pattern [%s]" % (frequencies[label][regexnum])
                for timeperiod in range(5):
                    if abs(freqs[timeperiod]-frequencies[label][2][timeperiod])>0.2:
                        logstr += "-- Mismatch. Desired %s" % str(frequencies[label][2])
                        logstr += "but got ",str(freqs)
                        lines = self.line(pattern)
                        WranglerLogger.error(logstr)
                        WranglerLogger.error("Problem lines:")
                        for line in lines: WranglerLogger.error(str(line))
                        raise NetworkException("Mismatching frequency")
                logstr += "-- Match%d!" % (regexnum+1)
            WranglerLogger.debug(logstr)
            
        if coverage:
            WranglerLogger.debug("Found %d uncovered lines" % len(covset))
            for linename in covset:
                WranglerLogger.debug(self.line(linename))


    def write(self, path='.', name='transit', writeEmptyFiles=True, suppressQuery=False, suppressValidation=False,
              cubeNetFileForValidation=None):
        """
        Write out this full transit network to disk in path specified.
        """
        if not suppressValidation:
            self.validateWnrsAndPnrs()
            
            if not cubeNetFileForValidation:
                WranglerLogger.fatal("Trying to validate TransitNetwork but cubeNetFileForValidation not passed")
                exit(2)
            
            self.checkValidityOfLinks(cubeNetFile=cubeNetFileForValidation)

        
        if not os.path.exists(path):
            WranglerLogger.debug("\nPath [%s] doesn't exist; creating." % path)
            os.mkdir(path)

        else:
            trnfile = os.path.join(path,name+".lin")
            if os.path.exists(trnfile) and not suppressQuery:
                print "File [%s] exists already.  Overwrite contents? (y/n/s) " % trnfile
                response = raw_input("")
                WranglerLogger.debug("response = [%s]" % response)
                if response == "s" or response == "S":
                    WranglerLogger.debug("Skipping!")
                    return

                if response != "Y" and response != "y":
                    exit(0)

        WranglerLogger.info("Writing into %s\\%s" % (path, name))
        logstr = ""
        if len(self.lines)>0 or writeEmptyFiles:
            logstr += " lines"
            f = open(os.path.join(path,name+".lin"), 'w');
            f.write(";;<<Trnbuild>>;;\n")
            for line in self.lines:
                if isinstance(line,str): f.write(line)
                else: f.write(repr(line)+"\n")
            f.close()

        if len(self.links)>0 or writeEmptyFiles:
            logstr += " links"
            f = open(os.path.join(path,name+".link"), 'w');
            for link in self.links:
                f.write(str(link)+"\n")
            f.close()

        if len(self.pnrs)>0 or writeEmptyFiles:
            logstr += " pnr"
            f = open(os.path.join(path,name+".pnr"), 'w');
            for pnr in self.pnrs:
                f.write(str(pnr)+"\n")
            f.close()

        if len(self.zacs)>0 or writeEmptyFiles:
            logstr += " zac"
            f = open(os.path.join(path,name+".zac"), 'w');
            for zac in self.zacs:
                f.write(str(zac)+"\n")
            f.close()

        if len(self.accessli)>0 or writeEmptyFiles:
            logstr += " access"
            f = open(os.path.join(path,name+".access"), 'w');
            for accessli in self.accessli:
                f.write(str(accessli)+"\n")
            f.close()
        
        if len(self.xferli)>0 or writeEmptyFiles:
            logstr += " xfer"
            f = open(os.path.join(path,name+".xfer"), 'w');
            for xferli in self.xferli:
                f.write(str(xferli)+"\n")
            f.close()
            
        # fares
        for farefile in TransitNetwork.FARE_FILES:
            # don't write an empty one unless there isn't anything there
            if len(self.farefiles[farefile]) == 0:
                if writeEmptyFiles and not os.path.exists(os.path.join(path,farefile)):
                    logstr += " " + farefile
                    f = open(os.path.join(path,farefile), 'w')
                    f.write("; no fares known\n")
                    f.close()

            else:
                logstr += " " + farefile
                f = open(os.path.join(path,farefile), 'w')
                for line in self.farefiles[farefile]:
                    f.write(line)
                f.close()

        logstr += "... done."
        WranglerLogger.debug(logstr)
        WranglerLogger.info("")

    def parseAndPrintTransitFile(self, trntxt, production="transit_file", verbosity=1):
        """
        Verbosity=1: 1 line per line summary
        Verbosity=2: 1 line per node
        """
        if trntxt.strip() in ["; no fares known", "; no known fares", ";no fares known", ";no known fares"]:
            WranglerLogger.debug(trntxt)
            return [], [], [], [], [], [], [], [], []
        
        success, children, nextcharacter = self.parser.parse(trntxt, production=production)
        if not nextcharacter==len(trntxt):
            errorstr  = "\n   Did not successfully read the whole file; got to nextcharacter=%d out of %d total" % (nextcharacter, len(trntxt))
            errorstr += "\n   Did read %d lines, next unread text = [%s]" % (len(children), trntxt[nextcharacter:nextcharacter+50])
            raise NetworkException(errorstr)

        # Convert from parser-tree format to in-memory transit data structures:
        convertedLines = self.parser.convertLineData()
        convertedLinks = self.parser.convertLinkData()
        convertedPNR   = self.parser.convertPNRData()
        convertedZAC   = self.parser.convertZACData()
        convertedAccessLinki = self.parser.convertLinkiData("access")
        convertedXferLinki   = self.parser.convertLinkiData("xfer")
        convertedODFares     = self.parser.convertODFareData()
        convertedXFFares     = self.parser.convertXFFareData()
        convertedFarelinksFares = self.parser.convertFarelinksFareData()
            
        return convertedLines, convertedLinks, convertedPNR, convertedZAC, \
            convertedAccessLinki, convertedXferLinki, convertedODFares, convertedXFFares, \
            convertedFarelinksFares

    def parseSupplinks(self, trntxt, production="transit_file",verbosity=1):
        """
        Verbosity=1: 1 line per line summary
        Verbosity=2: 1 line per node
        """
        if trntxt.strip() in ["; no fares known", "; no known fares", ";no fares known", ";no known fares"]:
            WranglerLogger.debug(trntxt)
            return []

        success, children, nextcharacter = self.parser.parse(trntxt, production=production)
        if not nextcharacter==len(trntxt):
            errorstr  = "\n   Did not successfully read the whole file; got to nextcharacter=%d out of %d total" % (nextcharacter, len(trntxt))
            errorstr += "\n   Did read %d lines, next unread text = [%s]" % (len(children), trntxt[nextcharacter:nextcharacter+50])
            raise NetworkException(errorstr)
        
        convertedSupplinks   = self.parser.convertSupplinksData()
        return convertedSupplinks
        
    def parseFile(self, fullfile, insert_replace=True):
        """
        fullfile is the filename,
        insert_replace=True if you want to replace the data in place rather than appending
        """
        suffix = fullfile.rsplit(".")[-1].lower()
        self.parseFileAsSuffix(fullfile,suffix,insert_replace)
        
    def parseFileAsSuffix(self,fullfile,suffix,insert_replace):
        """
        This is a little bit of a hack, but it's meant to allow us to do something
        like read an xfer file as an access file...
        """
        production = "fare_file" if suffix == "fare" else "transit_file"
        self.parser = TransitParser(transit_file_def, verbosity=0)
        self.parser.tfp.liType = suffix
        logstr = "   Reading %s as %s" % (fullfile, suffix)
        f = open(fullfile, 'r');
        lines,links,pnr,zac,accessli,xferli,od_fares,xf_fares,farelinks_fares = self.parseAndPrintTransitFile(f.read(), production=production, verbosity=0)
        f.close()
        logstr += self.doMerge(fullfile,lines,links,pnr,zac,accessli,xferli,od_fares,xf_fares,farelinks_fares,insert_replace)
        WranglerLogger.debug(logstr)
            
    def doMerge(self,path,lines,links,pnrs,zacs,accessli,xferli,od_fares,xf_fares,farelinks_fares,insert_replace=False):
        """
        Merge a set of transit lines & support links with this network's transit representation.
        """

        logstr = " -- Merging"

        if len(lines)>0:
            logstr += " %s lines" % len(lines)

            extendlines = copy.deepcopy(lines)
            for line in lines:
                if isinstance(line,TransitLine) and (line in self.lines):
                    # logstr += " *%s" % (line.name)
                    if insert_replace:
                        self.lines[self.lines.index(line)]=line
                        extendlines.remove(line)
                    else:
                        self.lines.remove(line)

            if len(extendlines)>0:
                # for line in extendlines: print line
                self.lines.extend(["\n;######################### From: "+path+"\n"])
                self.lines.extend(extendlines)

        if len(links)>0:
            logstr += " %d links" % len(links)
            self.links.extend(["\n;######################### From: "+path+"\n"])
            self.links.extend(links)  #TODO: Need to replace existing links

        if len(pnrs)>0:
            logstr += " %d PNRs" % len(pnrs)
            self.pnrs.extend( ["\n;######################### From: "+path+"\n"])
            self.pnrs.extend(pnrs)  #TODO: Need to replace existing PNRs

        if len(zacs)>0:
            logstr += " %d ZACs" % len(zacs)
            self.zacs.extend( ["\n;######################### From: "+path+"\n"])
            self.zacs.extend(zacs)  #TODO: Need to replace existing PNRs
            
        if len(accessli)>0:
            logstr += " %d accesslinks" % len(accessli)
            self.accessli.extend( ["\n;######################### From: "+path+"\n"])
            self.accessli.extend(accessli)

        if len(xferli)>0:
            logstr += " %d xferlinks" % len(xferli)
            self.xferli.extend( ["\n;######################### From: "+path+"\n"])
            self.xferli.extend(xferli)
            
        if len(od_fares)>0:
            logstr += " %d od_fares" % len(od_fares)
            self.od_fares.extend( ["\n;######################### From: "+path+"\n"])
            self.od_fares.extend(od_fares)

        if len(xf_fares)>0:
            logstr += " %d od_fares" % len(xf_fares)
            self.xf_fares.extend( ["\n;######################### From: "+path+"\n"])
            self.xf_fares.extend(xf_fares)

        if len(farelinks_fares)>0:
            logstr += " %d farelinks_fares" % len(farelinks_fares)
            self.farelinks_fares.extend( ["\n;######################### From: "+path+"\n"])
            self.farelinks_fares.extend(farelinks_fares)


        logstr += "...done."
        return logstr

    def mergeDir(self,path,insert_replace=False):
        """
        Append all the transit-related files in the given directory.
        Does NOT apply __init__.py modifications from that directory.
        """
        dirlist = os.listdir(path)
        dirlist.sort()
        WranglerLogger.debug("Path: %s" % path)

        for filename in dirlist:
            suffix = filename.rsplit(".")[-1].lower()
            if suffix in ["lin","link","pnr","zac","access","xfer","fare"]:
                production = "fare_file" if suffix == "fare" else "transit_file"
                self.parser = TransitParser(transit_file_def, verbosity=0)
                self.parser.tfp.liType = suffix
                fullfile = os.path.join(path,filename)
                logstr = "   Reading %s" % filename
                f = open(fullfile, 'r');
                lines,links,pnr,zac,accessli,xferli,od_fares,xf_fares,farelinks_fares = self.parseAndPrintTransitFile(f.read(), production=production, verbosity=0)
                f.close()
                logstr += self.doMerge(fullfile,lines,links,pnr,zac,accessli,xferli,od_fares,xf_fares,farelinks_fares,insert_replace)
                WranglerLogger.debug(logstr)
                
    def mergeSupplinks(self,path,walk_am_only=True):
        dirlist = os.listdir(path)
        dirlist.sort()
        WranglerLogger.debug("Path: %s" % path)

        for filename in dirlist:
            total_supplinks = 0
            suffix = filename.rsplit('.')[-1].lower()
            if suffix == 'dat':
                self.parser = TransitParser(transit_file_def, verbosity=0)
                self.parser.tfp.liType = suffix
                logstr = "   Reading %s" % filename
                f = open(os.path.join(path,filename))
                tp = filename[:2].upper()
                supplinks = self.parseSupplinks(f.read(),production='transit_file',verbosity=0)
                # only need to get walk supplinks for AM since they are the same in all time periods.
                if walk_am_only and tp != "AM":
                    walk_removed = []
                    for s in supplinks:
                        if isinstance(s,Supplink):
                            if s.isWalkAccess() or s.isWalkEgress() or s.isWalkFunnel(): continue
                            walk_removed.append(s)
                    WranglerLogger.debug("Skipped %d of %d supplinks in %s" % (len(supplinks)-len(walk_removed),len(supplinks),filename))
                    supplinks = walk_removed
                if tp not in self.supplinks.keys(): self.supplinks[tp] = []
                self.supplinks[tp].extend(supplinks)
                total_supplinks += len(supplinks)
                WranglerLogger.debug("added %7d new supplinks, total %7d supplinks" % (len(supplinks),total_supplinks))

    def getFastTripsSupplinks(self, walkskims, nodeToTaz, maxTaz, hwyskims, pnrNodeToTaz):
        '''
        inputs: 
            walkskims:   WalkSkim object
            nodeToTaz:  dict of node -> taz
            maxTaz:     highest node number that is a taz
            hwyskims:   dict of timeperiod -> HighwaySkim object
        '''
        got_node_to_node_xfers = [] # list of (from_node, to_node) transfer pairs
        counter = 0
        total_supplinks = 0
        for tp in WranglerLookups.ALL_TIMEPERIODS:
            total_supplinks += len(self.supplinks[tp])
            
        for tp in WranglerLookups.ALL_TIMEPERIODS:
            for supplink in self.supplinks[tp]:
                counter += 1
                if isinstance(supplink, Supplink):
                    ftsupp = None
                    if supplink.isWalkAccess():
##                        if (supplink.Anode, supplink.Bnode) in self.fasttrips_walk_supplinks.keys():
##                            continue
                        try:
                            ftsupp = FastTripsWalkSupplink(walkskims=walkskims,nodeToTaz=nodeToTaz,
                                                           maxTaz=maxTaz, template=supplink)
                        except NetworkException as e:
                            WranglerLogger.debug(str(e))
                            WranglerLogger.debug("Skipping walk access supplink (%d,%d)" % (supplink.Anode,supplink.Bnode))
                            continue
                        self.fasttrips_walk_supplinks[(ftsupp.Anode,ftsupp.Bnode)] = ftsupp
                    elif supplink.isWalkEgress():
                        pass
                    elif supplink.isWalkFunnel():
                        for k, s in self.fasttrips_walk_supplinks.iteritems():
                            if k[1] == supplink.Anode:
                                s.setSupportFlag(True)
                                ftsupp = copy.deepcopy(s)
                                ftsupp.Bnode = supplink.Bnode
                                ftsupp.stop_id = supplink.Bnode
                                ftsupp.setSupportFlag(False)
                        if ftsupp:
                            if (ftsupp.Anode,ftsupp.Bnode) in self.fasttrips_walk_supplinks.keys():
                                WranglerLogger.warn("(%d-(%d)-%d) already exists in walk_access_supplinks" % (ftsupp.Anode,supplink.Anode,ftsupp.Bnode))
                                continue
                            self.fasttrips_walk_supplinks[(ftsupp.Anode,ftsupp.Bnode)] = ftsupp
                        else:
                            continue
                    elif supplink.isDriveFunnel() or supplink.isTransitTransfer():
                        if (supplink.Anode, supplink.Bnode) in got_node_to_node_xfers:
                            continue
                        got_node_to_node_xfers.append((supplink.Anode,supplink.Bnode))
                        from_lines, to_lines = [],[]
                        for line in self.lines:
                            if isinstance(line, TransitLine):
                                stop_list = line.getStopList()
                                ##WranglerLogger.debug("%s" % str(stop_list))
                                if (supplink.Anode in stop_list) and (line.name not in from_lines): from_lines.append(line.name)
                                if (supplink.Bnode in stop_list) and (line.name not in to_lines): to_lines.append(line.name)
                        for from_line in from_lines:
                            for to_line in to_lines:
                                try:
                                    ftsupp = FastTripsTransferSupplink(walkskims=walkskims,nodeToTaz=nodeToTaz,
                                                                       maxTaz=maxTaz, from_route_id=from_line, to_route_id=to_line,
                                                                       template=supplink)
                                except NetworkException as e:
                                    WranglerLogger.debug(str(e))
                                    WranglerLogger.debug("Skipping walk access supplink (%d,%d)" % (supplink.Anode,supplink.Bnode,from_route_id,to_route_id))
                                    continue
                            
                                self.fasttrips_transfer_supplinks[(ftsupp.Anode,ftsupp.Bnode,ftsupp.from_route_id,ftsupp.to_route_id)] = ftsupp
                            
                    elif supplink.isDriveAccess() or supplink.isDriveEgress():
##                        if (supplink.Anode,supplink.Bnode,tp) in self.fasttrips_drive_supplinks.keys():
##                            continue
                        ftsupp = FastTripsDriveSupplink(hwyskims=hwyskims, pnrNodeToTaz=pnrNodeToTaz, tp=tp, template=supplink)
                        self.fasttrips_drive_supplinks[(ftsupp.Anode,ftsupp.Bnode,tp)] = ftsupp
                    else:
                        WranglerLogger.debug('unknown supplink type %s' % str(supplink))
                if counter % 10000 == 0:
                    WranglerLogger.debug("processed %7d of %7d records" % (counter,total_supplinks))
        WranglerLogger.debug("processed %7d of %7d records" % (counter,total_supplinks))
        
    @staticmethod
    def initializeTransitCapacity(directory="."):
        TransitNetwork.capacity = TransitCapacity(directory=directory)

    def convertTransitLinesToFastTripsTransitLines(self):
        cols = ['name','agency_id','route_id','champ_direction_id','direction_id']
        data = []
        reverse_lines = []
        for line, idx in zip(self.lines,range(len(self.lines))):
            if isinstance(line, TransitLine):
                newline = FastTripsTransitLine(name=line.name,template=line)
                self.lines[idx] = newline
                data.append(newline.asList(cols))
                if self.lines[idx].isOneWay():
                    continue
                self.lines[idx].setOneWay()
                reverse_line = copy.deepcopy(self.lines[idx])
                reverse_line.reverse()
                data.append(reverse_line.asList(cols))
                reverse_lines.append(reverse_line)
        self.lines += reverse_lines
        direction_df = pd.DataFrame(data,columns=cols)
        # set direction ids; first get dataframe that will function as lookup for 
        direction_df['direction_id'] = np.nan
        direction_df.loc[direction_df['champ_direction_id'].isin(['O','WB','NB']),'direction_id'] = 0
        direction_df.loc[direction_df['champ_direction_id'].isin(['I','EB','SB']),'direction_id'] = 1
        unassigned = direction_df[pd.isnull(direction_df['direction_id'])]
        grouped = unassigned.groupby(['agency_id','route_id'])

        for name, group in grouped:
            if len(group) > 2:
                raise NetworkException('%s (%s) trying to assign direction id to route with more than 2 directions' % (name[1], group['name']))
            elif len(group) > 1:
                WranglerLogger.debug('%s (%s) setting direction_id = 0' % (name[1], group.loc[group.index[0],'name']))
                WranglerLogger.debug('%s (%s) setting direction_id = 1' % (name[1], group.loc[group.index[1],'name']))
                direction_df.loc[group.index[0],'direction_id'] = 0
                direction_df.loc[group.index[1],'direction_id'] = 1
            else:
                WranglerLogger.debug('%s (%s) only one direction, setting direction_id = 0' % (name[1], group['name']))
                direction_df.loc[group.index[0],'direction_id'] = 0

        direction_df.to_csv('direction_lookup.csv')
        # check validity of lines
        for line in self.lines:
            if not isinstance(line, FastTripsTransitLine) and not isinstance(line, str):
                raise NetworkException('failed to convert')
            if isinstance(line, FastTripsTransitLine):
                direction_id = direction_df.loc[(direction_df['agency_id']==line.agency_id) & (direction_df['name']==line.name),'direction_id'].irow(0)
##                if not isinstance(direction_id,int):
##                    print line.agency_id, line.name
##                    print direction_id
##                    print direction_df.loc[(direction_df['agency_id']==line.agency_id) & (direction_df['name']==line.name)]['direction_id'][0]
##                    sys.exit()
                line.setDirectionId(direction_id)
            
    def makeFarelinksUnique(self):
        '''
        This is a function added for fast-trips.
        It replaces non-unique FarelinksFares (those with multiple links or modes) and replaces them with a set of
        unique Farelinks that cover all link-mode combinations in the original.
        '''
        # for FarelinksFares where more than one link and more than one mode may be included, get uniqure link/modes
        farelinks = self.farelinks_fares
        orig_len = len(farelinks)
        to_pop = []
        verbosity = 0
        for fare, i in zip(farelinks,range(len(farelinks))):
            if isinstance(fare, FarelinksFare):
                if verbosity == 1:
                    WranglerLogger.debug("checking FarelinksFare for uniqueness.")
                    WranglerLogger.debug("%s" % str(fare))
                new_fare_list = fare.uniqueFarelinksToList()
                new_fare_list.reverse()
                
                if len(new_fare_list) > 1:
                    if verbosity == 1: WranglerLogger.debug("This FarelinksFare is not unique. Replacing...")
                    to_pop.append(i)
                    for new_fare in new_fare_list:
                        if verbosity == 1: WranglerLogger.debug("REPLACEMENT FARE (pos %d): %s" % (i, str(new_fare)))
                        farelinks.append(new_fare)
                    if verbosity == 1: WranglerLogger.debug("Removed %s" % str(removed))
        to_pop.sort()
        to_pop.reverse()
        
        for i in to_pop:
            popped = farelinks.pop(i)
        self.farelinks_fares = farelinks

    def addStationNamestoODFares(self,station_lookup):
        '''
        This is a function added for fast-trips.
        Takes a station_lookup dict and adds station names to od fares.
        '''
        for od_fare in self.od_fares:
            if isinstance(od_fare, ODFare):
                if not od_fare.hasStationNames():
                    od_fare.addStationNames(station_lookup)
                Node.addNodeToZone(od_fare.from_node, od_fare.from_name)
                Node.addNodeToZone(od_fare.to_node, od_fare.to_name)
            
    def addXY(self, coord_dict=None):
        '''
        This is a function added for fast-trips.
        takes a dict of node_number to (x,y) and iterates through each TransitLine and Node, adding
        xy-coordinates as attributes to the Node
        '''
        for line in self.lines:
            if isinstance(line, str):
                # then it's just a comment/text line, so pass
                pass
            elif isinstance(line, TransitLine):
                # then we should add coordinates to it.
                for node in line.n:
                    node.addXY(coord_dict)
            else:
                raise NetworkException('Unhandled data type %s in self.lines' % type(line))

        if isinstance(coord_dict, dict):
            for k, v in coord_dict.iteritems():
                self.coord_dict[k] = v

    def addDeparturesFromHeadways(self, psuedo_random=True, offset=0):
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                line.setDeparturesFromHeadways(psuedo_random, offset)
            else:
                raise NetworkException('Unhandled data type %s in self.lines' % type(line))

    def addFirstDeparturesToAllLines(self, psuedo_random=True, offset=0):
        '''
        This is a function added for fast-trips.
        '''
        for line in self.lines:
            if isinstance(line, str):
                # then it's just a comment/text line, so pass
                pass
            elif isinstance(line, TransitLine):
                # then we should add coordinates to it.
                line.setFirstDepartures(psuedo_random=psuedo_random, offset=offset)
            else:
                raise NetworkException('Unhandled data type %s in self.lines' % type(line))

    def map_projectWGS84_to_SPPoint(self, row):
        import pyproj
        import shapely
        from shapely.geometry import Point
        prj_wgs84 = pyproj.Proj("+init=EPSG:4326") # WGS 84
        prj_spca3 = pyproj.Proj("+init=EPSG:2227") # California State Plane III, US Feet
        conv_ft_to_m = 0.3048
        conv_m_to_ft = 1 / conv_ft_to_m
        x, y = pyproj.transform(prj_wgs84, prj_spca3, row['stop_lon'], row['stop_lat'])
        x = x * conv_m_to_ft
        y = y * conv_m_to_ft
        p = Point(x,y)
        return p
        
    def matchLinesToGTFS(self, gtfs_path, dist_threshold = 100, match_threshold=0.85, sort=True):
        import gtfs_utils
        import pyproj
        import shapely
        from shapely.geometry import Point
        
        gtfs = gtfs_utils.GTFSFeed(gtfs_path)
        gtfs.load()
        gtfs.standardize()
        gtfs.build_common_dfs()
        crosswalk = pd.DataFrame(columns=['champ_line_name','route_id','route_short_name','direction_id','pattern_id','match']) # champ_line_name -> gtfsFeed route_id, direction_id, pattern_id
        #buffers = [50,100,150] # in feet
        route_patterns = pd.DataFrame(gtfs.route_patterns,columns=['route_id','route_short_name','route_long_name','direction_id','pattern_id'])
        route_patterns = route_patterns.reset_index()
        gtfs_stop_patterns = pd.merge(route_patterns, gtfs.stop_patterns,left_on='pattern_id',right_on='trip_id')
        gtfs_stop_patterns['point'] = gtfs_stop_patterns.apply(self.map_projectWGS84_to_SPPoint, axis=1)
        
        grouped_gtfs = gtfs_stop_patterns.groupby(['route_id','pattern_id'])
        
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                ft_stop_patterns = line.stopsAsDataFrame()
                tot_match = float(len(ft_stop_patterns))
                has_route_match = False
                if line.agency_id != 'sf_muni':
                    continue
##                if line.name not in ['MUN1I','MUN1O']:
##                    continue
                for name, route_pattern in grouped_gtfs:
                    this_route_match = True
                    max_match = float(len(ft_stop_patterns))
                    f = min(float(len(route_pattern)) / float(len(ft_stop_patterns)), 1.00)
                    if line.name in ['MUN1I','MUN1O'] and name[0] == 7517:
                        #print route_pattern['stop_id'][0:10]
                        #print route_pattern['stop_sequence'][0:10].tolist()
                        WranglerLogger.warn('%s - %s max match = %0.2f' % (line.name, str(name),f))
                    if f < match_threshold:
                        if line.name in ['MUN1I','MUN1O'] and name[0] == 7517:
                            WranglerLogger.warn('%s skipping %s because max match (type 1) = %0.2f' % (line.name, str(name),f))
                        continue
                    else:
                        if line.name in ['MUN1I','MUN1O'] and name[0] == 7517:
                            WranglerLogger.warn('%s searching for matches' % line.name)
                    if max_match / tot_match < match_threshold:
                        if line.name in ['MUN1I','MUN1O'] and name[0] == 7517:
                            WranglerLogger.warn('%s skipping %s because max match (type 2) = %0.2f' % (line.name, str(name),(max_match/tot_match)))
                        continue
                    if sort:
                        route_pattern = route_pattern.sort('stop_sequence').reset_index()
                    last_idx = 0
                    for ft_idx, ft_row in ft_stop_patterns.iterrows():
                        ftp = Point(ft_row['x'],ft_row['y'])
                        has_stop_match = False
                        if line.name == 'MUN1O' and name[0] == 7517:
                            WranglerLogger.debug('idx: %s, recs: %d' % (last_idx, len(route_pattern[last_idx:])))
                        for gt_idx, gt_row in route_pattern[last_idx:].iterrows():
                            gtp = gt_row['point']
                            if line.name == 'MUN1O' and name[0] == 7517:
                                WranglerLogger.debug('(%d,%d), (%d, %d)  %0.2f' % (ftp.x, ftp.y, gtp.x, gtp.y, ftp.distance(gtp)))
                            if ftp.distance(gtp) <= dist_threshold:
                                if line.name == 'MUN1O' and name[0] == 7517:
                                    WranglerLogger.debug('match! (%d,%d), (%d, %d)  %0.2f' % (ftp.x, ftp.y, gtp.x, gtp.y, ftp.distance(gtp)))
                                has_stop_match = True
                                last_idx = gt_idx
                                break
                        if not has_stop_match:
                            max_match -= 1.0
                        if max_match/tot_match < match_threshold:
                            this_route_match = False
                            break
                    if this_route_match:
                        has_route_match = True
                        crosswalk = crosswalk.append(pd.DataFrame([[line.name,gt_row['route_id'],gt_row['route_short_name'],gt_row['direction_id'],gt_row['pattern_id'],max_match]],
                                                                  columns=['champ_line_name','route_id','route_short_name','direction_id','pattern_id','match']))
                        WranglerLogger.debug('%s found match in gtfs %s  %s  %s  %s  %0.2f' % (line.name, gt_row['route_id'],gt_row['route_short_name'],gt_row['direction_id'],gt_row['pattern_id'],(max_match/tot_match)))
                        
                if has_route_match and max_match >= match_threshold:
##                    crosswalk.loc[
##                    crosswalk.loc[line.name,'route_short_name'].tolist()
                    WranglerLogger.debug('%s found match in gtfs %s  %s  %s  %s  %0.2f' % (line.name, gt_row['route_id'],gt_row['route_short_name'],gt_row['direction_id'],gt_row['pattern_id'],(max_match/tot_match)))
                else:
                    WranglerLogger.debug('%s no match found in gtfs' % line.name)
                
            else:
                raise NetworkException("invalid type found in transit_network.lines: %s" % str(line))
        crosswalk.to_csv('found_crosswalk.csv')
        
    def addDeparturesFromGTFS(self, gtfs_path, crosswalk):
        import gtfs_utils
        gtfs = gtfs_utils.GTFSFeed(gtfs_path)
        gtfs.load()
        gtfs.build_common_dfs()
        crosswalk = pd.read_csv(crosswalk)
        gtfs.route_trips.to_csv('route_trips.csv')
        
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                list_of_pattern_ids = crosswalk[crosswalk['CHAMP ROUTE ID']==line.name]['pattern_id'].drop_duplicates().tolist()
                list_of_departure_times = gtfs.route_trips[gtfs.route_trips['pattern_id'].isin(list_of_pattern_ids)]['trip_departure_mpm'].tolist()
                if len(list_of_departure_times) == 0:
                    WranglerLogger.warn("ROUTE ID %s: No GTFS departure times for, calculating from headways" % line.name)
                    line.setDeparturesFromHeadways()
                    WranglerLogger.warn("ROUTE ID %s: added %d departures" % (line.name, len(line.all_departure_times)))
                else:
                    WranglerLogger.debug("ROUTE ID %s: Setting departure times from GTFS" % line.name)
                    line.setDepartures(list_of_departure_times)
                            
    def addTravelTimes(self, highway_networks):
        '''
        This is a function added for fast-trips.
        Takes a dict of links_dicts, with one links_dict for each time-of-day

            highway_networks[tod] -> tod_links_dict
            tod_links_dict[(Anode,Bnode)] -> (distance, streetname, bustime)

        For each TransitLine, sets link travel times.
        '''
        for line in self.lines:
            if isinstance(line, str):
                # then it's just a comment/text line, so pass
                pass
            elif isinstance(line, TransitLine):
                # then we should add coordinates to it.
                line.setTravelTimes(highway_networks, self.links)
            else:
                raise NetworkException('Unhandled data type %s in self.lines' % type(line))

    def createFastTrips_PNRs(self, coord_dict):
        for pnr in self.pnrs:
            if isinstance(pnr, PNRLink):
                if not isinstance(pnr.pnr, int):
                    pnr_nodenum = int(pnr.station)
                else:
                    pnr_nodenum = int(pnr.pnr)
                    #WranglerLogger.warn("Non-integer pnr node %s for pnr" % (str(pnr.pnr)
                n = FastTripsNode(pnr_nodenum, coord_dict)
                self.fasttrips_pnrs[pnr_nodenum] = n
        
    def createFastTrips_Agencies(self):
        agency_data = []
        for line in self.lines:
            if isinstance(line,str): continue
            if not isinstance(line,FastTripsTransitLine): continue
            if line.agency_id in WranglerLookups.OPERATOR_NAME_TO_URL.keys():
                agency_url = WranglerLookups.OPERATOR_NAME_TO_URL[line.agency_id]
            else:
                agency_url = 'https://www.%s.com/' % line.agency_id
            data = [line.agency_id,line.agency_id,agency_url,self.fasttrips_timezone]
            if line.agency_id in self.fasttrips_agencies.keys() and data != self.fasttrips_agencies[line.agency_id]:
                WranglerLogger.warn('MISMATCH BETWEEN EXISTING AND EXPECTED AGENCY DATA FOR %s' % line.agency_id)
                WranglerLogger.warn('%s\t\t%s' % (str(self.fasttrips_agencies[line.agency_id]), str(data)))
            self.fasttrips_agencies[line.agency_id] = data

    def createFastTrips_Calendar(self, days='MTWThFSaSu', start_date='20150101', end_date='20151231'):
        if (self.fasttrips_agencies) == 0:
            self.createFastTrips_Agencies()
            
        monday, tuesday, wednesday, thursday, friday, saturday, sunday = 0,0,0,0,0,0,0
        if re.search('M|m',days):
            monday=1
        if re.search('T(?!h)|t(?!h)|T(?!H)',days):
            tuesday=1
        if re.search('W|w',days):
            wednesday=1
        if re.search('Th|TH|th',days):
            thursday=1
        if re.search('F|f',days):
            friday=1
        if re.search('Sa|SA|sa',days):
            saturday=1
        if re.search('Su|SU|su',days):
            sunday=1
        if not (monday or tuesday or wednesday or thursday or friday or saturday or sunday):
            raise NetworkException("No valid days in the calendar for %s" % str(days))
        bin_days = '%d%d%d%d%d%d%d' % (monday, tuesday, wednesday, thursday, friday, saturday, sunday)
        if bin_days == '1111100':
            service = 'weekday'
        elif bin_days == '0000011':
            service = 'weekend'
        else:
            service = days
        for agency in self.fasttrips_agencies.keys():            
            self.fasttrips_calendar[agency+'_'+service] = [agency+'_'+service,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date]
            
    def writeFastTrips_Calendar(self, f='calendar.txt', path='.', writeHeaders=True):
        if len(self.fasttrips_calendar) == 0:
            self.createFastTrips_Calendar(days='MTWThF')
            
        df_calendar = pd.DataFrame(data=self.fasttrips_calendar.values(),columns=['service_id','monday','tuesday',
                                                                                  'wednesday','thursday','friday',
                                                                                  'saturday','sunday',
                                                                                  'start_date','end_date'])
        df_calendar.to_csv(os.path.join(path,f),index=False,headers=writeHeaders)
    
    def writeFastTrips_Agencies(self, f='agency.txt', path='.', writeHeaders=True):
        if len(self.fasttrips_agencies) == 0:
            self.createFastTrips_Agencies()
        
        df_agency = pd.DataFrame(columns=['agency_id','agency_name','agency_url','agency_timezone'],data=self.fasttrips_agencies.values())
        df_agency.to_csv(os.path.join(path,f),index=False,headers=writeHeaders)

    def writeFastTrips_PNRs(self, f='drive_access_points_ft.txt', path='.', writeHeaders=True):
        df_pnrs = None
        pnr_data = []
        for pnr in self.fasttrips_pnrs.values():
            if not isinstance(pnr, FastTripsNode): continue
            data = pnr.asList(['stop_id','stop_lat','stop_lon'])
            pnr_data.append(data)
        df_pnrs = pd.DataFrame(columns=['lot_id','lot_lat','lot_lon'],data=pnr_data)
        df_pnrs = df_pnrs.drop_duplicates()
        df_pnrs.to_csv(os.path.join(path, f),index=False, headers=['lot_id','lot_lat','lot_lon'])
        
    def writeFastTrips_Vehicles(self, f='vehicles_ft.txt', path='.', writeHeaders=True):
        vehicles = []
        df_vehicles = None
        for line in self.lines:
            if isinstance(line,str): continue
            if not isinstance(line,TransitLine): continue
            for vtype in line.vehicle_types.itervalues():
                if vtype not in vehicles:
                    values = [vtype,20,int(self.capacity.vehicleTypeToCapacity[vtype])-20]
                    df_row = pd.DataFrame(columns=['vehicle_name','seated_capacity','standing_capacity'],
                                          data=[values])
                    if not isinstance(df_vehicles,pd.DataFrame):
                        df_vehicles = df_row
                    else:
                        df_vehicles = df_vehicles.append(df_row)
                    vehicles.append(vtype)
        df_vehicles.to_csv(os.path.join(path,f),index=False,headers=writeHeaders)

    def writeFastTrips_Access(self, f_walk='walk_access_ft.txt', f_drive='drive_access_ft.txt', f_transfer='transfers.txt', f_transfer_ft='transfers_ft.txt', path='.', writeHeaders=True):
        df_walk = None
        df_drive = None
        df_transfer = None
        walk_data = []
        drive_data = []
        transfer_data = []
        walk_columns = ['taz','stop_id','dist','elevation_gain','population_density','employment_density','auto_capacity','indirectness']
        drive_columns = ['taz','lot_id','direction','dist','cost','travel_time','start_time','end_time']
        transfer_keys = ['from_stop_id','to_stop_id']
        transfer_columns = ['transfer_type','min_transfer_time']
        transfer_ft_columns = ['dist','from_route_id','to_route_id','schedule_precedence']
        
        for supplink in self.fasttrips_walk_supplinks.values():
            if supplink.support_flag: continue
            try:
                slist = supplink.asList(walk_columns)
                walk_data.append(slist)
            except Exception as e:
                WranglerLogger.warn(str(e))

        for supplink in self.fasttrips_drive_supplinks.values():
            if supplink.support_flag: continue
            try:
                slist = supplink.asList(drive_columns)
                drive_data.append(slist)
            except Exception as e:
                WranglerLogger.warn(str(e))

        for supplink in self.fasttrips_transfer_supplinks.values():
            if supplink.support_flag: continue
            try:
                transfer_data.append(supplink.asList(transfer_keys+transfer_columns+transfer_ft_columns))
            except Exception as e:
                WranglerLogger.warn(str(e))

        if len(walk_data) > 0:
            df_walk = pd.DataFrame(columns=walk_columns, data=walk_data)
            df_walk = df_walk.drop_duplicates()
        else:
            df_walk = pd.DataFrame(columns=walk_columns)

        if len(drive_data) > 0:
            df_drive = pd.DataFrame(columns=drive_columns, data=drive_data)
            df_drive = df_drive.drop_duplicates()
        else:
            df_drive = pd.DataFrame(columns=drive_columns)

        if len(transfer_data) > 0:
            df_transfer = pd.DataFrame(columns=transfer_keys+transfer_columns+transfer_ft_columns, data=transfer_data)
            df_transfer = df_transfer.drop_duplicates()
        else:
            df_transfer = pd.DataFrame(columns=transfer_columns)

        df_transfer_ft = pd.DataFrame(data=df_transfer,columns=transfer_keys+transfer_ft_columns)
        df_transfer = pd.DataFrame(data=df_transfer,columns=transfer_keys+transfer_columns)
        
        df_walk.to_csv(os.path.join(path,f_walk),index=False,headers=writeHeaders)
        df_drive.to_csv(os.path.join(path,f_drive),index=False,headers=writeHeaders)
        df_transfer.to_csv(os.path.join(path,f_transfer),index=False,headers=writeHeaders)
        df_transfer_ft.to_csv(os.path.join(path,f_transfer_ft),index=False,headers=writeHeaders)
            
    def writeFastTrips_Shapes(self, f='shapes.txt', path='.', writeHeaders=True):
        '''
        this is a funtion added for fast-trips.
        Iterate each line in this TransitNetwork and write fast-trips style shapes.txt to f
        '''
        f = openFileOrString(os.path.join(path,f))
        count = 0
        # go through lines and write them to f.
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                line.writeFastTrips_Shape(f, writeHeaders)
                writeHeaders = False # only write them the with the first line.
                count += 1
            else:
                WranglerLogger.debug("skipping line because unknown type")
        print "wrote %d lines" % count

    def writeFastTrips_Trips(self, f_trips='trips.txt', f_trips_ft='trips_ft.txt',
                             f_stoptimes='stop_times.txt', f_stoptimes_ft='stop_times_ft.txt', path='.', writeHeaders=True):
        '''
        This is a function added for fast-trips.
        Iterate each line in this TransitNetwork and write fast-trips style stop_times.txt fo f
        This requires that each line has a complete set of links with ``BUSTIME_<TOD>`` for each
        <TOD> in ``AM``, ``MD``, ``PM``, ``EV``, ``EA``.
        '''
        f_trips     = openFileOrString(os.path.join(path,f_trips))
        f_trips_ft  = openFileOrString(os.path.join(path,f_trips_ft))
        f_stoptimes = openFileOrString(os.path.join(path,f_stoptimes))
        f_stoptimes_ft = openFileOrString(os.path.join(path,f_stoptimes_ft))
        id_generator = generate_unique_id(range(1,999999))
        
        # go through lines and write them to f.
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                line.writeFastTrips_Trips(f_trips, f_trips_ft, f_stoptimes, f_stoptimes_ft, id_generator, writeHeaders)
                writeHeaders = False # only write them the with the first line.

    def writeFastTrips_Routes(self, f_routes='routes.txt', f_routes_ft='routes_ft.txt', path='.', writeHeaders=True):
        '''
        This is a function added for fast-trips.
        '''
        df_routes       = None
        df_routes_ft    = None

        for line in self.lines:
            if isinstance(line, TransitLine):
                if line.fare_class == None:
                    fc = line.setFareClass()
                    WranglerLogger.debug('%s fare_class set to %s at writeFastTrips_Routes' % (line.name, fc))
                else:
                    WranglerLogger.debug('%s fare_class already set as %s' % (line.name, line.fare_class))
                df_row = line.asDataFrame(columns=['route_id','agency_id','route_short_name','route_long_name','route_type'])
                if not isinstance(df_routes,pd.DataFrame):
                    df_routes = df_row
                else:
                    df_routes = df_routes.append(df_row)
                df_row = line.asDataFrame(['route_id','mode','fare_class','proof_of_payment'])
                if not isinstance(df_routes_ft,pd.DataFrame):
                    df_routes_ft = df_row
                else:
                    df_routes_ft = df_routes_ft.append(df_row)

        #df_routes = df_routes.sort(['agency_id','route_id'])
        df_routes.to_csv(os.path.join(path,f_routes),index=False,header=writeHeaders)
        df_routes_ft.to_csv(os.path.join(path,f_routes_ft),index=False,header=writeHeaders)
        
    def getLeftAndRightTransitNodeNums(self,farelink,stops_only=True):
        '''
        This is a function added for fast-trips.
        Takes a TransitLink, and iterates over each line returning a list of all nodes on either
        side of the link (denoted by left, meaning nodes preceding the link on a line, and right,
        meaning the nodes following the link on a line.  They should be non-overlapping lists.
        '''
        left_nodes = [] # integer list of node numbers that precede the farelink(stops only)
        right_nodes = [] # integer list of node numbers that follow the farelink(stops only)
        
        for line in self.lines:
            if isinstance(line,str):
                continue
            modenum = int(line.attr['MODE'])
            if line.hasLink(farelink.farelink.Anode,farelink.farelink.Bnode) and modenum == int(farelink.mode):
                for n in line.n[:line.getNodeIdx(farelink.farelink.Bnode)]:
                    if isinstance(n, int):
                        node_num = n
                        if node_num < 0 and stops_only: continue
                    elif isinstance(n, Node):
                        node_num = int(n.num)
                        if not n.isStop() and stops_only: continue
                    else:
                        raise NetworkException("Unknown node type n=%s" % str(n))
                    if node_num not in left_nodes:
                        left_nodes.append(node_num)
                        
                for n in line.n[line.getNodeIdx(farelink.farelink.Bnode):]:
                    if isinstance(n, int):
                        node_num = n
                        if node_num < 0 and stops_only: continue
                    elif isinstance(n, Node):
                        node_num = int(n.num)
                        if not n.isStop() and stops_only: continue
                    else:
                        raise NetworkException("Unknown node type n=%s" % str(n))
                    if node_num not in right_nodes:
                        right_nodes.append(node_num)
        return (left_nodes, right_nodes)

    def crossesWall(self, nodes, left_wall, right_wall):
        '''
        This is a function added for fast-trips.
        Determines whether the nodes in nodes are allowed to be in the same zone by
        checking against left_wall and right_wall.  left_wall and right_wall are lists
        of nodes that cannot be in the same zone because they cross a "wall" (i.e. farelink).
        '''
        junk, junk, overlap1 = getListOverlap(nodes, left_wall)
        junk, junk, overlap2 = getListOverlap(nodes, right_wall)
        if len(overlap1) > 0 and len(overlap2) > 0:
            return True
        else:
            return False

    def addAndSplitZoneList(self, zone_list, left_nodes, right_nodes):
        '''
        This is a function added for fast-trips.
        '''
        if len(zone_list) == 0:
            zone_list.append(left_nodes)
            zone_list.append(right_nodes)
            return zone_list
        for nodeset in zone_list:
            idx = zone_list.index(nodeset)
            newsets = boilDown(nodeset,left_nodes,right_nodes)
            if len(newsets) > 1:
                zone_list.remove(nodeset)
            for newset in newsets:
                if len(newset) == 0:
                    WranglerLogger.warn("GOT ZERO LENGTH LIST")
                    continue
                if newset not in zone_list:
                    for set in zone_list:
                        if isSubset(newset, set):
                            newset = []
                            break
                            # don't add, it's already there
                        #elif isSubset(set, newset):
                        else:
                            left, newset, overlap = getListOverlap(set, newset)
                            # add just the part that's missing
                    if len(newset) > 0: zone_list.insert(idx, newset)
                idx += 1
        return zone_list
                                
    def createFarelinksZones(self):
        '''
        This is a function added for fast-trips.
        '''
        # Start with Farelinks
        # gather up sets of left_nodes, right_nodes for each link
        walls = [] # put nodeset pairs in here, where the left nodeset can't be in the same zone as the right nodeset
        id_generator = generate_unique_id(range(1,999999))
        zone_to_nodes = {}
        link_counter = 0
        zone_list = []
        all_nodes = []
        
        for fare in self.farelinks_fares:
            if isinstance(fare, FarelinksFare):
                link_counter += 1
                if link_counter % 10 == 0: print "checked %d links" % link_counter
                if fare.isUnique():
                    (left_nodes, right_nodes) = self.getLeftAndRightTransitNodeNums(fare)
                    if len(left_nodes) == 0 and len(right_nodes) == 0: continue
                    left_nodes.sort()
                    right_nodes.sort()
                    for n in left_nodes:
                        if n not in all_nodes: all_nodes.append(n)
                    for n in right_nodes:
                        if n not in all_nodes: all_nodes.append(n)
                        
                    zone_list = self.addAndSplitZoneList(zone_list, left_nodes, right_nodes)

        found_nodes = []
        
        for nodes in zone_list:
            id = id_generator.next()
            id = str(id)
            zone_to_nodes[id] = nodes
            for n in nodes:
                if n not in found_nodes: found_nodes.append(n)
        WranglerLogger.debug("EXPECT %d TOTAL NODES" % len(all_nodes))
        WranglerLogger.debug("FOUND %d TOTAL NODES" % len(found_nodes))
        missing_nodes, junk, junk = getListOverlap(all_nodes, found_nodes)

        node_to_zone = {}
        for zone, nodes in zone_to_nodes.iteritems():
            for n in nodes:
                if n in node_to_zone.keys():
                    WranglerLogger.warn("DUPLICATE ZONE-NODE PAIR for NODE %d" % n)
                node_to_zone[n] = zone
                
        Node.setNodeToZone(node_to_zone)
        return zone_to_nodes
    
    def addFaresToLines(self):
        '''
        This is a function added for fast-trips.
        '''
        for line in self.lines:
            if isinstance(line, TransitLine):
                line.addFares(od_fares=self.od_fares, xf_fares=self.xf_fares, farelinks_fares=self.farelinks_fares)
                
    def createFastTrips_Fares(self, price_conversion=1):
        '''
        This is a function added for fast-trips.
        '''
        fasttrips_fares = []
        fare_dict = {} # dict of (fare_id,price) -> list of fares.  This will be used to collapse zone fares that currently share a fare_id
        for line in self.lines:
            if isinstance(line,TransitLine):
                fares = line.getFastTripsFares_asList(zone_suffixes=False, price_conversion=price_conversion)  # zone_suffixes=False means that fare_ids will not be unique
                WranglerLogger.debug("GOT %d FAST-TRIPS FARE RULES FOR LINE %s" % (len(fares),line.name))
                for fare in fares:
                    if (fare.fare_id,fare.price) not in fare_dict.keys():
                        fare_dict[(fare.fare_id,fare.price)] = []
                    fare_dict[(fare.fare_id,fare.price)].append(fare)
                    ##if fare not in fasttrips_fares: fasttrips_fares.append(fare)
                    
        # go through each fare, check if identical with another fare on fare_id and price.
        # if so then they will get the same fare_id, although they should still get multiple
        # rules for unique zone-zone combos
        keys = fare_dict.keys()
        keys.sort()
        last_fare_id = None
        i = 1
        for key in keys:
            if key[0] != last_fare_id: i = 1
            last_fare_id = key[0]
            for fare in fare_dict[key]:
                if fare.isZoneFare():
                    fare_suffix = 'Z%d' % i
                elif i > 1:
                    fare_suffix = 'F%d' % i
                else:
                    fare_suffix = None
                    
                fare.setFareId(fare_id=fare.fare_id,suffix=fare_suffix)
                fare.setFareClass()
                fasttrips_fares.append(fare)
                ##WranglerLogger.debug("fare_id: %s" % str(fare.fare_id))
            i += 1
        self.fasttrips_fares = fasttrips_fares

        count = 0
        fare_classes = {} # fare_class -> FastTripsFare
        fare_classes_by_mode = {} # champ modenum -> list of fare_class
        
        for fare in self.fasttrips_fares:
            if fare.fare_class not in fare_classes.keys():
                fare_classes[fare.fare_class] = fare
            if not fare.champ_mode: WranglerLogger.warn("fare %s missing champ mode" % fare.fare_id)
            if fare.champ_mode not in fare_classes_by_mode.keys(): fare_classes_by_mode[fare.champ_mode] = []
            if fare.fare_class not in fare_classes_by_mode[fare.champ_mode]:
                fare_classes_by_mode[fare.champ_mode].append(fare.fare_class)

        for xffare in self.xf_fares:
            if isinstance(xffare, XFFare):
                if not xffare.isTransferType():
                    WranglerLogger.debug("skipping %d to %d because non-transit transfer" % (xffare.from_mode, xffare.to_mode))
                    continue
                if xffare.from_mode not in fare_classes_by_mode.keys() or xffare.to_mode not in fare_classes_by_mode.keys():
                    WranglerLogger.debug("skipping xfer %d to %d because no valid fares found" % (xffare.from_mode, xffare.to_mode))
                    continue
                if xffare.price == 0:
                    WranglerLogger.debug("skipping xfer %d to %d because price is 0" % (xffare.from_mode, xffare.to_mode))
                    continue
                from_classes = len(fare_classes_by_mode[xffare.from_mode])
                to_classes = len(fare_classes_by_mode[xffare.to_mode])
                WranglerLogger.debug("from_classes: %7d, to_classes: %7d, total combinations: %7d" % (from_classes,to_classes,from_classes*to_classes))
                for from_fare in fare_classes_by_mode[xffare.from_mode]:
                    for to_fare in fare_classes_by_mode[xffare.to_mode]:
                        ftfare = FastTripsTransferFare(from_fare_class=from_fare,
                                                       to_fare_class=to_fare,
                                                       from_mode=xffare.from_mode,
                                                       to_mode=xffare.to_mode,
                                                       is_flat_fee=1,
                                                       transfer_rule=xffare.price,
                                                       price_conversion=price_conversion)
                        ##if ftfare not in self.fasttrips_transfer_fares:
                        self.fasttrips_transfer_fares.append(ftfare)
                        count += 1
                        if count % 10000 == 0: WranglerLogger.debug("%7d" % count)
        return fasttrips_fares, self.fasttrips_transfer_fares

    def createFastTrips_Nodes(self):
        '''
        This is a function added for fast-trips.txt

        All stops and stops_ft variables:
        'stop_id','stop_code','stop_name','stop_desc','stop_lat','stop_lon','zone_id','location_type',
        'parent_station','stop_timezone','wheelchair_boarding','shelter','lighting','bike_parking',
        'bike_share_station','seating','platform_height','level','off_board_payment'
        '''
        
        nodes = {} # nodenum (int): Node
        # add all nodes that occur in any line, regardless of whether they are stops. Any nodes
        # that are a stop in one line, and not a stop in another will be duplicated.
        for line in self.lines:
            if isinstance(line,str): continue
            for n in line.n:
                if not isinstance(n,Node):
                    if isinstance(n,int): raise NetworkExcetption('LINE %s HAS INTEGER NODE.  ALL NODES SHOULD BE OF TYPE NODE.' % line.name)
                    continue
                if int(n.num) not in nodes.keys():
                    ft_node = FastTripsNode(int(n.num), {abs(int(n.num)):(n.x,n.y)})
                    nodes[int(n.num)] = ft_node
        self.fasttrips_nodes = nodes
            
    def writeFastTrips_Fares(self,f_farerules='fare_rules.txt',f_farerules_ft='fare_rules_ft.txt',
                             f_fareattr='fare_attributes.txt',f_fareattr_ft='fare_attributes_ft.txt',
                             f_faretransferrules='fare_transfer_rules.txt',
                             path='.', writeHeaders=True, sortFareRules=False):
        df_farerules    = None
        df_farerules_ft = None
        df_fareattrs    = None
        df_fareattrs_ft = None
        df_transfer_rules_data = []
        
        for fare in self.fasttrips_fares:
            df_row = fare.asDataFrame(['fare_id','route_id','origin_id','destination_id','contains_id'])
            if not isinstance(df_farerules, pd.DataFrame):
                df_farerules = df_row
            else:
                df_farerules = df_farerules.append(df_row)
            df_row = fare.asDataFrame(['fare_id','fare_class','start_time','end_time'])
            if not isinstance(df_farerules_ft, pd.DataFrame):
                df_farerules_ft = df_row
            else:
                df_farerules_ft = df_farerules_ft.append(df_row)
            df_row = fare.asDataFrame(['fare_id','price','currency_type','payment_method','transfers','transfer_duration'])
            if not isinstance(df_fareattrs, pd.DataFrame):
                df_fareattrs = df_row
            else:
                df_fareattrs = df_fareattrs.append(df_row)
            df_row = fare.asDataFrame(['fare_class','price','currency_type','payment_method','transfers','transfer_duration'])
            if not isinstance(df_fareattrs_ft, pd.DataFrame):
                df_fareattrs_ft = df_row
            else:
                df_fareattrs_ft = df_fareattrs_ft.append(df_row)

        if sortFareRules:
            df_farerules = df_farerules.drop_duplicates().sort(['fare_id','route_id'])
            df_farerules_ft = df_farerules_ft.drop_duplicates().sort('fare_id')
            df_fareattrs = df_fareattrs.drop_duplicates().sort('fare_id')
            df_fareattrs_ft = df_fareattrs_ft.drop_duplicates().sort('fare_class')
        else:
            df_farerules = df_farerules.drop_duplicates()
            df_farerules_ft = df_farerules_ft.drop_duplicates()
            df_fareattrs = df_fareattrs.drop_duplicates()
            df_fareattrs_ft = df_fareattrs_ft.drop_duplicates()
            
        df_farerules.to_csv(os.path.join(path, f_farerules),index=False,headers=writeHeaders)
        df_farerules_ft.to_csv(os.path.join(path,f_farerules_ft),index=False,headers=writeHeaders)
        df_fareattrs.to_csv(os.path.join(path,f_fareattr),index=False,header=writeHeaders,float_format='%.2f')
        df_fareattrs_ft.to_csv(os.path.join(path, f_fareattr_ft),index=False,header=writeHeaders,float_format='%.2f')

        transfer_columns = ['from_fare_class','to_fare_class','is_flat_fee','transfer_rule']
        transfer_data = []
        
        for fare in self.fasttrips_transfer_fares:
            data = fare.asList(columns=transfer_columns)
            transfer_data.append(data)
            
        df_transfer_rules = pd.DataFrame(columns=transfer_columns, data=transfer_data)
        df_transfer_rules = df_transfer_rules.drop_duplicates()
        df_transfer_rules.to_csv(os.path.join(path,f_faretransferrules),index=False,header=writeHeaders,float_format='%.2f')
    
    def writeFastTrips_Stops(self,f_stops='stops.txt',f_stops_ft='stops_ft.txt',path='.', writeHeaders=True):
        # UNFINISHED
        # MAY NEED TO KNOW ZONES, WHICH WILL COME FROM ODFARES
        '''
        stops:      stop_id, stop_code*, stop_name, stop_desc*, stop_lat, stop_lon, zone_id*, location_type*,
                    parent_station*,stop_timezone*,wheelchair_boarding*
        stops_ft:   stop_id, shelter*, lighting*, bike_parking*, bike_share_station*, seating*, platform_hight*,
                    level*, off_board_payment*
        '''
        df_stops = None
        df_stops_ft = None

        for nodekey, node in self.fasttrips_nodes.iteritems():
            if node.isStop():
                df_row = node.asDataFrame(columns=['stop_id','stop_name','stop_lat','stop_lon','zone_id'])
                if not isinstance(df_stops,pd.DataFrame):
                    df_stops = df_row
                else:
                    df_stops = df_stops.append(df_row)
                df_row = node.asDataFrame(columns=['stop_id'])
                if not isinstance(df_stops_ft,pd.DataFrame):
                    df_stops_ft = df_row
                else:
                    df_stops_ft = df_stops_ft.append(df_row)
        df_stops.to_csv(os.path.join(path,f_stops),index=False,header=writeHeaders)
        df_stops_ft.to_csv(os.path.join(path,f_stops_ft),index=False,header=writeHeaders)
        
    def findSimpleDwellDelay(self, line):
        """
        Returns the simple mode/owner-based dwell delay for the given *line*.  This could
        be a method in :py:class:`TransitLine` but I think it's more logical to be 
        :py:class:`TransitNetwork` specific...
        """
        # use AM to lookup the vehicle
        simpleDwell = TransitNetwork.capacity.getSimpleDwell(line.name, "AM")
        
        owner = None
        if 'OWNER' in line.attr:
            owner = line.attr['OWNER'].strip(r'"\'')

        if owner and owner.upper() == 'TPS':
            simpleDwell -= 0.1

        if owner and owner.upper() == 'BRT':
            # (20% Savings Low Floor)*(20% Savings POP)
            simpleDwell = simpleDwell*0.8*0.8
            # but lets not go below 0.3
            if simpleDwell < 0.3:
                simpleDwell = 0.3

        return simpleDwell
                
    def addDelay(self, timeperiod="Simple", additionalLinkFile=None, 
                  complexDelayModes=[], complexAccessModes=[],
                  transitAssignmentData=None,
                  MSAweight=1.0, previousNet=None, logPrefix="", stripTimeFacRunTimeAttrs=True):
        """
        Replaces the old ``addDelay.awk`` script.  
        
        The simple version simply looks up a delay for all stops based on the
        transit line's OWNER and MODE. (Owners ``TPS`` and ``BRT`` get shorter delays.)
        It will also dupe any two-way lines that are one of the complexAccessModes because those
        access mode shutoffs only make sense if the lines are one-way.
        
        Exempts nodes that are in the network's TransitLinks and in the optional
        *additionalLinkFile*, from dwell delay; the idea being that these are LRT or fixed
        guideway links and the link time includes a dwell delay.
        
        If *transitAssignmentData* is passed in, however, then the boards, alights and vehicle
        type from that data are used to calculate delay for the given *complexDelayModes*.
        
        When *MSAweight* < 1.0, then the delay is modified
        to be a linear combination of (prev delay x (1.0-*MSAweight*)) + (new delay x *MSAweight*))
        
        *logPrefix* is a string used for logging: this method appends to the following files:
        
           * ``lineStats[timeperiod].csv`` contains *logPrefix*, line name, total Dwell for the line, 
             number of closed nodes for the line
           * ``dwellbucket[timeperiod].csv`` contails distribution information for the dwells.
             It includes *logPrefix*, dwell bucket number, and dwell bucket count.
             Currently dwell buckets are 0.1 minutes
        
        When *stripTimeFacRunTimeAttrs* is passed as TRUE, TIMEFAC and RUNTIME is stripped for ALL
        modes.  Otherwise it's ignored.
        """

        # Use own links and, if passed, additionaLinkFile to form linSet, which is the set of
        # nodes in the links        
        linkSet = set()
        for link in self.links:
            if isinstance(link,TransitLink):
                link.addNodesToSet(linkSet)
        # print linkSet
        logstr = "addDelay: Size of linkset = %d" % (len(linkSet))

        if additionalLinkFile:
            linknet = TransitNetwork(self.champVersion)
            linknet.parser = TransitParser(transit_file_def, verbosity=0)
            f = open(additionalLinkFile, 'r');
            junk,additionallinks,junk,junk,junk,junk,junk,junk,junk = \
                linknet.parseAndPrintTransitFile(f.read(), verbosity=0)
            f.close()
            for link in additionallinks:
                if isinstance(link,TransitLink):
                    link.addNodesToSet(linkSet)
                    # print linkSet
            logstr += " => %d with %s\n" % (len(linkSet), additionalLinkFile)
        WranglerLogger.info(logstr)

        # record keeping for logging
        statsfile           = open("lineStats"+timeperiod+".csv", "a")
        dwellbucketfile     = open("dwellbucket"+timeperiod+".csv", "a")            
        totalLineDwell      = {}  # linename => total dwell
        totalClosedNodes    = {}  # linename => closed nodes
        DWELL_BUCKET_SIZE   = 0.1    # minutes
        dwellBuckets        = defaultdict(int) # initialize to index => bucket    
        
        # Dupe the one-way lines for complexAccessModes
        if timeperiod=="Simple" and len(complexAccessModes)>0:
            line_idx = 0
            while True:
                # out of lines, done!
                if line_idx >= len(self.lines): break
                
                # skip non-TransitLines
                if not isinstance(self.lines[line_idx],TransitLine):
                    line_idx += 1
                    continue
                
                # skip non-ComplexAccessMode lines
                if int(self.lines[line_idx].attr['MODE']) not in complexAccessModes:
                    line_idx += 1
                    continue
                
                # this is a relevant line -- is it oneway?  then we're ok
                if self.lines[line_idx].isOneWay():
                    line_idx += 1
                    continue

                # make it one way and add a reverse copy
                self.lines[line_idx].setOneWay()
                reverse_line = copy.deepcopy(self.lines[line_idx])
                reverse_line.reverse()
                
                WranglerLogger.debug("Reversed line %s to line %s" % (str(self.lines[line_idx]), str(reverse_line)))                
                self.lines.insert(line_idx+1,reverse_line)
                line_idx += 2
                        

        # iterate through my lines
        for line in self:

            totalLineDwell[line.name]   = 0.0
            totalClosedNodes[line.name] = 0

            # strip the TIMEFAC and the RUNTIME, if desired
            if stripTimeFacRunTimeAttrs:
                if "RUNTIME" in line.attr:
                    WranglerLogger.debug("Stripping RUNTIME from %s" % line.name)
                    del line.attr["RUNTIME"]
                if "TIMEFAC" in line.attr:
                    WranglerLogger.debug("Stripping TIMEFAC from %s" % line.name)                    
                    del line.attr["TIMEFAC"]
            
            # Passing on all the lines that do not have service during the specific time of day
            if timeperiod in TransitLine.HOURS_PER_TIMEPERIOD and line.getFreq(timeperiod) == 0.0: continue
                   
                
            simpleDwellDelay = self.findSimpleDwellDelay(line)

            for nodeIdx in range(len(line.n)):

                # linkSet nodes exempt - don't add delay 'cos that's inherent to the link
                if int(line.n[nodeIdx].num) in linkSet: continue
                # last stop - no delay, end of the line
                if nodeIdx == len(line.n)-1: continue
                # dwell delay for stop nodes only
                if not line.n[nodeIdx].isStop(): continue
                
                # =======================================================================================
                # turn off access?
                if (transitAssignmentData and 
                    (nodeIdx>0) and 
                    (int(line.attr["MODE"]) in complexAccessModes)):
                    try:                  
                        loadFactor  = transitAssignmentData.loadFactor(line.name,
                                                                       abs(int(line.n[nodeIdx-1].num)),
                                                                       abs(int(line.n[nodeIdx].num)),
                                                                       nodeIdx)
                    except:
                        WranglerLogger.warning("Failed to get loadfactor for (%s, A=%d B=%d SEQ=%d); assuming 0" % 
                          (line.name, abs(int(line.n[nodeIdx-1].num)), abs(int(line.n[nodeIdx].num)),nodeIdx))
                        loadFactor = 0.0
                        
                    # disallow boardings (ACCESS=2) (for all nodes except first stop) 
                    # if the previous link has load factor greater than 1.0
                    if loadFactor > 1.0:
                        line.n[nodeIdx].attr["ACCESS"]  = 2
                        totalClosedNodes[line.name]     += 1

                # =======================================================================================                                   
                # Simple delay if
                # - we do not have boards/alighting data,
                # - or if we're not configured to do a complex delay operation
                if not transitAssignmentData or (int(line.attr["MODE"]) not in complexDelayModes):
                    if simpleDwellDelay > 0:
                        line.n[nodeIdx].attr["DELAY"] =  str(simpleDwellDelay)
                    totalLineDwell[line.name]         += simpleDwellDelay
                    dwellBuckets[int(math.floor(simpleDwellDelay/DWELL_BUCKET_SIZE))] += 1
                    continue
                             
                # Complex Delay
                # =======================================================================================
                vehiclesPerPeriod = line.vehiclesPerPeriod(timeperiod)
                try:
                    boards = transitAssignmentData.numBoards(line.name,
                                                             abs(int(line.n[nodeIdx].num)),
                                                             abs(int(line.n[nodeIdx+1].num)),
                                                             nodeIdx+1)
                except:
                    WranglerLogger.warning("Failed to get boards for (%s, A=%d B=%d SEQ=%d); assuming 0" % 
                          (line.name, abs(int(line.n[nodeIdx].num)), abs(int(line.n[nodeIdx+1].num)),nodeIdx+1))
                    boards = 0

                # At the first stop, vehicle has no exits and load factor
                if nodeIdx == 0:             
                    exits       = 0
                else:
                    try:
                        exits       = transitAssignmentData.numExits(line.name,
                                                                     abs(int(line.n[nodeIdx-1].num)),
                                                                     abs(int(line.n[nodeIdx].num)),
                                                                     nodeIdx)
                    except:
                        WranglerLogger.warning("Failed to get exits for (%s, A=%d B=%d SEQ=%d); assuming 0" % 
                          (line.name, abs(int(line.n[nodeIdx-1].num)), abs(int(line.n[nodeIdx].num)),nodeIdx))
                        exits = 0


                
                if MSAweight < 1.0:
                    try:
                        existingDelay = float(previousNet.line(line.name).n[nodeIdx].attr["DELAY"])
                    except:
                        WranglerLogger.debug("No delay found for line %s node %s -- using 0" % 
                                             (line.name, previousNet.line(line.name).n[nodeIdx].num))
                        existingDelay = 0.0 # this can happen if no boards/alights and const=0
                else:
                    MSAdelay = -99999999
                    existingDelay = 0.0

                (delay_const,delay_per_board,delay_per_alight) = transitAssignmentData.capacity.getComplexDwells(line.name, timeperiod)

                WranglerLogger.debug("line name=%s, timeperiod=%s, delay_const,perboard,peralight=%.3f, %.3f, %.3f" %
                                     (line.name, timeperiod, delay_const, delay_per_board, delay_per_alight))

                dwellDelay = (1.0-MSAweight)*existingDelay + \
                             MSAweight*((delay_per_board*float(boards)/vehiclesPerPeriod) +
                                        (delay_per_alight*float(exits)/vehiclesPerPeriod) +
                                        delay_const)
                line.n[nodeIdx].attr["DELAY"]   ="%.3f" % dwellDelay 
                totalLineDwell[line.name]       += dwellDelay
                dwellBuckets[int(math.floor(dwellDelay/DWELL_BUCKET_SIZE))] += 1
                # end for each node loop

            statsfile.write("%s,%s,%f,%d\n" % (logPrefix, line.name, 
                                               totalLineDwell[line.name], totalClosedNodes[line.name]))
            # end for each line loop

        for bucketnum, count in dwellBuckets.iteritems():
            dwellbucketfile.write("%s,%d,%d\n" % (logPrefix, bucketnum, count))
        statsfile.close()
        dwellbucketfile.close()

    def checkCapacityConfiguration(self, complexDelayModes, complexAccessModes):
        """
        Verify that we have the capacity configuration for all lines in the complex modes.
        To save heart-ache later.
        return Success
        """
        if not TransitNetwork.capacity:
            TransitNetwork.capacity = TransitCapacity()
        
        failures = 0
        for line in self:
            linename = line.name.upper()
            mode     = int(line.attr["MODE"])
            if mode in complexDelayModes or mode in complexAccessModes:
            
                for timeperiod in ["AM", "MD", "PM", "EV", "EA"]:
                    if line.getFreq(timeperiod) == 0: continue

                    try:
                        (vehicletype, cap) = TransitNetwork.capacity.getVehicleTypeAndCapacity(linename, timeperiod)
                        if mode in complexDelayModes:
                            (delc,delpb,delpa) = TransitNetwork.capacity.getComplexDwells(linename, timeperiod)

                    except NetworkException as e:
                        print e
                        failures += 1
        return (failures == 0)
    
    def checkValidityOfLinks(self, cubeNetFile):
        """
        Checks the validity of each of the transit links against the given cubeNetFile.
        That is, each link in a .lin should either be in the roadway network, or in a .link file.
        """
        import Cube
    
        (nodes_dict, links_dict) = Cube.import_cube_nodes_links_from_csvs(cubeNetFile,
                                        extra_link_vars=['LANE_AM', 'LANE_OP','LANE_PM',
                                                         'BUSLANE_AM', 'BUSLANE_OP', 'BUSLANE_PM'],
                                        extra_node_vars=[],
                                        links_csv=os.path.join(os.getcwd(),"cubenet_validate_links.csv"),
                                        nodes_csv=os.path.join(os.getcwd(),"cubenet_validate_nodes.csv"),
                                        exportIfExists=True)
        for line in self:
            
            # todo fix this
            line_is_oneway = True
            
            last_node = None
            for node in line:

                # this is the first node - nothing to do                
                if not last_node:
                    last_node = node
                    continue
                
                # we need to check this link but possibly also the reverse
                link_list = [(abs(last_node), abs(node))]
                if not line_is_oneway:
                    link_list.append((abs(node), abs(last_node)))
                
                # check the link(s)
                for (a,b) in link_list:
                    
                    # it's a road link
                    if (a,b) in links_dict: continue
                    
                    found_link = False
                    for link in self.links:
                        if not isinstance(link,TransitLink): continue
                        
                        if link.Anode == a and link.Bnode == b:
                            found_link = True
                            break
                        
                        if not link.isOneway() and link.Anode == b and link.Bnode == a:
                            found_link = True
                            break
                    
                    if found_link: continue

                    WranglerLogger.debug("TransitNetwork.checkValidityOfLinks: (%d, %d) not in the roadway network nor in the off-road links (line %s)" % (a, b, line.name))
                
                last_node = node

    def applyProject(self, parentdir, networkdir, gitdir, projectsubdir=None, **kwargs):
        """
        Apply the given project by calling import and apply.  Currently only supports
        one level of subdir (so projectsubdir can be one level, no more).
        e.g. parentdir=``tmp_blah``, networkdir=``Muni_GearyBRT``, projectsubdir=``center_center``

        See :py:meth:`Wrangler.Network.applyProject` for argument details.
        """
        # paths are already taken care of in checkProjectVersion
        if projectsubdir:
            projectname = projectsubdir
        else:
            projectname = networkdir
            
        evalstr = "import %s; %s.apply(self" % (projectname, projectname)
        for key,val in kwargs.iteritems():
            evalstr += ", %s=%s" % (key, str(val))
        evalstr += ")"
        try:
            exec(evalstr)
        except:
            print "Failed to exec [%s]" % evalstr
            raise
               
        evalstr = "dir(%s)" % projectname
        projectdir = eval(evalstr)
        # WranglerLogger.debug("projectdir = " + str(projectdir))
        pyear = (eval("%s.year()" % projectname) if 'year' in projectdir else None)
        pdesc = (eval("%s.desc()" % projectname) if 'desc' in projectdir else None)            
        
        # print "projectname=" + str(projectname)
        # print "pyear=" + str(pyear)
        # print "pdesc=" + str(pdesc)
        
        # fares
        for farefile in TransitNetwork.FARE_FILES:
            fullfarefile = os.path.join(gitdir, farefile)
            linecount = 0
            # WranglerLogger.debug("cwd=%s  farefile %s exists? %d" % (os.getcwd(), fullfarefile, os.path.exists(fullfarefile)))
            
            if os.path.exists(fullfarefile):
                infile = open(fullfarefile, 'r')
                lines = infile.readlines()
                self.farefiles[farefile].extend(lines)
                linecount = len(lines)
                infile.close()
                WranglerLogger.debug("Read %5d lines from fare file %s" % (linecount, fullfarefile))
        
        return self.logProject(gitdir=gitdir,
                               projectname=(networkdir + "\\" + projectsubdir if projectsubdir else networkdir),
                               year=pyear, projectdesc=pdesc)
