NetworkWrangler
===============

Wrangles transit and road networks from SF-CHAMP

06.13.2017
Several changes need to be made to the output network before FastTrips is run.
(1) Add dwell time formula in vehicles_ft.txt (see network 1.12_fare)
(2) Change the "transfer" field values for sf_muni_express_bus_allday, sf_muni_light_rail_allday, sf_muni_local_bus_allday to 2 in fare_attributes_ft.txt
(3) Change the "mode" for ace_ACE_ from "inter_regional_rail" to "commuter_rail" in routes_ft.txt
(4) Replace zones_ft.txt with the version with non-zero zone_lon and zone_lat values (see network 1.12_fare)
