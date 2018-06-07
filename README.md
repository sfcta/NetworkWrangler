
## Network Wrangler -- fastrips

Tools to build GTFS-PLUS from the SFCTA's SF-CHAMP model inputs

**version**: 1.14  
**updated**: 07 June 2018  
**created**: 29 December 2015  
**authors**:

 * Drew Cooper (San Francisco County Transportation Authority)  
 
[issues]: https://github.com/sfcta/NetworkWrangler/issues
[repo]: https://github.com/sfcta/NetworkWrangler/tree/fasttrips
[GTFS]: https://developers.google.com/transit/gtfs/reference
[GTFS-PLUS]: https://github.com/osplanning-data-standards/GTFS-PLUS

PREREQUISITES: NetworkWrangler relies on Python 2.7.  Most, if not all, required packages should be included in the 
			   Anaconda distribution of Python.  The following non-core packages, which are not included in the 
			   NetworkWrangler distribution, are used:
					dbfpy
					pandas
					shapely
					pyproj
					xlrd
					shapefile
					odict
					
USAGE: python NetworkWrangler\scripts\convert_cube_to_fasttrips.py NetworkWrangler\config\config_testnet.py

NOTE: This is still under development. If you have comments
or suggestions please file them in the [issue tracker][issues]. If you have
explicit changes please fork the [git repo][repo] and submit a pull request.

### Changelog





