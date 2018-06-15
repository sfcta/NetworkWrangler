'''
'''

import sys, os
import numpy as np
import pandas as pd
import shapefile
import itertools
import copy
import shapefile
import shapely
from shapely.geometry import Point, Polygon

def HHMMSS_to_MPM(hhmmss):
    sep = ':'
    if sep:
        hh, mm, ss = hhmmss.split(sep)
    else:
        hh = hhmmss[:2]
        mm = hhmmss[2:4]
        ss = hhmmss[4:]

    return 60 * int(hh) + int(mm) + float(ss)/60

def HHMMSSpair_to_MPMpair(hhmmsspair):
    if hhmmsspair == np.nan: return (np.nan, np.nan)
    hhmmss1, hhmmss2 = hhmmsspair.split('-')
    mpm1 = HHMMSS_to_MPM(hhmmss1)
    mpm2 = HHMMSS_to_MPM(hhmmss2)
    if mpm2 < mpm1: mpm2 += 24*60
    return (mpm1,mpm2)

class GTFSFeed(object):
    def __init__(self, path='.',agency='agency.txt',calendar='calendar.txt',calendar_dates='calendar_dates.txt',fare_attributes='fare_attributes.txt',
                 fare_rules='fare_rules.txt',routes='routes.txt',shapes='shapes.txt',stop_times='stop_times.txt',stops='stops.txt',
                 trips='trips.txt',weekday_only=True, segment_by_service_id=True):
        # GTFS files
        self.path           = path

        self.all_files = [agency, calendar, calendar_dates, fare_attributes, fare_rules, routes, shapes, stop_times, stops, trips]
        self.all_names = ['agency','calendar','calendar_dates','fare_attributes','fare_rules','routes','shapes','stop_times','stops','trips']
        
        self.agency         = None
        self.calendar       = None
        self.calendar_dates = None
        self.fare_attributes= None
        self.fare_rules     = None
        self.routes         = None
        self.shapes         = None
        self.stop_times     = None
        self.stops          = None
        self.trips          = None

        # settings
        self.has_time_periods       = False
        self.weekday_only           = weekday_only
        self.segment_by_service_id  = segment_by_service_id

        # initialize other vars
        self.time_periods           = None
        self.stop_sequence_cols     = None
        self.weekday_service_ids    = None
        self.used_stops             = None

        self.route_trips            = None
        self.route_patterns         = None
        self.patterns               = None
        self.route_statistics       = None
        self.stop_statistics        = None
        self.route_stops            = None
        #self.stop_route             = None

        # standard index columns to be used for grouping
        self._route_trip_idx_cols   = ['route_id','trip_id','service_id','shape_id','direction_id','route_short_name','route_long_name','route_desc']
        self._route_dir_idx_cols    = ['route_id','route_short_name','route_long_name','direction_id']
        self._trip_idx_cols         = ['trip_id','direction_id']
        self._tp_idx_cols           = []
        self._route_pattern_info_cols = []

    def load(self, encoding=None):
        for name, file in itertools.izip(self.all_names, self.all_files):
            try:
                self.__dict__[name] = pd.read_csv(os.path.join(self.path,file),encoding=encoding)
            except:
                print "%s not found in %s" % (file, self.path)
                
        # Useful GTFS manipulations
        self.weekday_service_ids= self._get_weekday_service_ids()
        if self.weekday_only:
            self.trips = self.trips[self.trips['service_id'].isin(self.weekday_service_ids)]
            self.stop_times = self.stop_times[self.stop_times['trip_id'].isin(self.trips['trip_id'].tolist())]
        
        self.stop_sequence_cols = self._get_stop_sequence_cols()
        self.used_stops         = self._get_used_stops()

    def write(self, path='.', ext=None):
        for name, file in itertools.izip(self.all_names, self.all_files):
            try:
                if isinstance(ext, str):
                    if ext[0] != '.': ext = '.' + ext
                    file = file.replace('.txt',ext)
                if not os.path.exists(path):
                    os.mkdir(path)
                if os.path.exists(os.path.join(path,file)):
                    response = raw_input("(y/n) overwrite file at %s" % os.path.join(path, file))
                    if not response.lower() in ['y','yes']: continue
                self.__dict__[name].to_csv(os.path.join(path,file), index=False)
            except Exception as e:
                print 'error writing file %s to path %s: %s' % (file, path, e)

##    def export_shapefiles(path='.', routes='routes.shp', stops='stops.shp'):
##        shape_writer = shapefile.Writer(shapeType=shapefile.POLYLINE)
##        shape_writer.field('route_id',          'N',    10, 0)
##        shape_writer.field('route_short_name',  'C',    10, 0)
##        shape_writer.field('route_long_name',   'C',    50, 0)
##        shape_writer.field('direction_id',      'N',    1,  0)
##        shape_writer.field('shape_id',          'N',    10, 0)
##        if isinstance(self.shapes, pd.DataFrame):
##            for i, shape in self.shapes.iterrows():
##                if shape_id == None:
##                    route_id = shape['route_id']
##                    route_short_name =  shape['route_short_name']
##                    route_long_name = shape['route_long_name']
##                    direction_id = shape['direction_id']
##                    shape_id = shape['shape_id']
##                    points = []
##                if shape_id != shape['shape_id']:
##                    shape_writer.line([points])
##                    shape_writer.record(route_id, route_short_name, route_long_name, direction_id, shape_id)
##                    route_id = shape['route_id']
##                    route_short_name =  shape['route_short_name']
##                    route_long_name = shape['route_long_name']
##                    direction_id = shape['direction_id']
##                    shape_id = shape['shape_id']
##                    points = []
##                point = [shape['shape_pt_lon'],shape['shape_pt_lat']]
##                points.append(point)
##            shape_writer.line([points])
##            shape_writer.record(shape['route_id'], shape['route_short_name'],
##                                shape['route_long_name'], shape['direction_id'], shape['shape_id'])
##            shape_writer.save(os.path.join(path,routes))
##        elif isinstance(self.route_stops, pd.DataFrame):
##            for i, route in self.routes.iterrows():
##                if route_id == None:
##                    route_id = route['route_id']
##                    route_short_name =  route['route_short_name']
##                    route_long_name = route['route_long_name']
##                    direction_id = route['direction_id']
##                    points = []
##                if route_id != route['route_id']:
##                    route_writer.line([points])
##                    route_writer.record(route_id, route_short_name, route_long_name, direction_id, route_id)
##                    route_id = route['route_id']
##                    route_short_name =  route['route_short_name']
##                    route_long_name = route['route_long_name']
##                    direction_id = route['direction_id']
##    
##                    points = []
##                point = [route['shape_pt_lon'],shape['shape_pt_lat']]
##                points.append(point)
##            shape_writer.line([points])
##            shape_writer.record(shape['route_id'], shape['route_short_name'],
##                                shape['route_long_name'], shape['direction_id'], shape['shape_id'])
##            shape_writer.save(os.path.join(path,routes))
            
    def standardize(self, dir_col='trip_headsign'):
        self._drop_stops_no_times()
        if 'direction_id' not in self.trips.columns.tolist():
            # changed Bhargav 4/5/2016
            # Let's try trip_headsign and see if it helps in case of AC Transit
            if dir_col in self.trips.columns:
                self.trips['direction_id'] = self.trips[dir_col]
            else:
                self.trips['direction_id'] = 0 
        #self._assign_direction()
    
    def build_common_dfs(self):
        # common groupings
        #   route_trips routes->trips
        self.route_trips        = pd.merge(self.routes,self.trips,on=['route_id'])
        #   stop_routes used_stops->stop_times->trips->routes, keep only stop and route columns
        self.stop_routes        = pd.merge(self.used_stops, self.stop_times, on=['stop_id'])
        self.stop_routes        = pd.merge(self.stop_routes, self.trips, on=['trip_id'])
        self.stop_routes        = pd.merge(self.stop_routes, self.routes, on=['route_id'])
        self.stop_routes        = pd.DataFrame(self.stop_routes,columns=self.stops.columns.tolist()+self.routes.columns.tolist()+['direction_id'])
        self.stop_routes        = self.stop_routes.drop_duplicates()
        
        self.route_patterns     = self._get_route_patterns()
        self.route_patterns     = self._get_similarity_index(self.route_patterns, idx_cols=['route_id','direction_id'])
        non_stop_seq_cols = [x for x in self.route_patterns.columns if x not in self.stop_sequence_cols]
        self.route_patterns = pd.DataFrame(self.route_patterns, columns=non_stop_seq_cols+self.stop_sequence_cols)
        pattern_ids = self.route_patterns['pattern_id'].drop_duplicates().tolist()
        self.trip_patterns      = self.trips[self.trips['trip_id'].isin(pattern_ids)]
        self.stop_patterns      = self.stop_times[self.stop_times['trip_id'].isin(pattern_ids)]
        self.stop_patterns      = pd.merge(self.stop_patterns, self.stops, on='stop_id')
        self.stop_patterns      = self.stop_patterns.sort(['trip_id','stop_sequence'])

        ##if self.has_time_periods == False:
        sp1 = self.stop_patterns.pivot(index='trip_id',columns='stop_sequence',values='stop_id').reset_index()
        for col in self.stop_sequence_cols:
            if col not in sp1.columns.tolist():
                sp1[col] = np.nan

        sp1 = sp1.fillna(-1).set_index(self.stop_sequence_cols)
        sp2 = self.stop_times.pivot(index='trip_id',columns='stop_sequence',values='stop_id').reset_index()
        for col in self.stop_sequence_cols:
            if col not in sp2.columns.tolist():
                sp2[col] = np.nan
                           
        sp2 = sp2.fillna(-1).set_index(self.stop_sequence_cols)

        sp2['pattern_id'] = sp1['trip_id']
        sp2 = sp2.reset_index().set_index(['trip_id'])
        self.route_trips = self.route_trips.set_index(['trip_id'])
        self.route_trips['pattern_id'] = sp2['pattern_id']
        trips_with_departure = self.get_trip_departure_times(self.trips, self.stop_times)
        trips_with_departure = trips_with_departure.set_index(['trip_id'])
        self.route_trips['trip_departure_time'] = trips_with_departure['trip_departure_time']
        self.route_trips['trip_departure_mpm'] = trips_with_departure['trip_departure_mpm']
        self.route_trips = self.route_trips.reset_index()
    
        #self.route_trips.to_csv('route_trips.csv')
        # statistics
        self.route_statistics   = self._get_route_statistics() # frequency by route
        self.stop_statistics    = self._get_stop_statistics() # # lines by route,

        self.all_files += ['route_trips.txt', 'stop_routes.txt', 'route_patterns.txt', 'trip_patterns.txt', 'stop_patterns.txt', 'route_statistics.txt', 'stop_statistics.txt']
        self.all_names += ['route_trips', 'stop_routes', 'route_patterns', 'trip_patterns', 'stop_patterns', 'route_statistics', 'stop_statistics']

    def get_route_statistics(self, pivot_timeperiods=True):
        self.route_statistics = self._get_route_statistics(pivot_timeperiods)
        return self.route_statistics
    
    def spatial_match_stops(self, left, right):
        pass
        
    def _drop_stops_no_times(self):
        self.stop_times = self.stop_times[(pd.isnull(self.stop_times['arrival_time']) != True)
                                          & (pd.isnull(self.stop_times['departure_time']) != True)]

    def drop_weekend(self):
        self.weekday_only = True
        self.trips = self.trips[self.trips['service_id'].isin(self.weekday_service_ids)]
        self.route_statistics = self.route_statistics[self.route_statistics['service_id'].isin(self.weekday_service_ids)]
        self.route_patterns = self.route_patterns[self.route_patterns['service_id'].isin(self.weekday_service_ids)]
        
    def drop_days(self, days=['saturday','sunday']):
        service_ids = []
        for day in days:
            service_ids += self.get_service_ids_by_day(day)
        self.trips = self.trips[self.trips['service_id'].isin(service_ids) != True]
        self.route_statistics = self.route_statistics[self.route_statistics['service_id'].isin(service_ids) != True]
        self.route_patterns = self.route_patterns[self.route_patterns['service_id'].isin(service_ids) != True]
        
    def get_service_ids_by_day(self, day='monday'):
        service_ids = self.calendar[self.calendar[day] == 1]['service_id'].tolist()
        return list(set(service_ids))
    
    def _get_weekday_service_ids(self, weekdays=['monday','tuesday','wednesday','thursday','friday']):
        weekday_service_ids = []
        for day in weekdays:
            weekday_service_ids += self.calendar[self.calendar[day] == 1]['service_id'].tolist()
        weekday_service_ids = list(set(weekday_service_ids))
        return weekday_service_ids

    def _get_used_stops(self):
        used_stops = pd.DataFrame(self.stop_times,columns=['stop_id'])
        used_stops = used_stops.drop_duplicates()
        used_stops['used_flag'] = 1
        used_stops = used_stops.set_index('stop_id')
        stops = self.stops.set_index('stop_id')
        stops['used_flag'] = used_stops['used_flag']
        stops = stops[stops['used_flag'] == 1]
        stops = stops.reset_index()
        return stops

    def get_trip_departure_times(self, trips, stop_times):
        first_stops = stop_times.groupby('trip_id')
        for name, group in first_stops:
            stop_time = group.loc[group['stop_sequence'].idxmin(),'arrival_time']
            trips.loc[trips['trip_id']==name,'trip_departure_time'] = stop_time
        trips['trip_departure_mpm'] = trips['trip_departure_time'].map(HHMMSS_to_MPM)
        return trips
    
    def apply_time_periods(self, time_periods):
        # update column collections
        self._tp_idx_cols += ['trip_departure_tp']
        self.time_periods = time_periods
        self.has_time_periods = True        
        if time_periods != None and not isinstance(time_periods,list) and not isinstance(time_periods,dict):
            raise Exception("time_periods MUST be None-type OR list-type of HH:MM:SS-HH:MM:SS pairs")

        self.stop_times['arr_mpm'] = self.stop_times['arrival_time'].map(HHMMSS_to_MPM)
        self.stop_times['dep_mpm'] = self.stop_times['departure_time'].map(HHMMSS_to_MPM)
        self.stop_times['arr_tp'] = 'other'
        self.stop_times['dep_tp'] = 'other'
        if isinstance(time_periods, list):
            ntp = {}
            for ctp in time_periods:
                ntp['%s' % ctp] = ctp
            time_periods = ntp

        for key, value in time_periods.iteritems():
            tp_name = key
            tp_start, tp_end = HHMMSSpair_to_MPMpair(value)
            arr_idx = self.stop_times[(self.stop_times['arr_mpm'].between(tp_start,tp_end))
                                      | (self.stop_times['arr_mpm'].between(tp_start-24*60,tp_end-24*60))
                                      | (self.stop_times['arr_mpm'].between(tp_start+24*60,tp_end+24*60))].index
            dep_idx = self.stop_times[(self.stop_times['dep_mpm'].between(tp_start,tp_end))
                                      | (self.stop_times['dep_mpm'].between(tp_start-24*60,tp_end-24*60))
                                      | (self.stop_times['dep_mpm'].between(tp_start+24*60,tp_end+24*60))].index
            self.stop_times.loc[arr_idx,'arr_tp'] = key
            self.stop_times.loc[dep_idx,'dep_tp'] = key

        first_stop = self.stop_times.groupby(['trip_id']).first()
        self.trips = self.trips.set_index(['trip_id'])
        self.trips['trip_departure_time'] = first_stop['departure_time']
        self.trips['trip_departure_mpm'] = first_stop['dep_mpm']
        self.trips['trip_departure_tp'] = first_stop['dep_tp']
        self.trips = self.trips.reset_index()
                
    def _get_route_statistics(self, pivot_timeperiods=True):
        grouped = self.route_trips.fillna(-1).groupby(self._route_dir_idx_cols+['service_id','pattern_id']+self._tp_idx_cols)
        rte_dir_pattern_tp_cols = self._route_dir_idx_cols+['service_id','pattern_id']+self._tp_idx_cols
        rte_dir_pattern_cols    = self._route_dir_idx_cols+['service_id','pattern_id']
        # calculate average headways / frequencies based on number of runs and length of time period
        route_statistics = grouped.sum()
        route_statistics = pd.DataFrame(route_statistics,columns=[])
        route_statistics['trips'] = grouped.size()
        route_statistics['shape_id'] = grouped.first()['shape_id']
        route_statistics = route_statistics.reset_index()
        
        if self.has_time_periods:
            for tp, hhmmsspair in self.time_periods.iteritems():
                start, stop = HHMMSSpair_to_MPMpair(hhmmsspair)
                length = round(stop-start,0)
                route_statistics.loc[route_statistics['trip_departure_tp'] == tp,'period_len_minutes'] = length
            route_statistics = route_statistics.set_index(self._route_dir_idx_cols+['service_id','pattern_id']+self._tp_idx_cols)
            route_statistics['freq'] = 60 * route_statistics['trips'] / route_statistics['period_len_minutes']
            route_statistics['avg_headway'] = route_statistics['period_len_minutes'] / route_statistics['trips']
            if pivot_timeperiods:
                route_statistics = route_statistics.reset_index()
                pivot = route_statistics.pivot_table(index=self._route_dir_idx_cols+['service_id','pattern_id'],columns=self._tp_idx_cols,values=['trips','freq','avg_headway'])
                route_statistics = pd.DataFrame(self.route_patterns,columns=self._route_dir_idx_cols+['service_id','pattern_id']+self._route_pattern_info_cols)
                for col in self._route_dir_idx_cols:
                    route_statistics[col] = route_statistics[col].fillna(-1)
                route_statistics = route_statistics.set_index(self._route_dir_idx_cols+['service_id','pattern_id'])
                for stat in ['trips','freq','avg_headway']:
                    for tp in self.time_periods.iterkeys():
                        route_statistics['%s_%s' % (tp, stat)] = pivot[stat][tp]
        else:
            route_statistics['freq'] = route_statistics['trips'] / 24
            route_statistics['avg_headway'] = 60 / route_statistics['freq']

        # calculate average headways and headway variation from actual headways
        sorted_trips = self.route_trips.sort(self._route_dir_idx_cols+['pattern_id','trip_departure_mpm'])
        for col in self._route_dir_idx_cols:
            sorted_trips[col] = sorted_trips[col].fillna(-1)
        sorted_trips['next_departure'] = sorted_trips['trip_departure_mpm'].shift(-1)
        sorted_trips['next_pattern'] = sorted_trips['pattern_id'].shift(-1)
        sorted_trips = sorted_trips[sorted_trips['pattern_id'] == sorted_trips['next_pattern']]
        sorted_trips['headway'] = sorted_trips['next_departure'] - sorted_trips['trip_departure_mpm']
        sorted_trips['outlier'] = 0
        
        if sorted_trips['headway'].lt(0).sum() > 0:
            print "sorted trips have negative headways"
            print sorted_trips[sorted_trips['headway'].lt(0)]
            #sys.exit()

        # find outliers (ex. large gaps in service for routes that only run in peak)
        grouped = sorted_trips.groupby(self._route_dir_idx_cols+['pattern_id']+self._tp_idx_cols)
        minmax = []
        for name, group in grouped:
            # drop the min and max headways
            idxmin = group['headway'].idxmin()
            idxmax = group['headway'].idxmax()
            minmax.append(idxmin)
            minmax.append(idxmax)

        no_min_max = sorted_trips[~sorted_trips.index.isin(minmax)]
        test = no_min_max.groupby(self._route_dir_idx_cols+['service_id','pattern_id']+self._tp_idx_cols)['headway'].agg([np.mean,np.std])

        for name, group in grouped:
            if name not in test.index: continue
            outliers = group[group['headway'] > (test.loc[name,'mean'] * 2)]
            if len(outliers > 0):
                sorted_trips.loc[outliers.index,'outlier'] = 1

        #sorted_trips.to_csv('sorted_trips.csv')
        sorted_trips = sorted_trips[sorted_trips['outlier'] == 0]

        calc_headways = sorted_trips.groupby(self._route_dir_idx_cols+['service_id','pattern_id']+self._tp_idx_cols)
        calc_headways = calc_headways['headway'].agg([np.mean, np.std, np.median, np.min, np.max])

        if self.has_time_periods:
            if pivot_timeperiods:
                pivot = calc_headways.reset_index().pivot_table(index=self._route_dir_idx_cols+['service_id','pattern_id'],columns=self._tp_idx_cols,values=['mean','std','median','amin','amax'])
                for stat in ['mean','std','median','amin','amax']:
                    for tp in self.time_periods.iterkeys():
                        route_statistics['%s_%s_headway' % (tp, stat)] = pivot[stat][tp]
        route_statistics.to_csv('route_stats.csv')
        route_statistics = route_statistics.reset_index()
        return route_statistics

    def _get_stop_statistics(self):
        # number of routes serving stop
        stop_stats = pd.DataFrame(self.stops.set_index(['stop_id']))
        grouped = self.stop_routes.groupby(['stop_id'])
        dir_size = self.stop_routes.groupby(['stop_id','direction_id']).size().reset_index().pivot(index='stop_id',columns='direction_id',values=0)
        stop_stats['num_routes'] = grouped.size()
        stop_stats['num_routes_outbound'] = dir_size[0] if 0 in dir_size.columns.tolist() else 0
        stop_stats['num_routes_inbound'] = dir_size[1] if 1 in dir_size.columns.tolist() else 0

##        # frequency of routes serving stop
##        grouped = self.stop_times.groupby(['stop_id','route_id','direction_id'])
##        stop_stats['avg_freq']
##        stop_stats['avg_freq_outbound']
##        stop_stats['avg_freq_inbound']
        return stop_stats
        
    def _get_route_patterns(self):
        trip_route = pd.merge(self.routes,self.trips,on='route_id')
        trip_route = pd.DataFrame(trip_route,columns=self._route_trip_idx_cols)
        patterns = self.stop_times.pivot(index='trip_id',columns='stop_sequence',values='stop_id')
        patterns = patterns.reset_index()
        if not self.stop_sequence_cols:
            self.stop_sequence_cols = self._get_stop_sequence_cols()
            
        route_pattern = pd.merge(trip_route, patterns, on='trip_id')
        columns = route_pattern.columns.tolist()
        columns.remove('trip_id')
        columns.remove('shape_id')

        # get the count of trips of this pattern for this route
        route_pattern = route_pattern.fillna(-1)
        grouped_route_pattern = route_pattern.groupby(columns)
        route_pattern = grouped_route_pattern.count()
        route_pattern['count'] = route_pattern['trip_id']
        route_pattern['shape_id'] = grouped_route_pattern.first()['shape_id']
        route_pattern['trip_id'] = grouped_route_pattern.first()['trip_id']

        # sometimes the same pattern shows up under multiple routes (why? prob out of service nonsense)
        # so just keep one pattern that all those routes can use.
        route_pattern = route_pattern.reset_index().set_index(self.stop_sequence_cols)
        grouped_patterns = patterns.fillna(-1).groupby(self.stop_sequence_cols)
        route_pattern['pattern_id'] = grouped_patterns.first()['trip_id']
        route_pattern = route_pattern.reset_index()
        route_pattern = route_pattern.replace(-1, np.nan)

        return route_pattern

    def _get_trip_id_to_pattern_id(self):
        trip_stops = pd.merge(self.trips, self.stop_patterns, on=['trip_id'])
        trip_stop_patterns = trip_stops.pivot(index='trip_id',columns='stop_sequence',values='stop_id')
        pattern_stop_patterns = self.stop_patterns.pivot(index='trip_id',columns='stop_sequence',values='stop_id')

        trip_stop_patterns = trip_stop_patterns.reset_index().set_index(self.stop_sequence_cols)
        pattern_stop_patterns = pattern_stop_patterns.reset_index().set_index(self.stop_sequence_cols)
        trip_stop_patterns['pattern_id'] = pattern_stop_patterns['trip_id']
        trip_stop_patterns = trip_stop_patterns.reset_index()
        trip_stop_patterns = pd.DataFrame(trip_stop_patterns,columns=self._route_trip_idx_cols+['pattern_id'])
        return trip_to_pattern
    
    def _get_stop_sequence_cols(self):
        stop_sequence_cols = list(set(self.stop_times['stop_sequence'].tolist()))
        return stop_sequence_cols
        
    def _get_similarity_index(self, route_patterns, idx_cols=['route_id','direction_id']):
        # figure out which pattern is the 'base' pattern
        grouped = route_patterns.groupby(idx_cols)
        route_patterns['total_base_stops'] = 0
        route_patterns['similar_base_stops'] = 0
        route_patterns['similarity_index'] = 0
        route_patterns['is_base_pattern'] = 0
        self._route_pattern_info_cols = ['is_base_pattern','similarity_index']
        
        for name, group in grouped:
            this_group = pd.DataFrame(group,columns=self.stop_sequence_cols+['count'])
            # assume the pattern that shows up the most is the base route
            maxrow = this_group[this_group.index == this_group['count'].idxmax()]
            if len(maxrow) > 1:
                print "maxrow contains multiple records, selecting first"
                maxrow = maxrow[0]
            route_patterns.loc[this_group['count'].idxmax(),'is_base_pattern'] = 1
            route_patterns.loc[this_group.index,'total_base_stops'] = maxrow.loc[:,self.stop_sequence_cols].T.count().sum()
            route_patterns.loc[this_group.index,'similar_base_stops'] = this_group.loc[:,self.stop_sequence_cols].eq(maxrow.loc[:,self.stop_sequence_cols].values.tolist()[0]).T.sum()
        route_patterns['similarity_index'] = route_patterns['similar_base_stops'] / route_patterns['total_base_stops']
        
        return route_patterns
        
    def __str__(self):
        ret = 'GTFS Feed at %s containing:' % self.path
        i = 0
        for key, value in self.__dict__.items():
            if not key.startswith('__'):
                if not isinstance(value, pd.DataFrame):
                    continue
                if i == 0:
                    ret = ret + '\n%s' % (key)
                    i += 1
                else:
                    ret = ret + ', %s' % (key)
        return ret


##    def is_aligned_stop_sequence(self):
##        '''
##        return true if there is a set correspondence between stop_id and stop_sequence for all routes
##        '''
##        pass
##
##    def align_stop_sequence(self):
##        '''
##        reassign stop_sequences so there is a unique correspondence between stop_id and stop_sequence for all routes
##        '''
##        rts = pd.merge(self.routes, self.trips, on=['route_id'])
##
##    def drop_deadheads(self, freq_threshold=0.25, similarity_threshold=0.5, how='and'):
##        if how == 'and':
##            pass
##
##        elif how == 'or':
##            pass
##        

if __name__=='__main__':
    gtfs = GTFSFeed('..\SFMTA_20120319')
    print gtfs
    time_periods = {'EA':"03:00:00-05:59:59",
                    'AM':"06:00:00-08:59:59",
                    'MD':"09:00:00-15:29:59",
                    'PM':"15:30:00-18:29:59",
                    'EV':"18:30:00-27:00:00"}
    
    gtfs.apply_time_periods(time_periods)
    gtfs.set_route_patterns()
    route_patterns = gtfs.get_route_patterns()
    print route_patterns[0:10]
    
    
    