# Initial revision 2011 Sept 14 by lmz
# From Y:\champ\util\pythonlib\champUtil

from itertools import izip

MAX_MTC_ZONE = 1475
MAX_SF_ZONE = 2475
MAX_SF_COUNTY_ZONE = 981


class Lookups:
    """
    This class is just for those lookups that don't really belong anywhere else.
    """
    
    TIMEPERIODS_NUM_TO_STR  = {1:"EA", 2:"AM", 3:"MD", 4:"PM", 5:"EV" }
    TIMEPERIODS_STR_TO_NUM  = dict((v,k) for k,v in TIMEPERIODS_NUM_TO_STR.iteritems())
    OPCOST                  = 0.12 # dollars/mile
    WALKSPEED               = 3.0  # mph
    BIKESPEED               = 10.0 # mph
    PSEG                    = {1:"Worker", 2:"AdultStudent", 3:"Other", 4:"ChildStudent"}
    PURPOSE_NUM_TO_STR      = {1:"Work",    2:"GradeSchool", 3:"HighSchool",
                               4:"College", 5:"Other",       6:"WorkBased" }
    PURPOSE_STR_TO_NUM      = dict((v,k) for k,v in PURPOSE_NUM_TO_STR.iteritems())
    
    #IMPORTANT - THIS ORDER IS "set" and shouldn't be changed unless changes are made to src/sftripmc/define.h
    CHAMP_TRIP_MODES        =["DA",     "SR2",     "SR3",                         
                              "DA_TOLL","SR2_TOLL","SR3_TOLL",
                              "DA_PAID","SR2_PAID","SR3_PAID",
                              "WALK","BIKE",
                              "WLOC","WLRT","WPRE","WFER","WBAR",
                              "DLOCW","DLRTW","DPREW","DFERW","DBARW",
                              "TAXI",
                              "WLOCD","WLRTD","WPRED","WFERD","WBARD"]  
    CHAMP_TRIP_MODES_NUM_TO_STR = dict(izip(range(1,len(CHAMP_TRIP_MODES)+1), CHAMP_TRIP_MODES))
    CHAMP_TRIP_MODES_STR_TO_NUM = dict(izip(CHAMP_TRIP_MODES, range(1,len(CHAMP_TRIP_MODES)+1)))
    
        
    TRANSITMODES    = ["WLW", "ALW", "WLA",
                       "WMW", "AMW", "WMA",
                       "WPW", "APW", "WPA", 
                       "WFW", "AFW", "WFA",
                       "WBW", "ABW", "WBA"]
    
    #IMPORTANT - THIS ORDER IS "set" and shouldn't be changed unless changes are made to src/sfchamp/define.h
    CHAMP_TOUR_MODES        =["DA",     "SR2",      "SR3",
                              "DA_TOLL","SR2_TOLL", "SR3_TOLL",
                              "WALK",   "BIKE",
                              "WTRN",   "DTRN",
                              "TAXI"]
    CHAMP_TOUR_MODES_NUM_TO_STR = dict(izip(range(1,len(CHAMP_TOUR_MODES)+1), CHAMP_TOUR_MODES))
    CHAMP_TOUR_MODES_STR_TO_NUM = dict(izip(CHAMP_TOUR_MODES, range(1,len(CHAMP_TOUR_MODES)+1)))
    
    # from sftripmc/persdata.cpp
    #                   //----------+-------------------------------------------------
    #                   //          |                     TDDEPART
    #                   // TODEPART |        1         2         3         4         5
    #                   //----------+-------------------------------------------------
    DURATION_TRIP = [
                                    [      0.3,       1.2,     8.4,      10.5,    14.1],
                                    [      1.2,       0.3,     4.8,       8.9,    11.5],
                                    [      8.4,       4.8,     0.8,       2.7,     7.7],
                                    [     10.5,       8.9,     2.7,       0.4,     2.0],
                                    [     14.1,      11.5,     7.7,       2.0,     1.1] ]
    
    # from sfourmc/persdata.cpp
    DURATION_TOUR = [
                                    [      0.3,       1.5,     8.2,      10.2,    13.1],
                                    [      1.5,       0.4,     5.1,       8.7,    10.9],
                                    [      8.2,       5.1,     1.0,       3.1,     7.6],
                                    [     10.2,       8.7,     3.1,       0.5,     2.1],
                                    [      2.4,       6.8,     9.4,      13.8,     1.4] ]
    
    TIMEPERIODS_TO_SUBTIMES  = {"EA":[300, 500],
                                "AM":[600, 630, 700, 730, 800, 830],
                                "MD":[900, 1000, 1100, 130, 230,],
                                "PM":[330, 400, 430, 500, 530, 600],
                                "EV":[630, 730] }

    TIMEPERIODS_TO_SUBTIME_DURATIONS = {"EA":[2.0, 1.0],
                                        "AM":[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                                        "MD":[1.0, 1.0, 2.5, 1.0, 1.0],
                                        "PM":[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                                        "EV":[1.0, 7.5] }

    @classmethod
    def readSubTimeVolumeFactors(self):
        """
        Returns dict of dicts.  E.g.  { "EA":{300:0.405, 500:0.595}, ... }
        """
        import re
        WHITESPACE_RE   = re.compile(r"^\s*$")
        VOLFAC_RE       = re.compile(r"^\s*VOLFAC_(EA|AM|MD|PM|EV)([0-9]+)\s*=\s*([0-9\.]+)\s*$")
        ret_dict        = {}
        
        volfacfile = open('VolumeFactors.ctl', 'r')
        for line in volfacfile:
            # skip comments
            if line[0] == ";": continue
            # skip whitespace
            if WHITESPACE_RE.match(line) != None: continue
            match = VOLFAC_RE.match(line)
            if match == None:
                print "Do not understand line: [%s]" % line
                continue
            timeperiod  = match.group(1)
            subtime     = int(match.group(2))
            volfac      = float(match.group(3))
            if timeperiod not in ret_dict:
                ret_dict[timeperiod] = {}
            ret_dict[timeperiod][subtime] = volfac
            
        volfacfile.close()
        # verify they sum to 1 per main time period
        for timeperiod in ret_dict.keys():
            total = 0.0
            for subtime in ret_dict[timeperiod].keys():
                total += ret_dict[timeperiod][subtime]
            if abs(total - 1.0) > 0.01:
                print "Total for timeperiod %s is %f not 1.0: %s" % (timeperiod, total, str(ret_dict))
                exit(2)
        return ret_dict
