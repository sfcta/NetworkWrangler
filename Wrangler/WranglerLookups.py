class WranglerLookups:
    
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

    ACCESS_MODES        = [1,3,6,7]
    EGRESS_MODES        = [2,4]
    TRANSFER_MODES      = [5]
    UNUSED_MODES        = [8,9,10]
    NONTRANSIT_MODES    = [1,2,3,4,5,6,7,8,9,10]
    TRANSIT_MODES       = [11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]
    NONTRANSIT_TYPES    = ['non-transit']
    TRANSIT_TYPES       = ['local bus', 'LRT', 'BRT', 'Premium', 'Ferry', 'BART']
    
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
                           '56_': "westcat", '57_': "westcat", '59_': "vallejo_transit", '60_': "vallejo_transit",
                           '62_': "fast", '63_': "fast", '64_': "fast",
                           '65_': "american_canyon", '66_': "vacaville", '68_': "benicia",
                           '70_': "vine", '71_': "vine",
                           '73_': "sonoma_county_transit", '74_': "sonoma_county_transit",
                           '76_': "santa_rosa", '78_': "petaluma",
                           '80_': "golden_gate_transit", '82_': "golden_gate_transit", '83_': "golden_gate_transit",
                           '84_': "golden_gate_transit",
                           '90_': "ferry", '91_': "ferry", '92_': "ferry", '93_': "ferry", '94_': "ferry", '95_': "ferry",
                           'EBA': "ebart", 'MUN': "sf_muni", 'PRES': "presidigo", 'SFS': "sfsu_shuttle",}