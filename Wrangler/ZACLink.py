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

__all__ = ['ZACLink']

class ZACLink(dict):
    """ ZAC support Link.
       'link' property is the node-pair for this link (e.g. 24133-34133)
       'comment' is any end-of-line comment for this link
                 (must include the leading semicolon)
        All other attributes are stored in a dictionary (e.g. thislink['MODE']='17')
    """
    def __init__(self):
        dict.__init__(self)
        self.id=''
        self.comment=''

    def __repr__(self):
        s = "ZONEACCESS link=%s " % (self.id,)

        # Deal w/all link attributes
        fields = ['%s=%s' % (k,v) for k,v in self.items()]

        s += " ".join(fields)
        s += self.comment

        return s
