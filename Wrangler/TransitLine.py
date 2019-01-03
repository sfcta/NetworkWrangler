# SFCTA NetworkWrangler: Wrangles transit and road networks from SF-CHAMP
# Copyright (C) 2018 San Francisco County Transportation Authority
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from .NetworkException import NetworkException
from .Node import Node
from .Logger import WranglerLogger

__all__ = ['TransitLine']

class TransitLine(object):
    """
    Transit route. Behaves like a dictionary of attributes.
    *n* is list of Node objects (see :py:class:`Node`)
    All other attributes are stored as a dictionary. e.g.::

        thisroute['MODE']='5'

    """
    
    HOURS_PER_TIMEPERIOD = {"AM":3.0, #what about 4-6a?
                            "MD":6.5,
                            "PM":3.0,
                            "EV":8.5,
                            "EA":3.0
                            }
    MODETYPE_TO_MODES = {"Local":[11,12,16,17,18,19],
                         "BRT":[13,20],
                         "LRT":[14,15,21],
                         "Premium":[22,23,24,25,26,27,28,29,30],
                         "Ferry":[31],
                         "BART":[32,33]
                         }
    
    # Do these modes have offstreet stops?
    MODENUM_TO_OFFSTREET = {11:False, # muni bus
                            12:False, # muni Express bus
                            13:False, # mun BRT
                            14:False, # cable car -- These are special because they don't have explicity WNR nodes
                            15:False, # LRT       -- and are just implemented by reading the muni.xfer line as muni.access
                            16:False, # Shuttles
                            17:False, # SamTrans bus
                            18:False, # AC bus
                            19:False, # other local bus
                            20:False, # Regional BRT
                            21:True,  # Santa Clara LRT
                            22:False, # AC premium bus
                            23:False, # GG premium bus
                            24:False, # SamTrans premium bus
                            25:False, # Other premium bus
                            26:True,  # Caltrain
                            27:True,  # SMART
                            28:True,  # eBART
                            29:True,  # Regional Rail/ACE/Amtrak
                            30:True,  # HSR
                            31:True,  # Ferry
                            32:True,  # BART
                            33:True   # BART							
                            }
    
    def __init__(self, name=None, template=None):
        self.attr = {}
        self.n = []
        self.comment = None

        self.name = name
        if name and name.find('"')==0:
            self.name = name[1:-1]  # Strip leading/trailing dbl-quotes

        if template:
            self._applyTemplate(template)

    def __iter__(self):
        """
        Iterator for looping through stops
        """
        self.currentStopIdx = 0
        return self

    def next(self):
        """
        Method for iterator.  Iterator usage::

            line = transitnet.line("MUN14LI")
            for stop in line:
                print stop # stop is an int
        """
        if self.currentStopIdx >= len(self.n):
            raise StopIteration

        self.currentStopIdx += 1
        return int(self.n[self.currentStopIdx-1].num)

    def setFreqs(self, freqs, timepers=None, allowDowngrades=True):
        '''Set some or all five headways (AM,MD,PM,EV,EA)
           - freqs is a list of numbers (or can be one number if only setting one headway)
             also accepts list of strings of numbers e.g. ["8","0","8","0","0"]
           - If setting fewer than 5 headways, timepers must specify the time period(s)
             for which headways are being set. Can be numbers like [1,3] or strings like ['AM','PM'].
             If setting all headways, True or 'All' may be passed.
           - allowDowngrades (optional, pass either True or False) specifies whether headways
             may be increased (i.e., whether service may be reduced) with the current action. 
        '''
        all_timepers = ['AM','MD','PM','EV','EA']
        if timepers in (None, True, 'All', 'all', 'ALL'):
            if not len(freqs)==5: raise NetworkException('Must specify all 5 frequencies or specify time periods to set')
            num_freqs = 5
            num_timepers = 5
            timepers = all_timepers[:]
        else:
            try:
                num_freqs = len(freqs)
            except TypeError:   # only single number, not list, passed
                num_freqs = 1
                freqs = [freqs]
            try:
                num_timepers = len(timepers)
            except TypeError:   # only single time period, not list, passed
                num_timepers = 1
                timepers = [timepers]
            if num_freqs <> num_timepers: raise NetworkException('Specified ' + num_freqs + ' frequencies for ' + num_timepers + ' time periods')
        for i in range(num_timepers):
            timeper = timepers[i]
            try:
                timeper_int = int(timeper)  # time period may be number (1) or string ("1")
                timepers[i] = all_timepers[timeper_int - 1]
                timeper_idx = timeper_int
            except ValueError:  # time period may be descriptive ("AM")
                timeper = timeper.upper()
                if timeper not in all_timepers: raise NetworkException('"' + timeper + '" is not a valid time period')
                timeper_idx = 1 + all_timepers.index(timeper)
            attr_set = 'FREQ[' + str(timeper_idx) + ']'
            if(allowDowngrades):
                self.attr[attr_set] = float(freqs[i])
            else:
                self.attr[attr_set] = min(float(freqs[i]),self.attr[attr_set])

        
    def getFreqs(self):
        """
        Return the frequencies for this line as a list of 5 strings representing AM,MD,PM,EV,EA.
        """
        return [self.attr['FREQ[1]'],
                self.attr['FREQ[2]'],
                self.attr['FREQ[3]'],
                self.attr['FREQ[4]'],
                self.attr['FREQ[5]']]

    def getFreq(self, timeperiod):
        """
        Returns a float version of the frequency for the given *timeperiod*, which should be one
        of ``AM``, ``MD``, ``PM``, ``EV`` or ``EA``
        """
        if timeperiod=="AM":
            return float(self.attr["FREQ[1]"])
        elif timeperiod=="MD":
            return float(self.attr["FREQ[2]"])
        elif timeperiod=="PM":
            return float(self.attr["FREQ[3]"])
        elif timeperiod=="EV":
            return float(self.attr["FREQ[4]"])
        elif timeperiod=="EA":
            return float(self.attr["FREQ[5]"])
        raise NetworkException("getFreq() received invalid timeperiod "+str(timeperiod))

    def hasService(self):
        """
        Returns true if any frequency is nonzero.
        """
        if self.getFreq("AM") != 0: return True
        if self.getFreq("MD") != 0: return True
        if self.getFreq("PM") != 0: return True
        if self.getFreq("EV") != 0: return True
        if self.getFreq("EA") != 0: return True
        return False

    def setOwner(self, newOwner):
        """
        Sets the owner for the transit line
        """
        self.attr["OWNER"] = str(newOwner)

    def getModeType(self):
        """
        Returns on of the keys in MODETYPE_TO_MODES 
        (e.g. one of "Local", "BRT", "LRT", "Premium", "Ferry" or "BART")
        """
        modenum = int(self.attr['MODE'])
        for modetype,modelist in TransitLine.MODETYPE_TO_MODES.iteritems():
            if modenum in modelist:
                return modetype
        return None

    def isOneWay(self):
        """
        Returns a bool indicating if the line is oneway
        """
        oneway = self.attr["ONEWAY"]
        if oneway.upper() in ["N", "F"]:
            return False
        # default is true
        return True
    
    def setOneWay(self):
        """
        Turns on the oneway flag
        """
        self.attr["ONEWAY"] = "T"
        
    def hasOffstreetNodes(self):
        """
        Returns True if the line has offstreet nodes
        """
        modenum = int(self.attr['MODE'])
        return TransitLine.MODENUM_TO_OFFSTREET[modenum]

    def vehiclesPerPeriod(self, timeperiod):
        """
        Returns the number of vehicles (as a float) that will run for the given time period.
        E.g. for 10 minute frequencies in the AM, 3*6 = 18
        """
        freq = self.getFreq(timeperiod)
        if freq < 0.01:
            return 0.0
        
        # minutes per time period divided by frequency
        return 60.0*self.HOURS_PER_TIMEPERIOD[timeperiod]/freq
              
    def hasNode(self,nodeNumber):
        """
        Returns True if the given *nodeNumber* is a node in this line (stop or no).
        *nodeNumber* should be an integer.
        """
        for node in self.n:
            if abs(int(node.num)) == abs(nodeNumber):
                return True
        return False
                
    def hasLink(self,nodeA,nodeB):
        """
        Returns True iff *(nodeA,nodeB)* is a link in this line.
        *nodeA* and *nodeB* should be integers and this method is stop-insensitive.
        However, it does not check for *(nodeB,nodeA)* even when the line is two-way.
        """
        nodeNumPrev = -1
        for node in self.n:
            nodeNum = abs(int(node.num))
            if nodeNum == abs(nodeB) and nodeNumPrev == abs(nodeA):
                return True
            nodeNumPrev = nodeNum
        return False
    
    def hasSegment(self,nodeA,nodeB):
        """
        Returns True iff *nodeA* and *nodeB* appear in this line, and *nodeA* appears before *nodeB*.
        This method is stop-insensitive.  Also it does not do any special checking for two-way
        lines.
        """
        hasA=False
        for node in self.n:
            nodeNum = abs(int(node.num))
            if nodeNum == abs(nodeA):
                hasA=True
            elif nodeNum == abs(nodeB):
                if hasA: return True
                else: return False
        return False

    def hasSequence(self,list_of_node_ids):
        """
        Returns True iff the nodes indicated by list_of_node_ids appear in this line, in the exact specified order.
        This method is stop-insenstive.
        list_of_node_ids should be a list of positive integers, ordered by transit line path.
        """
        node_ids = self.listNodeIds()
        for i in range(len(node_ids)):
            if node_ids[i:i+len(list_of_node_ids)] == list_of_node_ids:
                return True
        return False

    def listNodeIds(self,ignoreStops=True):
        """
        Returns a list of integers representing the node ids that appear along this line.
        This method is stop-sensitive if called with ignoreStops=False.
        """
        node_ids = []
        for node in self.n:
            nodeNum = int(node.num)
            if(ignoreStops):
                nodeNum = abs(nodeNum)
            node_ids.append(nodeNum)
        return node_ids

        
    def numStops(self):
        """
        Counts and returns the number of stops in the line.
        """
        numStops = 0
        for node in self.n:
            if node.isStop(): numStops += 1
        return numStops

    def setNodes(self, newnodelist):
        """
        Given a list of ints representing node numbers,
        converts these to Node types uses this new list, throwing away the previous node list.
        """
        for i in range(len(newnodelist)):
            if isinstance(newnodelist[i],int): newnodelist[i] = Node(newnodelist[i])
        self.n = newnodelist
    
    def insertNode(self,refNodeNum,newNodeNum,stop=False,after=True):
        """
        Inserts the given *newNodeNum* into this line, as a stop if *stop* is True.
        The new node is inserted after *refNodeNum* if *after* is True, otherwise it is inserted
        before *refNodeNum*.

        *refNodeNum* and *newNodeNum* are ints.
        """
        newNode = Node(newNodeNum)
        newNode.setStop(stop)

        nodeIdx = 0
        while True:
            # out of nodes -- done
            if nodeIdx >= len(self.n): return
            
            currentNodeNum = abs(int(self.n[nodeIdx].num))
            if currentNodeNum == abs(refNodeNum):
                if after==True:
                    self.n.insert(nodeIdx+1,newNode)
                    WranglerLogger.debug("In line %s: inserted node %s after node %s" % (self.name,newNode.num,str(refNodeNum)))
                else:
                    self.n.insert(nodeIdx,newNode)
                    WranglerLogger.debug("In line %s: inserted node %s before node %s" % (self.name,newNode.num,str(refNodeNum)))
                nodeIdx += 1 # skip ahead one since we just added
            
            nodeIdx += 1
    
    def splitLink(self,nodeA,nodeB,newNodeNum,stop=False):
        """
        Checks to see if the link exists in the line (throws an exception if not)
        and then inserts the *newNodeNum* in between *nodeA* and *nodeB* (as a stop, if *stop* is True)

        *nodeA*, *nodeB* and *newNodeNum* are all ints.

        This is stop-insensitive to *nodeA* and *nodeB*.
        """
        if not self.hasLink(nodeA,nodeB):
            raise NetworkException( "Line %s Doesn't have that link - so can't split it" % (self.name))
        newNode = Node(newNodeNum)
        if stop==True: newNode.setStop(True)
        
        nodeNumPrev = -1
        for nodeIdx in range(len(self.n)):
            currentNodeNum = abs(int(self.n[nodeIdx].num))
            if currentNodeNum == abs(nodeB) and nodeNumPrev == abs(nodeA):
                self.n.insert(nodeIdx,newNode)
                WranglerLogger.debug("In line %s: inserted node %s between node %s and node %s" % (self.name,newNode.num,str(nodeA),str(nodeB)))
            nodeNumPrev = currentNodeNum
    
    def extendLine(self, oldnode, newsection, beginning=True):
        """
        Replace nodes up through **and including** *oldnode* with *newsection*.
        *newsection* can be a list of numbers; they will be converted to Nodes.

        **This is stop-sensitive!**  If *oldnode* has the wrong sign, it will throw an exception.

        If beginning, does this at the beginning; otherwise at the end.
        """
        try:
            ind = self.n.index(oldnode)
        except:
            ind = self.n.index(-oldnode)
                    
        # make the new nodes
        for i in range(len(newsection)):
            if isinstance(newsection[i],int): newsection[i] = Node(newsection[i])
        
        if beginning:
            # print self.n[:ind+1]
            self.n[:ind+1] = newsection
        else:
            self.n[ind:] = newsection
    
    def replaceSegment(self, node1, node2, newsection, preserveStopStatus=False):
        """ Replaces the section from node1 to node2 with the newsection
            Newsection can be an array of numbers; this will make nodes.
            preserveStopStatus means if node1 is a stop, make the replacement first node a stop, ditto for node2
        """
        WranglerLogger.debug("replacing segment " + str(node1) + " "+str(node2)+" with "+str(newsection)+" for "+self.name)
        try:
            ind1 = self.n.index(node1)
            stop1 = True
        except:
            ind1 = self.n.index(-node1)
            stop1 = False
            
        try:
            ind2 = self.n.index(node2)
            stop2 = True
        except:
            ind2 = self.n.index(-node2)
            stop2 = False
        
        attr1 = self.n[ind1].attr
        attr2 = self.n[ind2].attr
        
        # make the new nodes
        for i in range(len(newsection)):
            if isinstance(newsection[i],int): newsection[i] = Node(newsection[i])
        # xfer the attributes
        newsection[0].attr=attr1
        newsection[-1].attr=attr2
        
        if preserveStopStatus:
            newsection[0].setStop(stop1)
            newsection[-1].setStop(stop2)
        
        self.n[ind1:ind2+1] = newsection

    def replaceSequence(self, node_ids_to_replace, replacement_node_ids):
        """
        Replaces the sequence of nodes indicated by the positive integer list node_ids_to_replace
        with the new sequence of nodes indicated by the positive integer list replacement_node_ids
        This method removes stops from the replaced sequence; stops will have to be re-added.
        Returns true iff the sequence is successfully replaced.
        """
        if self.hasSequence(node_ids_to_replace):
            WranglerLogger.debug("replacing sequence " + str(node_ids_to_replace) + " with " + str(replacement_node_ids) + " for " + self.name)
        else:
            return False
        node_ids = self.listNodeIds()
        replaceNodesStartingAt = -1
        for i in range(len(node_ids)):
            if node_ids[i:i+len(node_ids_to_replace)] == node_ids_to_replace:
                replaceNodesStartingAt = i
                break
        if replaceNodesStartingAt < 0:
            WranglerLogger.debug("an unexpected error occurred in replaceSequence for " + self.name)
            return False

        attr1 = self.n[replaceNodesStartingAt].attr
        attr2 = self.n[replaceNodesStartingAt+len(node_ids_to_replace)].attr
        
        # make the new nodes
        replacement_nodes = list(replacement_node_ids) # copy this, we'll make them nodes
        for i in range(len(replacement_nodes)):
            if isinstance(replacement_nodes[i],int): replacement_nodes[i] = Node(replacement_nodes[i])
            # they aren't stops
            replacement_nodes[i].setStop(False)
        # xfer the attributes
        replacement_nodes[0].attr=attr1
        replacement_nodes[-1].attr=attr2

        self.n[replaceNodesStartingAt:replaceNodesStartingAt+len(node_ids_to_replace)] = replacement_nodes
        return True

    def setStop(self, nodenum, isStop=True):
        """ 
        Throws an exception if the nodenum isn't found
        """
        found = False
        for node in self.n:
            if abs(int(node.num)) == abs(nodenum):
                node.setStop(isStop)
                found = True
        if not found:
            raise NetworkException("TransitLine %s setStop called but stop %d not found" % (self.name, nodenum))

    def addStopsToSet(self, set):
        for nodeIdx in range(len(self.n)):
            if self.n[nodeIdx].isStop():
                set.add(int(self.n[nodeIdx].num))
                
    def reverse(self):
        """
        Reverses the current line -- adds a "-" to the name, and reverses the node order
        """
        # if name is 12 chars, have to drop one -- cube has a MAX of 12
        if len(self.name)>=11: self.name = self.name[:11]
        self.name = self.name + "R"
        self.n.reverse()
        
    def _applyTemplate(self, template):
        '''Copy all attributes (including nodes) from an existing transit line to this line'''
        self.attr = copy.deepcopy(template.attr)
        self.n = copy.deepcopy(template.n)
        self.comment = template.comment

    # Dictionary methods
    def __getitem__(self,key): return self.attr[key.upper()]
    def __setitem__(self,key,value): self.attr[key.upper()]=value
    def __cmp__(self,other): return cmp(self.name,other)

    # String representation: for outputting to line-file
    def __repr__(self):
        s = '\nLINE NAME=\"%s\",\n    ' % (self.name,)
        if self.comment: s+= self.comment

        # Line attributes
        s += ",\n    ".join(["%s=%s" % (k,v) for k,v in sorted(self.attr.items())])

        # Node list
        s += ",\n"
        prevAttr = True
        for nodeIdx in range(len(self.n)):
            s += self.n[nodeIdx].lineFileRepr(prependNEquals=prevAttr, lastNode=(nodeIdx==len(self.n)-1))
            prevAttr = len(self.n[nodeIdx].attr)>0

        return s

    def __str__(self):
        s = 'Line name \"%s\" freqs=%s' % (self.name, str(self.getFreqs()))
        return s
