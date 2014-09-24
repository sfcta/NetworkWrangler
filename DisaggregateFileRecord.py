# Initial revision 2011 Sept 13 by lmz
# From Y:\champ\util\pythonlib\champUtil Trip class
# See example usage in the MAIN

from tables import openFile, IsDescription, Int32Col, Float32Col, Filters
from collections import defaultdict
import time

recordKeys = list()  # Callers can access these by importing these variables

class DisaggregateFileRecord(IsDescription):
    """
    Class to represent the disaggregate trip data from SF-CHAMP.
    May also be modified to represent other disaggregate data.
    For use with pytables.  See TourDiary.cpp for more.
    
    All this stuff happens once, I think when the file is imported.
    """
    
    # Each item is a record.  Source of truth: src/util/TourDiary.cpp
    global recordKeys
    recordKeys.append("hhid");          hhid        = Int32Col(pos=len(recordKeys))
    recordKeys.append("persid");        persid      = Int32Col(pos=len(recordKeys))
    recordKeys.append("homestaz");      homestaz    = Int32Col(pos=len(recordKeys))
    recordKeys.append("hhsize");        hhsize      = Int32Col(pos=len(recordKeys))
    recordKeys.append("hhadlt");        hhadlt      = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage65up");      nage65up    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage5064");      nage5064    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage3549");      nage3549    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage2534");      nage2534    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage1824");      nage1824    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage1217");      nage1217    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nage511");       nage511     = Int32Col(pos=len(recordKeys))
    recordKeys.append("nageund5");      nageund5    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nfulltim");      nfulltim    = Int32Col(pos=len(recordKeys))
    recordKeys.append("nparttim");      nparttim    = Int32Col(pos=len(recordKeys))
    recordKeys.append("autos");         autos       = Int32Col(pos=len(recordKeys))
    recordKeys.append("hhinc");         hhinc       = Float32Col(pos=len(recordKeys))
    recordKeys.append("gender");        gender      = Int32Col(pos=len(recordKeys))
    recordKeys.append("age");           age         = Int32Col(pos=len(recordKeys))
    recordKeys.append("relat");         relat       = Int32Col(pos=len(recordKeys))
    recordKeys.append("race");          race        = Int32Col(pos=len(recordKeys))
    recordKeys.append("employ");        employ      = Int32Col(pos=len(recordKeys))
    recordKeys.append("educn");         educn       = Int32Col(pos=len(recordKeys)) # 23

    recordKeys.append("worksTwoJobs");  worksTwoJobs= Int32Col(pos=len(recordKeys))
    recordKeys.append("worksOutOfArea");worksOutOfArea    = Int32Col(pos=len(recordKeys))
    recordKeys.append("mVOT");          mVOT        = Float32Col(pos=len(recordKeys))
    recordKeys.append("oVOT");          oVOT        = Float32Col(pos=len(recordKeys))
    recordKeys.append("randseed");      randseed    = Int32Col(pos=len(recordKeys))
    recordKeys.append("workstaz");      workstaz    = Int32Col(pos=len(recordKeys))
    recordKeys.append("paysToPark");    paysToPark  = Int32Col(pos=len(recordKeys)) # 30

    # MC Logsums
    recordKeys.append("mcLogSumW0");    mcLogSumW0  = Float32Col(pos=len(recordKeys))
    recordKeys.append("mcLogSumW1");    mcLogSumW1  = Float32Col(pos=len(recordKeys))
    recordKeys.append("mcLogSumW2");    mcLogSumW2  = Float32Col(pos=len(recordKeys))
    recordKeys.append("mcLogSumW3");    mcLogSumW3  = Float32Col(pos=len(recordKeys)) # 34

    # DC Logsum outputs
    recordKeys.append("mcLogSumW");     mcLogSumW   = Float32Col(pos=len(recordKeys))
    recordKeys.append("dcLogSumPk");    dcLogSumPk  = Float32Col(pos=len(recordKeys))
    recordKeys.append("dcLogSumOp");    dcLogSumOp  = Float32Col(pos=len(recordKeys))
    recordKeys.append("dcLogSumAtWk");  dcLogSumAtWk= Float32Col(pos=len(recordKeys)) # 38
   
    # Day Pattern outputs
    recordKeys.append("pseg");          pseg        = Int32Col(pos=len(recordKeys))
    recordKeys.append("tour");          tour        = Int32Col(pos=len(recordKeys))
    recordKeys.append("daypattern");    daypattern  = Int32Col(pos=len(recordKeys))
    recordKeys.append("purpose");       purpose     = Int32Col(pos=len(recordKeys))
    recordKeys.append("ctprim");        ctprim      = Int32Col(pos=len(recordKeys))
    recordKeys.append("cttype");        cttype      = Int32Col(pos=len(recordKeys))
    recordKeys.append("tnstopsb");      tnstopsb    = Int32Col(pos=len(recordKeys))
    recordKeys.append("tnstopsa");      tnstopsa    = Int32Col(pos=len(recordKeys))
    recordKeys.append("todepart");      todepart    = Int32Col(pos=len(recordKeys))
    recordKeys.append("tddepart");      tddepart    = Int32Col(pos=len(recordKeys))

    # for MC
    recordKeys.append("alreadyPaid");   alreadyPaid = Int32Col(pos=len(recordKeys))
    recordKeys.append("priority");      priority    = Int32Col(pos=len(recordKeys))
    recordKeys.append("primdest");      primdest    = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopBefTime1");  stopBefTime1= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopBefTime2");  stopBefTime2= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopBefTime3");  stopBefTime3= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopBefTime4");  stopBefTime4= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopAftTime1");  stopAftTime1= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopAftTime2");  stopAftTime2= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopAftTime3");  stopAftTime3= Int32Col(pos=len(recordKeys))
    recordKeys.append("stopAftTime4");  stopAftTime4= Int32Col(pos=len(recordKeys)) # 59

    recordKeys.append("tourmode");              tourmode             = Int32Col(pos=len(recordKeys))
    recordKeys.append("autoExpUtility");        autoExpUtility       = Float32Col(pos=len(recordKeys))
    recordKeys.append("walkTransitAvailable");  walkTransitAvailable = Int32Col(pos=len(recordKeys))
    recordKeys.append("walkTransitProb");       walkTransitProb      = Float32Col(pos=len(recordKeys))
    recordKeys.append("driveTransitOnly");      driveTransitOnly     = Int32Col(pos=len(recordKeys))
    recordKeys.append("driveTransitOnlyProb");  driveTransitOnlyProb = Float32Col(pos=len(recordKeys)) # 65
    
    # for ISTOP
    recordKeys.append("stopb1");        stopb1      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopb2");        stopb2      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopb3");        stopb3      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopb4");        stopb4      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopa1");        stopa1      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopa2");        stopa2      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopa3");        stopa3      = Int32Col(pos=len(recordKeys))
    recordKeys.append("stopa4");        stopa4      = Int32Col(pos=len(recordKeys))

    # Trip Mode Choice
    recordKeys.append("mcurrseg");      mcurrseg    = Int32Col(pos=len(recordKeys))
    recordKeys.append("mOtaz");         mOtaz       = Int32Col(pos=len(recordKeys))
    recordKeys.append("mDtaz");         mDtaz       = Int32Col(pos=len(recordKeys))
    recordKeys.append("mOdt");          mOdt        = Int32Col(pos=len(recordKeys))
    recordKeys.append("mChosenmode");   mChosenmode = Int32Col(pos=len(recordKeys))
    recordKeys.append("mNonMot");       mNonMot     = Int32Col(pos=len(recordKeys))
    recordKeys.append("mExpAuto");      mExpAuto    = Float32Col(pos=len(recordKeys))
    recordKeys.append("mWlkAvail");     mWlkAvail   = Int32Col(pos=len(recordKeys))
    recordKeys.append("mWlkTrnProb");   mWlkTrnProb = Float32Col(pos=len(recordKeys))
    recordKeys.append("mDriveOnly");    mDriveOnly  = Int32Col(pos=len(recordKeys))
    recordKeys.append("mDriveTrnProb"); mDriveTrnProb=Float32Col(pos=len(recordKeys))
    recordKeys.append("mSegDir");       mSegDir     = Int32Col(pos=len(recordKeys))

    recordKeys.append("curr_segdur");   curr_segdur = Int32Col(pos=len(recordKeys))
    recordKeys.append("trippkcst");     trippkcst   = Float32Col(pos=len(recordKeys))

    recordKeys.append("prefTripTod");   prefTripTod = Int32Col(pos=len(recordKeys))
    recordKeys.append("tripTod");       tripTod     = Int32Col(pos=len(recordKeys))

if __name__ == '__main__':

    # this is a READ example - it doesn't actually use the DisaggregateFileRecord
    infilename = "TRIPMC.H51"
    infile = openFile(infilename, mode="r")
    rownum = 1
    chosenmodes = defaultdict(int)
    segdurs     = defaultdict(int)
    start       = time.time()
    
    for row in infile.root.records:
        chosenmodes[row['mChosenmode']] += 1
        segdurs[row['curr_segdur']]     += 1
        rownum += 1
        
        if rownum % 1000000 == 0: print "Read %10d rows" % rownum
    infile.close()
    print "Read %s in %5.2f mins" % (infilename, (time.time() - start)/60.0)
    
    for chosenmode,count in chosenmodes.iteritems():
        print "Chosenmode %3d => %d" % (chosenmode, count)
 
    for segdur,count in segdurs.iteritems():
        print "segdur %3d => %d" % (segdur, count)
    
    # this is a WRITE example - it does use the DisaggregateFileRecord
    outfilename = r"C:\TEMP\DisaggregateFileRecord_writeTest.h5"
    outfile = openFile(outfilename, mode="w")
    compfilt = Filters(complevel=1,complib='zlib')
    table = outfile.createTable("/", "records", DisaggregateFileRecord,"test records",
                                filters=compfilt, expectedrows=10)
    
    record = table.row
    for hhid in range(10):
        record["hhid"] = hhid+1
        record["persid"] = hhid+1
        # you get the idea
        record["mChosenmode"] = hhid+1
        record["curr_segdur"] = hhid+1
        record["tripTod"] = 2
        
        record.append()
    table.flush()
    outfile.close()
    print "Wrote test file %s" % outfilename