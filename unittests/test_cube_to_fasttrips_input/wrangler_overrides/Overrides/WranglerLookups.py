import sys, os
##from Wrangler.Logger import WranglerLogger
##WranglerLogger.debug("IMPORTING OVERRIDING WranglerLookups FROM %s" % os.path.curdir)

class WranglerLookups:

    ALL_TIMEPERIODS = ["PM"]
    TIME_PERIOD_TOD_ORDER = ['PM']
    
    HOURS_PER_TIMEPERIOD = {"PM":3.0}
    
    MINUTES_PAST_MIDNIGHT = {"PM":900}

    TIMEPERIOD_TO_TIMERANGE = {'PM':('150000','175959')}
    
    MODETYPE_TO_MODES = {"Local":[11,12,16,17,18,19],
                         "BRT":[13,20],
                         "LRT":[14,15,21],
                         "Premium":[22,23,24,25,26,27,28,29,30],
                         "Ferry":[31],
                         "BART":[32]
                         }
    
    # Do these modes have offstreet stops?
    MODENUM_TO_OFFSTREET = {11:False, # muni bus
                            12:False, # muni Express bus
                            13:False, # mun BRT
                            14:False, # cable car -- These are special because they don't have explicity WNR nodes
                            15:False, # LRT       -- and are just implemented by reading the muni.xfer line as muni.access
                            16:False, # Shuttles
                            17:False, # SamTrans bus
                            18:False, # AC bus
                            19:False, # other local bus
                            20:False, # Regional BRT
                            21:True,  # Santa Clara LRT
                            22:False, # AC premium bus
                            23:False, # GG premium bus
                            24:False, # SamTrans premium bus
                            25:False, # Other premium bus
                            26:True,  # Caltrain
                            27:True,  # SMART
                            28:True,  # eBART
                            29:True,  # Regional Rail/ACE/Amtrak
                            30:True,  # HSR
                            31:True,  # Ferry
                            32:True   # BART
                            }
    
    MODE_TO_MODETYPE = {1:{'desc':"walk access", 'type':"non-transit"},
                        2:{'desc':"walk egress", 'type':"non-transit"},
                        3:{'desc':"drive access", 'type':"non-transit"},
                        4:{'desc':"drive egress", 'type':"non-transit"},
                        5:{'desc':"transfer", 'type':"non-transit"},
                        6:{'desc':"drive funnel", 'type':"non-transit"},
                        7:{'desc':"walk funnel", 'type':"non-transit"},
                        11:{'desc':"local_bus", 'type':"local_bus"},
                        12:{'desc':"express_bus", 'type':"express_bus"},
                        32:{'desc':"heavy_rail", 'type':"heavy_rail"},
                        }

    OFFBOARD_FTMODETYPES = ['commuter_rail','heavy_rail','regional_rail','inter_regional_rail','high_speed_rail','ferry']
    OFFBOARD_FTAGENCIES = []
    
    MODE_HEIRARCHY = [32, #:{'desc':"BART", 'type':"BART"},
                      12, #:{'desc':"Express Muni", 'type':"local bus"},
                      11, #:{'desc':"Local Muni", 'type':"local bus"},
                      ]
                      
    ACCESS_MODES        = [1,3,6,7]
    EGRESS_MODES        = [2,4]
    TRANSFER_MODES      = [5]
    UNUSED_MODES        = [8,9,10]
    NONTRANSIT_MODES    = [1,2,3,4,5,6,7]
    TRANSIT_MODES       = [11,12,32]
    NONTRANSIT_TYPES    = ['non-transit']
    TRANSIT_TYPES       = ['local_bus', 'express_bus', 'heavy_rail']
    
    OPERATOR_ID_TO_NAME = {'TNT':"tntransit",
                           'TNT_': "tntransit",
                           'BS_': "BlueSkyTransit"}

    OPERATOR_NAME_TO_URL = {'tntransit':'http://www.sfcta.org'}
    
    MODENUM_TO_FTMODETYPE = {11:'local_bus',
                             12:'express_bus',
                             13:'rapid_bus',
                             14:'cable_car',
                             15:'light_rail',
                             16:'open_shuttle',
                             17:'local_bus',
                             18:'local_bus',
                             19:'local_bus',
                             20:'rapid_bus',
                             21:'light_rail',
                             22:'premium_bus',
                             23:'premium_bus',
                             24:'premium_bus',
                             25:'premium_bus',
                             26:'commuter_rail',
                             27:'regional_rail',
                             28:'regional_rail',
                             29:'inter_regional_rail',
                             30:'high_speed_rail',
                             31:'ferry',
                             32:'heavy_rail'}

        ##Service type:
        ##0 - Tram, streetcar, light rail
        ##1 - Subway, metro
        ##2 - Rail
        ##3 - Bus
        ##4 - Ferry
        ##5 - Cable car
        ##6 - Gondola
        ##7 - Funicular
    MODENUM_TO_FTROUTETYPE = {11:3, # 'local_bus',
                              12:3, # 'express_bus',
                              13:3, # 'rapid_bus',
                              14:5, # 'cable_car',
                              15:0, # 'light_rail',
                              16:3, # 'open_shuttle',
                              17:3, # 'local_bus',
                              18:3, # 'local_bus',
                              19:3, # 'local_bus',
                              20:3, # 'rapid_bus',
                              21:0, # 'light_rail',
                              22:3, # 'premium_bus',
                              23:3, # 'premium_bus',
                              24:3, # 'premium_bus',
                              25:3, # 'premium_bus',
                              26:2, # 'commuter_rail',
                              27:2, # 'regional_rail',
                              28:2, # 'regional_rail',
                              29:2, # 'inter_regional_rail',
                              30:2, # 'high_speed_rail',
                              31:4, # 'ferry',
                              32:2, # 'heavy_rail'}
                              }

    MODENUM_TO_PROOF = {11:0, # {'desc':"Local Muni", 'type':"local bus"},
                        12:0, # {'desc':"Express Muni", 'type':"local bus"},
                        13:1, # {'desc':"BRT Muni", 'type':"local bus"},
                        14:0, # {'desc':"Muni Cable Car", 'type':"LRT"},
                        15:1, # {'desc':"LRT Muni", 'type':"LRT"},
                        16:1, # {'desc':"Free and Open Shuttles", 'type':"local bus"},
                        17:0, # {'desc':"SamTrans Local", 'type':"local bus"},
                        18:0, # {'desc':"AC Local", 'type':"local bus"},
                        19:0, # {'desc':"Other Local MTC Buses", 'type':"local bus"},
                        20:1, # {'desc':"Regional BRT", 'type':"BRT"},
                        21:1, # {'desc':"VTA LRT", 'type':"LRT"},
                        22:0, # {'desc':"AC Transbay Buses", 'type':"Premium"},
                        23:0, # {'desc':"Golden Gate Bus", 'type':"Premium"},
                        24:0, # {'desc':"Sam Trans Express Bus", 'type':"Premium"},
                        25:0, # {'desc':"Other Premium Bus", 'type':"Premium"},
                        26:1, # {'desc':"Caltrain", 'type':"Premium"},
                        27:1, # {'desc':"SMART", 'type':"Premium"},
                        28:1, # {'desc':"eBART", 'type':"Premium"},
                        29:0, # {'desc':"Regional Rail/ACE/AMTRAK", 'type':"Premium"},
                        30:0, # {'desc':"HSR", 'type':"Premium"},
                        31:1, # {'desc':"Ferry", 'type':"Ferry"},
                        32:0, # {'desc':"BART", 'type':"BART"},
                        }