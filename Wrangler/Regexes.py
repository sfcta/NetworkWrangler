import re

__all__ = [ 'nodepair_pattern', 'git_commit_pattern','linename_pattern']

nodepair_pattern = re.compile('(\d+)[-,\s]+(\d+)')
git_commit_pattern = re.compile('commit ([0-9a-f]{40}$)')
linename_pattern = re.compile('(?P<operator>^([\d]+_|MUN|EBA|PRES|SFS))(?P<line>[a-zA-Z0-9_]+)')
