class WranglerLookups:

    ALL_TIMEPERIODS = ["AM","MD","PM","EV","EA"]
    
    TIME_PERIOD_TOD_ORDER = ["EA","AM","MD","PM","EV"]
    
    HOURS_PER_TIMEPERIOD = {"AM":3.0, #what about 4-6a?
                            "MD":6.5,
                            "PM":3.0,
                            "EV":8.5,
                            "EA":3.0
                            }
    
    MINUTES_PAST_MIDNIGHT = {"AM":360, # 6am - 9am
                             "MD":540, # 9am - 3:30pm
                             "PM":930, # 3:30pm - 6:30pm
                             "EV":1110,# 6:30pm - 3am
                             "EA":180, # 3am - 6am
                             }

    TIMEPERIOD_TO_TIMERANGE = {'AM':('06:00:00','09:00:00'),
                               'MD':('09:00:00','15:30:00'),
                               'PM':('15:30:00','18:30:00'),
                               'EV':('18:30:00','27:00:00'),
                               'EA':('03:00:00','06:00:00')}

    TIMEPERIOD_TO_MPMRANGE = {'AM':(360,540),
                              'MD':(540,930),
                              'PM':(930,1110),
                              'EV':(1110,1620),
                              'EA':(180,360)}
    
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
                        8:{'desc':None, 'type':None},
                        9:{'desc':None, 'type':None},
                        10:{'desc':None, 'type':None},
                        11:{'desc':"Local Muni", 'type':"local bus"},
                        12:{'desc':"Express Muni", 'type':"local bus"},
                        13:{'desc':"BRT Muni", 'type':"local bus"},
                        14:{'desc':"Muni Cable Car", 'type':"LRT"},
                        15:{'desc':"LRT Muni", 'type':"LRT"},
                        16:{'desc':"Free and Open Shuttles", 'type':"local bus"},
                        17:{'desc':"SamTrans Local", 'type':"local bus"},
                        18:{'desc':"AC Local", 'type':"local bus"},
                        19:{'desc':"Other Local MTC Buses", 'type':"local bus"},
                        20:{'desc':"Regional BRT", 'type':"BRT"},
                        21:{'desc':"VTA LRT", 'type':"LRT"},
                        22:{'desc':"AC Transbay Buses", 'type':"Premium"},
                        23:{'desc':"Golden Gate Bus", 'type':"Premium"},
                        24:{'desc':"Sam Trans Express Bus", 'type':"Premium"},
                        25:{'desc':"Other Premium Bus", 'type':"Premium"},
                        26:{'desc':"Caltrain", 'type':"Premium"},
                        27:{'desc':"SMART", 'type':"Premium"},
                        28:{'desc':"eBART", 'type':"Premium"},
                        29:{'desc':"Regional Rail/ACE/AMTRAK", 'type':"Premium"},
                        30:{'desc':"HSR", 'type':"Premium"},
                        31:{'desc':"Ferry", 'type':"Ferry"},
                        32:{'desc':"BART", 'type':"BART"},
                        }

    MODE_HEIRARCHY = [30, #:{'desc':"HSR", 'type':"Premium"},
                      29, #:{'desc':"Regional Rail/ACE/AMTRAK", 'type':"Premium"},
                      31, #:{'desc':"Ferry", 'type':"Ferry"},
                      26, #:{'desc':"Caltrain", 'type':"Premium"},
                      32, #:{'desc':"BART", 'type':"BART"},
                      27, #:{'desc':"SMART", 'type':"Premium"},
                      28, #:{'desc':"eBART", 'type':"Premium"},
                      24, #:{'desc':"Sam Trans Express Bus", 'type':"Premium"},
                      25, #:{'desc':"Other Premium Bus", 'type':"Premium"},
                      22, #:{'desc':"AC Transbay Buses", 'type':"Premium"},
                      23, #:{'desc':"Golden Gate Bus", 'type':"Premium"},
                      15, #:{'desc':"LRT Muni", 'type':"LRT"},
                      21, #:{'desc':"VTA LRT", 'type':"LRT"},
                      20, #:{'desc':"Regional BRT", 'type':"BRT"},
                      13, #:{'desc':"BRT Muni", 'type':"local bus"},
                      12, #:{'desc':"Express Muni", 'type':"local bus"},
                      11, #:{'desc':"Local Muni", 'type':"local bus"},
                      18, #:{'desc':"AC Local", 'type':"local bus"},
                      14, #:{'desc':"Muni Cable Car", 'type':"LRT"},
                      16, #:{'desc':"Free and Open Shuttles", 'type':"local bus"},
                      17, #:{'desc':"SamTrans Local", 'type':"local bus"},
                      19, #:{'desc':"Other Local MTC Buses", 'type':"local bus"},
                      ]
                      
    ACCESS_MODES        = [1,3,6,7]
    EGRESS_MODES        = [2,4]
    TRANSFER_MODES      = [5]
    UNUSED_MODES        = [8,9,10]
    NONTRANSIT_MODES    = [1,2,3,4,5,6,7,8,9,10]
    TRANSIT_MODES       = [11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]
    NONTRANSIT_TYPES    = ['non-transit']
    TRANSIT_TYPES       = ['local bus', 'LRT', 'BRT', 'Premium', 'Ferry', 'BART']
    #OFFBOARD_PAYMENT_AGENCIES = ['caltrain','amtrak','ace','bart','airbart','ebart','ferry']
    
    OPERATOR_ID_TO_NAME = {'101_': "caltrain", '102_': "amtrak", '103_': "amtrak", '104_': "ace",
                           '105_': "dumbarton", '106_': "smart", '107_': "bart", '108_': "bart",
                           '100_': "bart", '10_': "west_berkeley_shuttle", '11_': "broadway_shuttle",
                           '12_': "shuttle", '13_': "shuttle", '14_': "caltrain_shuttle",
                           '15_': "shuttle", '16_': "shuttle", '17_': "shuttle", '18_': "shuttle",
                           '19_': "shuttle", '26_': "samtrans", '27_': "samtrans", '28_': "samtrans",
                           '29_': "samtrans", '30_': "samtrans", '31_': "scvta", '32_': "scvta",
                           '33_': "scvta", '34_': "scvta", '35_': "scvta",
                           '37_': "ac_transit", '38_': "ac_transit", '39_': "ac_transit", '40_': "ac_transit",
                           '42_': "lavta", '43_': "lavta", '44_': "lavta", '45_': "lavta",
                           '47_': "union_city_transit",
                           '49_': "airbart",
                           '51_': "cccta", '52_': "cccta", '54_': "tri_delta_transit",
                           '56_': "westcat", '57_': "westcat", '59_': "soltrans", '60_': "soltrans",
                           '62_': "fast", '63_': "fast", '64_': "fast",
                           '65_': "american_canyon", '66_': "vacaville", '68_': "benicia",
                           '70_': "vine", '71_': "vine",
                           '73_': "sonoma_county_transit", '74_': "sonoma_county_transit",
                           '76_': "santa_rosa", '78_': "petaluma",
                           '80_': "golden_gate_transit", '82_': "golden_gate_transit", '83_': "golden_gate_transit",
                           '84_': "golden_gate_transit",
                           '90_': "ferry", '91_': "ferry", '92_': "ferry", '93_': "ferry", '94_': "ferry", '95_': "ferry",
                           'EBA': "ebart", 'MUN': "sf_muni", 'PRES': "presidigo", 'SFS': "sfsu_shuttle",'PM':'parkmerced_shuttle'}

    OPERATOR_NAME_TO_URL = {'caltrain':'http://www.caltrain.com/',
                            'amtrak':'http://www.amtrak.com/',
                            'ace':'https://www.acerail.com/',
                            'dumbarton':'http://dumbartonexpress.com/',
                            'smart':'http://main.sonomamarintrain.org/',
                            'bart':'https://www.bart.gov/',
                            'west_berkeley_shuttle':'http://westberkeleyshuttle.net/',
                            'broadway_shuttle':'http://www.meetdowntownoak.com/shuttle.php',
                            'caltrain_shuttle':'http://www.caltrain.com/',
                            'samtrans':'http://www.samtrans.com/',
                            'scvta':'http://www.vta.org/',
                            'ac_transit':'http://www.actransit.org/',
                            'lavta':'http://www.wheelsbus.com/',
                            'union_city_transit':'http://www.unioncity.org/departments/transit-340',
                            'airbart':'https://www.bart.gov/',
                            'cccta':'http://countyconnection.com/',
                            'tri_delta_transit':'http://www.trideltatransit.com/',
                            'westcat':'http://www.westcat.org/',
                            'soltrans':'http://www.soltransride.com/',
                            'fast':'http://www.fasttransit.org/',
                            'american_canyon':'http://www.ridethevine.com/american-canyon-transit',
                            'vacaville':'http://www.citycoach.com/',
                            'benicia':'http://www.ci.benicia.ca.us/transit',
                            'vine':'http://www.ridethevine.com/vine',
                            'sonoma_county_transit':'http://sctransit.com/',
                            'santa_rosa':'http://ci.santa-rosa.ca.us/departments/transit/citybus/pages/default.aspx',
                            'petaluma':'http://cityofpetaluma.net/pubworks/transit-sub.html',
                            'golden_gate_transit':'http://goldengatetransit.org/',
                            'ebart':'https://www.bart.gov',
                            'sf_muni':'https://www.sfmta.com/',
                            'PRES':'http://presidiobus.com/',
                            'SFS':'sfsu_shuttle',
                            }

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
    
    OFFBOARD_FTMODETYPES = ['commuter_rail','heavy_rail','regional_rail','inter_regional_rail','high_speed_rail','ferry']
    OFFBOARD_FTAGENCIES = ['bart','amtrak','ferry']
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
                              32:1, # 'heavy_rail'}
                              }

    MODENUM_TO_PROOF = {11:1, # {'desc':"Local Muni", 'type':"local bus"},
                        12:1, # {'desc':"Express Muni", 'type':"local bus"},
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
                        32:1, # {'desc':"BART", 'type':"BART"},
                        }
                              
    LINENUM_TO_LINENAME = {'muni':{},
                           'ac_transit':{},
                           'vta':{},
                           }