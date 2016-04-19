import sys, os
import numpy as np
import pandas as pd
import shapefile
import pyproj
import shapely
from shapely.geometry import Point, Polygon
from itertools import izip
sys.path.insert(0,r'Y:\champ\util\pythonlib-migration\master_versions\gtfs_utils')
import gtfs_utils
import datetime

if __name__=='__main__':
##    args = sys.argv[1:]
##    gtfs_path = args[0]
##    ftfs_path = args[1]
    #gtfs_path = r'Q:\Model Development\SHRP2-fasttrips\Task2\gtfs\SFMTA_20120319'
    gtfs_path = r'Q:\Data\GTFS\ACTransit\GTFSFall12'
    ftfs_path = r'Q:\Model Development\SHRP2-fasttrips\Task2\built_fasttrips_network_2012Base\draft1.5'
    champ_to_gtfs_file = r''
    x_nearest = 4
    threshold = 50
    prj_wgs84 = pyproj.Proj("+init=EPSG:4326")
    prj_spca3 = pyproj.Proj("+init=EPSG:2227")
    conv_m_to_ft = 0.3048
    conv_ft_to_m = 1 / conv_m_to_ft
    
    print "initializing"
    gtfs = gtfs_utils.GTFSFeed(gtfs_path)
    ftfs = gtfs_utils.GTFSFeed(ftfs_path)
    
    print "importing gtfs"
    gtfs.load()
    print "importing gtfs-fasttrips"
    ftfs.load()

    print "standardizing gtfs"
    gtfs.standardize()
    print "standardizing gtfs-fasttrips"
    ftfs.standardize()
    print "calculating extras for gtfs"
    gtfs.build_common_dfs()
    print "calculating extras for gtfs-fasttrips"
    ftfs.build_common_dfs()

    gtfs.write(path='gtfs_gtfs')
    ftfs.write(path='fasttrips_gtfs')
    gtfs_stop_points = {}
    ftfs_stop_points = {}
    #gtfs.route_patterns.to_csv('gtfs_route_patterns.csv',index=False)
    #ftfs.route_patterns.to_csv('ftfs_route_patterns.csv',index=False)
    #sys.exit()
    #print gtfs.used_stops.columns
    
    print "converting gtfs stops to points"
    for i, stop in gtfs.stop_routes.iterrows():
        x, y = pyproj.transform(prj_wgs84, prj_spca3, stop['stop_lon'], stop['stop_lat'])
        x = x * conv_m_to_ft
        y = y * conv_m_to_ft
        point = Point(x,y)
        gtfs_stop_points[stop['stop_id']] = point

    print "converting gtfs-fasttrips stops to points"
    for i, stop in ftfs.stop_routes.iterrows():
        x, y = pyproj.transform(prj_wgs84, prj_spca3, stop['stop_lon'], stop['stop_lat'])
        x = x * conv_m_to_ft
        y = y * conv_m_to_ft
        point = Point(x,y)
        ftfs_stop_points[stop['stop_id']] = point

    # stop-to-stop distances, keep the nearest
    print "finding nearest stops"
    start = datetime.datetime.now()
    print start.isoformat()
    near_stops = {}
    near_stop_file = open('near_stop_file.csv','w')
    near_stop_file.write('gtfs_stop_id,champ_node_id,rank,distance\n')
    i = 0
    for l_stop_id, l_stop in gtfs_stop_points.iteritems():
        nearest_dists = []
        nearest_stops = []
        for r_stop_id, r_stop in ftfs_stop_points.iteritems():
            dist = l_stop.distance(r_stop)
            if dist > threshold: continue
            if len(nearest_dists) < x_nearest:
                nearest_dists.append(dist)
                nearest_stops.append(r_stop_id)
                nearest_dists.sort()
                nearest_stops.sort()
            elif dist < nearest_dists[x_nearest - 1]:
                for j in reversed(range(x_nearest)):
                    if dist >= nearest_dists[j]:
                        nearest_dists.insert(j+1, dist)
                        nearest_dists.pop()
                        nearest_stops.insert(j+1, r_stop_id)
                        nearest_stops.pop()
                        break
        if len(nearest_stops) == 0:
            near_stop_file.write('%s,,,\n' % str(l_stop_id))
            
        for k, s, d in izip(range(1, len(nearest_stops)+1), nearest_stops, nearest_dists):            
            #near_stops[((l_stop_id, k, s, d))
            near_stop_file.write('%s,%s,%d,%f\n' % (str(l_stop_id), str(s), k, d))
        i += 1
        if i % 100 == 0: print "%s matched %5d stops" % (datetime.datetime.now().isoformat(), i)
    stop = datetime.datetime.now()
    gtfs.used_stops.to_csv('gtfs_used_stops.csv')
    ftfs.used_stops.to_csv('fasttrips_used_stops.csv')
    
    near_stop_file.close()
    dur = stop - start
    print stop.isoformat()
    print dur