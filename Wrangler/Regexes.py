import re
##__all__ = [ 'nodepair_pattern', 'git_commit_pattern','allday_pattern','linename_pattern']
class Regexes(object):
    nodepair_pattern = re.compile('(\d+)[-,\s]+(\d+)')
    git_commit_pattern = re.compile('commit ([0-9a-f]{40}$)')
    ##linename_pattern = re.compile('(?P<operator>^([\d]+_|MUN|EBA|PRES|SFS))(?P<line>[a-zA-Z0-9_.]+)')
    allday_pattern = re.compile('(ALL|all|All)[\s\-_]*(day|DAY|Day)?')
    linename_pattern = re.compile('(?P<operator>^([\d]+_|MUN|EBA|PRES|SFS|PM))(?P<line>[a-zA-Z0-9/_.]+?)((?P<direction>WB|SB|NB|EB|I|O)?(?P<agency_short>ACE|VTA|AC|MUN|NAP|WC|GG)?(?P<reverse_flag>r)?)$')


