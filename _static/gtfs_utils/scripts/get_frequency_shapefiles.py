import sys, os
import numpy as np
import pandas as pd
sys.path.insert(0,r'Y:\champ\util\pythonlib-migration\master_versions\gtfs_utils')
import gtfs_utils
import shapefile

if __name__=='__main__':
    args = sys.argv[1:]
    path = args[0]
    tag = args[1]
    
    gtfs = gtfs_utils.GTFSFeed(path)
    print gtfs
    time_periods = {'00 to 01':"00:00:00-00:59:59",
                    '01 to 02':"01:00:00-01:59:59",
                    '02 to 03':"02:00:00-02:59:59",
                    '03 to 04':"03:00:00-03:59:59",
                    '04 to 05':"04:00:00-04:59:59",
                    '05 to 06':"05:00:00-05:59:59",
                    '06 to 07':"06:00:00-06:59:59",
                    '07 to 08':"07:00:00-07:59:59",
                    '08 to 09':"08:00:00-08:59:59",
                    '09 to 10':"09:00:00-09:59:59",
                    '10 to 11':"10:00:00-10:59:59",
                    '11 to 12':"11:00:00-11:59:59",
                    '12 to 13':"12:00:00-12:59:59",
                    '13 to 14':"13:00:00-13:59:59",
                    '14 to 15':"14:00:00-14:59:59",
                    '15 to 16':"15:00:00-15:59:59",
                    '16 to 17':"16:00:00-16:59:59",
                    '17 to 18':"17:00:00-17:59:59",
                    '18 to 19':"18:00:00-18:59:59",
                    '19 to 20':"19:00:00-19:59:59",
                    '20 to 21':"20:00:00-20:59:59",
                    '21 to 22':"21:00:00-21:59:59",
                    '22 to 23':"22:00:00-22:59:59",
                    '23 to 24':"23:00:00-23:59:59"
                    }
    tp_list = ['00 to 01', '01 to 02', '02 to 03', '03 to 04', '04 to 05', '05 to 06', '06 to 07', '07 to 08',
               '08 to 09', '09 to 10', '10 to 11', '11 to 12', '12 to 13', '13 to 14', '14 to 15', '15 to 16',
               '16 to 17', '17 to 18', '18 to 19', '19 to 20', '20 to 21', '21 to 22', '22 to 23', '23 to 24']
    print "loading gtfs"
    gtfs.load()

    print "conventionalizing"
    gtfs.standardize()
    
    #gtfs.routes = gtfs.routes[gtfs.routes['route_id'] == 7517]
    print "applying time periods"
    gtfs.apply_time_periods(time_periods)

    #gtfs.routes = gtfs.routes[gtfs.routes['route_id'] == 7517]
    print "building common dataframes"
    gtfs.build_common_dfs()
    print "writing route statistics"
##    late_night_routes = gtfs.route_statistics[(gtfs.route_statistics['freq'] > 0) & (gtfs.route_statistics['trip_departure_tp'] != 'other')]
##    late_night_routes.to_csv('%s_late_night_route_stats.csv' % tag)
    shape_ids = gtfs.route_trips['shape_id'].drop_duplicates().tolist()
    shapes = gtfs.shapes[gtfs.shapes['shape_id'].isin(shape_ids)]

    print "writing shapes"
##    shapes.to_csv('%s_late_night_shapes.csv' % tag)
    shape_freq = pd.merge(shapes, gtfs.route_patterns, how='left', on='shape_id')
    shape_freq = pd.DataFrame(shape_freq, columns=shapes.columns.tolist()+['pattern_id'])
    shape_freq = pd.merge(shape_freq, gtfs.route_statistics, how='left', on='pattern_id')
    #ln_freq = late_night_routes.fillna(-1)
    #ln_freq = ln_freq.set_index(['route_id','route_short_name','route_long_name','shape_id','direction_id'])
##    ln_freq = late_night_routes.pivot_table(index=['route_id','route_short_name','route_long_name','shape_id','direction_id'],
##                                            columns='trip_departure_tp',values='freq')
##    ln_freq.to_csv('%s_late_night_route_freqs.csv' % tag)
##    ln_freq = ln_freq.reset_index()
    #print ln_freq[ln_freq['shape_id'] == '40151']
##    shape_freq = pd.merge(shapes, ln_freq, how='left',on='shape_id')
##    shape_freq.to_csv('sfreq.csv')
    # write shapefile
    shape_writer = shapefile.Writer(shapeType=shapefile.POLYLINE)
    shape_writer.field('route_id',          'N',    10, 0)
    shape_writer.field('route_short_name',  'C',    10, 0)
    shape_writer.field('route_long_name',   'C',    50, 0)
    shape_writer.field('direction_id',      'C',    15,  0)
    shape_writer.field('shape_id',          'N',    10, 0)        
    for tp in tp_list:
        shape_writer.field(tp, 'N', 10, 0)

    for tp in tp_list:
        if tp not in shape_freq.columns.tolist():
            shape_freq[tp] = 0
            
    shape_id = None
    #print shape_freq[shape_freq['shape_id'] == '40182']
    #print shape_freq[shape_freq['shape_id'] == '40151']
    for i, shape in shape_freq.iterrows():
        if shape_id == None:
            route_id = shape['route_id']
            route_short_name =  shape['route_short_name']
            route_long_name = shape['route_long_name']
            direction_id = shape['direction_id']
            shape_id = shape['shape_id']
            tp_freqs = []
            for tp in tp_list:
                tp_freqs.append(shape['%s_freq' % tp])
            points = []
            
        if shape_id != shape['shape_id']:
            shape_writer.line([points])
            shape_writer.record(route_id, route_short_name, route_long_name, direction_id, shape_id, *tp_freqs)
            route_id = shape['route_id']
            route_short_name =  shape['route_short_name']
            route_long_name = shape['route_long_name']
            direction_id = shape['direction_id']
            shape_id = shape['shape_id']
            tp_freqs = []
            for tp in tp_list:
                tp_freqs.append(shape['%s_freq' % tp])
            points = []
            
        point = [shape['shape_pt_lon'],shape['shape_pt_lat']]
        points.append(point)
    # write the last one
    tp_freqs = []
    for tp in tp_list:
        tp_freqs.append(shape['%s_freq' % tp])
    shape_writer.line([points])
    shape_writer.record(shape['route_id'], shape['route_short_name'],
                        shape['route_long_name'], shape['direction_id'], shape['shape_id'], *tp_freqs)
    shape_writer.save('%s_late_night_service.shp' % tag)

    # write projection
    prj = open('%s_late_night_service.prj' % tag, "w")
    epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
    prj.write(epsg)
    prj.close()