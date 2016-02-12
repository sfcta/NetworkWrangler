import re,sys,os

class Regexes(object):
    nodepair_pattern = re.compile('(\d+)[-,\s]+(\d+)')
    git_commit_pattern = re.compile('commit ([0-9a-f]{40}$)')
    allday_pattern = re.compile('(ALL|all|All)[\s\-_]*(day|DAY|Day)?')
    linename_pattern = re.compile('(?P<operator>^([\d]+_|MUN|EBA|PRES|SFS|TNT))_(?P<line>[a-zA-Z0-9]+?)_((?P<direction>WB|SB|NB|EB|I|O|R)?(?P<agency_short>ACE|VTA|AC|MUN|NAP|WC|GG)?)$')


