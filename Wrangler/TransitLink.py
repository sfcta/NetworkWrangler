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

import re
from .Regexes import nodepair_pattern

__all__ = ['TransitLink']

class TransitLink(dict):
    """ Transit support Link.
       'nodes' property is the node-pair for this link (e.g. 24133,34133)
       'comment' is any end-of-line comment for this link
                 (must include the leading semicolon)
        All other attributes are stored in a dictionary (e.g. thislink['MODE']='1,2')
    """
    def __init__(self):
        dict.__init__(self)
        self.id=''
        self.comment=''
        
        self.Anode = None
        self.Bnode = None

    def __repr__(self):
        s = "LINK nodes=%s, " % (self.id,)

        # Deal w/all link attributes
        fields = []
        for k in sorted(self.keys()):
            fields.append("%s=%s" % (k,self[k]))
        s += ", ".join(fields)
        s += self.comment

        return s
    
    def addNodesToSet(self, set):
        """ Add integer versions of the nodes in this like to the given set
        """
        m = re.match(nodepair_pattern, self.id)
        set.add(int(m.group(1)))
        set.add(int(m.group(2)))
        
    def setId(self, id):
        self.id = id

        m = re.match(nodepair_pattern, self.id)
        self.Anode = int(m.group(1))
        self.Bnode = int(m.group(2))  

    def isOneway(self):
        for key in self.keys():
            
            if key.upper()=="ONEWAY":
                if self[key].upper() in ["NO", "N", "0", "F", "FALSE"]: return False
                return True
        # key not found - what's the default?
        return True
    
    def setOneway(self, oneway_str):
        for key in self.keys():
            if key.upper()=="ONEWAY":
                self[key] = oneway_str
                return
        # key not found
        self["ONEWAY"] = oneway_str