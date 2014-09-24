#
# Author: lmz
# Created: 11.02.2011
#

import os, shutil, sys

USAGE = """

python removeLines removeTag filename

 Simple script that reads filename and removes all lines in it that start with the removeTag.
 
 Note: uses filename.tmp for temporary file.
 
"""

if __name__ == '__main__':

    if len(sys.argv) != 3:
        print USAGE
        exit(2)
        
    removeTag       = sys.argv[1]
    filename        = sys.argv[2]
    tmpfilename     = filename + ".tmp"
    removeTagLen    = len(removeTag)
    
    print "Removing [%s] (length %d) lines from [%s] using [%s]" % (removeTag, removeTagLen, filename, tmpfilename)

    if os.path.exists(tmpfilename): 
        print "temp file [%s] exists, aborting." % tmpfilename
        exit(2)
    
    inf     = open(filename, 'r')
    outf    = open(tmpfilename, 'w')
    dropped = 0
    for line in inf:
        # drop this line?
        if line[:removeTagLen]==removeTag:
            dropped += 1
            continue
        
        outf.write(line)
    inf.close()
    outf.close()
    
    shutil.move(tmpfilename, filename)
    print "Dropped %d lines" % dropped