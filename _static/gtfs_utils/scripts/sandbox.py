import sys, os
import pandas as pd
import numpy as np
import shapefile

if __name__=='__main__':
    args = sys.argv[1:]
    if args[0] == 'SFMTA':
        path = 'SFMTA_20120319'
    if args[0] == 'AC':
        path = 'ACTransit_2012'
    if args[0] == 'VTA':
        path = 'VTA'

    print 'reading files for %s from %s' % (args[0], path)
    routes = pd.read_csv(os.path.join(path,'routes.txt'))
    trips = pd.read_csv(os.path.join(path,'trips.txt'))
    trips = trips[trips['service_id']==1]
    stop_times = pd.read_csv(os.path.join(path,'stop_times.txt'))
    shapes = pd.read_csv(os.path.join(path,'shapes.txt'))
    stops = pd.read_csv(os.path.join(path,'stops.txt'))
    
    print 'merging trips and routes'
    trip_route = pd.merge(routes,trips,on='route_id')
    trip_route = trip_route.reset_index()
    trip_route_sequence = pd.DataFrame(trip_route,columns=['route_id','trip_id','shape_id','direction_id','route_short_name','route_long_name','route_desc'])
    print 'getting stop sequences'
    sequences = stop_times.pivot(index='trip_id',columns='stop_sequence',values='stop_id')
    sequences = sequences.reset_index()
    print 'merging sequences with routes'
    trip_route_sequence = pd.merge(trip_route_sequence, sequences, on='trip_id')
    trip_route_sequence = trip_route_sequence.reset_index()
    #print 'trip_route_sequence cols:', trip_route_sequence.columns
    print 'getting unique sequences'
    #print trip_route_sequence.columns
    route_sequence = pd.DataFrame(trip_route_sequence)
    columns = route_sequence.columns.tolist()
    columns.remove('trip_id')
    columns.remove('index')
    columns.remove('shape_id')

    #route_sequence = trip_route_sequence.drop('trip_id',axis=1)
    #route_sequence = route_sequence.drop('index',axis=1)
    #print 'route_sequence cols:', route_sequence.columns
    route_sequence = route_sequence.fillna(-1)
    grouped_route_sequence = route_sequence.groupby(columns)
    route_sequence = grouped_route_sequence.count()

    route_sequence['count'] = route_sequence['trip_id']
    route_sequence['trip_id'] = grouped_route_sequence.first()['trip_id']
    route_sequence['shape_id'] = grouped_route_sequence.first()['shape_id']
    route_sequence = route_sequence.reset_index()
    route_sequence = route_sequence.replace(-1, np.nan)
    #route_sequence = route_sequence.drop_duplicates(subset=columns)
    #raw_input('press enter')
    #print route_sequence
    #raw_input('hit enter')
##    print 'counting unique sequences'
##    route_sequence_count = route_sequence.groupby(['route_id','shape_id']).count()
##    route_sequence_count = route_sequence_count.reset_index()
##    route_sequence_count['count'] = route_sequence_count['route_short_name']
##    route_sequence_count = pd.DataFrame(route_sequence_count,columns=['route_id','shape_id','count'])
    #print route_sequence.columns
    #print route_sequence_count.columns
##    route_sequence = pd.merge(route_sequence, route_sequence_count,how='left',on=['route_id','shape_id'])
    print 'writing to file'
    route_sequence = route_sequence.sort(columns=['route_short_name','route_long_name','direction_id'])
    route_sequence.to_csv('%s_route_sequence.csv' % args[0], index=False)
    route_sequence = pd.DataFrame(route_sequence,columns=['route_id','trip_id','shape_id','route_short_name','route_long_name','route_desc','direction_id','count'])
    print 'writing representative trip id correspondence file'
    route_sequence.to_csv('%s_route_to_repr_trip_ids.csv' % args[0], index=False)
    repr_trips = pd.merge(route_sequence,stop_times,how='left',on='trip_id')
    repr_trips = pd.merge(repr_trips,stops,how='left',on='stop_id')
    repr_trips = repr_trips.reset_index()
    print 'writing representative trip id shapes file'
    repr_trips = repr_trips.sort(columns=['route_id','route_short_name','route_long_name','direction_id','trip_id','stop_sequence'])
    repr_trips.to_csv('%s_repr_trips.csv' % args[0], index=False)
    
    print 'writing shapefile'
    shape_writer = shapefile.Writer(shapeType=shapefile.POLYLINE)
    shape_writer.field('route_id',          'N',    10, 0)
    shape_writer.field('route_short_name',  'C',    10, 0)
    shape_writer.field('route_long_name',   'C',    50, 0)
    shape_writer.field('direction_id',      'N',    1,  0)
    shape_writer.field('trip_id',           'N',    10, 0)
    shape_writer.field('shape_id',          'N',    10, 0)
    shape_writer.field('count',             'N',    10, 0)

    for i, route in route_sequence.iterrows():
        route_stops = repr_trips[repr_trips['trip_id'] == route['trip_id']]
        points = []
        for j, stop in route_stops.iterrows():
            point = [0,0]
            point[0] = stop['stop_lon']
            point[1] = stop['stop_lat']
            points.append(point)
        shape_writer.line([points])
        shape_writer.record(route['route_id'],route['route_short_name'],route['route_long_name'],route['direction_id'],route['trip_id'],route['shape_id'],route['count'])
    shape_writer.save('%s_repr_trips.shp' % args[0])
        

    
    
    
    