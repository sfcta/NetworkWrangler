import copy, glob, inspect, math, os, re, sys, xlrd
from collections import defaultdict
from .Linki import Linki
from .Logger import WranglerLogger
from .Network import Network
from .NetworkException import NetworkException
from .PNRLink import PNRLink
from .Regexes import nodepair_pattern
from .TransitAssignmentData import TransitAssignmentData, TransitAssignmentDataException
from .TransitCapacity import TransitCapacity
from .TransitLine import TransitLine
from .TransitLink import TransitLink
from .TransitParser import TransitParser, transit_file_def
from .ZACLink import ZACLink

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
        self.lines = []
        #note self.links is transit support links, i.e. stuff in muni.link, caltrain.link, etc.
        self.links = []
        self.pnrs   = []
        self.zacs   = []
        self.accessli = []
        self.xferli   = []
        self.farefiles = {} # farefile name -> [ lines in farefile ]
        
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
                    
                    m = re.match(nodepair_pattern, zac.id)
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
                        
        book = xlrd.open_workbook(os.environ["CHAMP_node_names"])
        sh = book.sheet_by_index(0)
        nodeNames = {}
        for rx in range(0,sh.nrows): # skip header
            therow = sh.row(rx)
            nodeNames[int(therow[0].value)] = therow[1].value
        # WranglerLogger.info(str(nodeNames))
        
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

    def parseAndPrintTransitFile(self, trntxt, verbosity=1):
        """
        Verbosity=1: 1 line per line summary
        Verbosity=2: 1 line per node
        """
        success, children, nextcharacter = self.parser.parse(trntxt, production="transit_file")
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

        return convertedLines, convertedLinks, convertedPNR, convertedZAC, \
            convertedAccessLinki, convertedXferLinki

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
        self.parser = TransitParser(transit_file_def, verbosity=0)
        self.parser.tfp.liType = suffix
        logstr = "   Reading %s as %s" % (fullfile, suffix)
        f = open(fullfile, 'r');
        lines,links,pnr,zac,accessli,xferli = self.parseAndPrintTransitFile(f.read(), verbosity=0)
        f.close()
        logstr += self.doMerge(fullfile,lines,links,pnr,zac,accessli,xferli,insert_replace)
        WranglerLogger.debug(logstr)
            
    def doMerge(self,path,lines,links,pnrs,zacs,accessli,xferli,insert_replace=False):
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
            if suffix in ["lin","link","pnr","zac","access","xfer"]:
                self.parser = TransitParser(transit_file_def, verbosity=0)
                self.parser.tfp.liType = suffix
                fullfile = os.path.join(path,filename)
                logstr = "   Reading %s" % filename
                f = open(fullfile, 'r');
                lines,links,pnr,zac,accessli,xferli = self.parseAndPrintTransitFile(f.read(), verbosity=0)
                f.close()
                logstr += self.doMerge(fullfile,lines,links,pnr,zac,accessli,xferli,insert_replace)
                WranglerLogger.debug(logstr)

    @staticmethod
    def initializeTransitCapacity(directory="."):
        TransitNetwork.capacity = TransitCapacity(directory=directory)

    def addXY(self, coord_dict=None):
        '''
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

    def addFirstDeparturesToAllLines(self):
        for line in self.lines:
            if isinstance(line, str):
                # then it's just a comment/text line, so pass
                pass
            elif isinstance(line, TransitLine):
                # then we should add coordinates to it.
                line.setFirstDepartures()
            else:
                raise NetworkException('Unhandled data type %s in self.lines' % type(line))
        
    def addTravelTimes(self, highway_networks):
        '''
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
    
##    def writeFastTrips_Network(self, dir, shapes=shapes.txt, stop_times, ):
##        pass

    def writeFastTrips_Shapes(self, f, writeHeaders=True):
        '''
        Iterate each line in this TransitNetwork and write fast-trips style shapes.txt to f
        '''
        # check if it's a filename or a file. Open it if it's a filename
        if isinstance(f, str):
            f = open(f, 'w')
        elif isinstance(f, file):
            if filestream.closed: f = open(f.name)
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
        
    def writeFastTrips_Trips(self, f_trips, f_stoptimes, writeHeaders=True):
        '''
        Iterate each line in this TransitNetwork and write fast-trips style stop_times.txt fo f
        This requires that each line has a complete set of links with ``BUSTIME_<TOD>`` for each
        <TOD> in ``AM``, ``MD``, ``PM``, ``EV``, ``EA``.
        '''
        # check if it's a filename or a file. Open it if it's a filename
        if isinstance(f_trips, str):
            f_trips = open(f_trips, 'w')
        elif isinstance(f_trips, file):
            if f_trips.closed: f_trips = open(f_trips.name)
            
        if isinstance(f_stoptimes, str):
            f_stoptimes = open(f_stoptimes, 'w')
        elif isinstance(f_stoptimes, file):
            if f_stoptimes.closed: f_stoptimes = open(f_stoptimes.name)

        id_generator = self.generate_unique_id(range(1,999999))
        
        # go through lines and write them to f.
        for line in self.lines:
            if isinstance(line, str):
                pass
            elif isinstance(line, TransitLine):
                line.writeFastTrips_Trips(f_trips, f_stoptimes, id_generator, writeHeaders)
                writeHeaders = False # only write them the with the first line.
                
    def generate_unique_id(self, seq):
        """
        Generator that yields a number from a passed in sequence
        """
        for x in seq:
            yield x
    
    def writeFastTrips_FareRules():
        pass

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
            junk,additionallinks,junk,junk,junk,junk = \
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
