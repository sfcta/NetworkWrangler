import sys, os
import numpy as np
import pandas as pd
import gtfs_utils

if __name__=='__main__':
    #path = r'Q:\Model Development\SHRP2-fasttrips\Task2\gtfs\SFMTA_20120319'
    args = sys.argv[1:]
    path = args[0]
    outpath = args[1]
    gtfs = gtfs_utils.GTFSFeed(path)
    time_periods = {'EA':"03:00:00-05:59:59",
                    'AM':"06:00:00-08:59:59",
                    'MD':"09:00:00-15:29:59",
                    'PM':"15:30:00-18:29:59",
                    'EV':"18:30:00-27:00:00"}
    gtfs.load()
    gtfs.apply_time_periods(time_periods)
    gtfs.standardize() # added this to use trip_headsign if direction_id is missing in trips.txt (Ex. 2012 AC Transit GTFS)
    gtfs.build_common_dfs()

    if not os.path.exists(outpath):
        os.mkdir(outpath)
        print outpath
    print "writing..."
    gtfs.route_statistics.to_csv(os.path.join(outpath,'route_statistics.csv'))
