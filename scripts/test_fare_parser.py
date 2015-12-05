import sys, os, getopt
sys.path.insert(0,r'Y:\Users\Drew\NetworkWrangler')
import Wrangler
#from Wrangler.FareParser import FareParser
from Wrangler.Fare import Fare, XFFare, ODFare, FarelinksFare
#from Wrangler.FareParser import fare_file_def
from Wrangler.TransitParser import TransitParser, transit_file_def


myfareparser = TransitParser(transit_file_def, verbosity=1)


parse_path = r'Q:\Model Development\SHRP2-fasttrips\Task2\network_translation\input_champ_network\freeflow\trn'
parse_files = ['amtrak.fare','bart.fare','caltrain.fare','ebart.fare','farelinks.fare','ferry.fare','hsr.fare','smart.fare','xfer.fare']
#parse_files = ['farelinks.fare']
for file in parse_files:
    parsefile = open(os.path.join(parse_path,file),'r')
    parsetxt = parsefile.read()
    try:
        success, children, nextcharacter = myfareparser.parse(parsetxt, production="fare_file")
        if nextcharacter == len(parsetxt):
            print "%s: successfully parsed" % file
        else:
            print '%s: failed to parse transit fare file.  Read %d out of %d characters' % (file, nextcharacter, len(parsetxt))
            print parsetxt[nextcharacter-200:nextcharacter]
##            errlog = open(os.path.join(r'Y:\Users\Drew\NetworkWrangler\scripts',file+'_errlog.log'),'w')
##            errlog.write(parsetxt[nextcharacter:])
##            errlog.close()
    except Exception as e:
        print e
        print "%s: failed to parse" % file

print "converting XFARE to Fares"
xf_fares = myfareparser.convertXFFareData()
print "converted %d XFARE records to Fares" % len(xf_fares)
i = 0
for fare in xf_fares:
    if isinstance(fare, Fare):
        #print str(fare)
        i += 1
print i
print "converting OD fare files to Fares"
od_fares = myfareparser.convertODFareData()
print "converted %d OD fare records to Fares" % len(od_fares)
i = 0
for fare in od_fares:
    if isinstance(fare, ODFare):
        i += 1
print i   
print "converting farelinks fare files to Fares"
farelinks_fares = myfareparser.convertFarelinksFareData()
print "converted %d Farelinks fare files to Fares" % len(farelinks_fares)
i = 0
for fare in farelinks_fares:
    if isinstance(fare, FarelinksFare):
        #print str(fare)
        i += 1
print i
