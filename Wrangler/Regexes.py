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

__all__ = [ 'nodepair_pattern', 'git_commit_pattern']

nodepair_pattern = re.compile('(\d+)[-,\s]+(\d+)')
git_commit_pattern = re.compile('commit ([0-9a-f]{40}$)')
