NetworkWrangler
===============

**version**: 2.1  
**updated**: 14 June 2018  
**authors**:

NetworkWrangler is the brainchild of Billy Charlton, who was the Deputy Director for Technology Services at SFCTA through 2011.
Contributors include:
* Elizabeth Sall, 2010-2014
* Lisa Zorn, 2010-2014
* Dan Tischler, 2011-Present
* Drew Cooper, 2013-Present
* Bhargava Sana, 2015-Present

NetworkWrangler is licensed under [BSD (3-clause version)](https://github.com/sfcta/NetworkWrangler/LICENSE)

NetworkWrangler has two primary functions: 
1. Create Citilabs Cube networks for SF-CHAMP
2. Create GTFS-PLUS networks for Fast-Trips

## Creating Cube Networks for SF-CHAMP
NetworkWrangler is a python library that enables users to define roadway
and transit projects as collection of data files in a local git repository,
and then create networks by starting with a base network and applying a
set of projects to that base network.

The base network and resulting network are in the [Citilabs Cube](http://www.citilabs.com/software/cube/) format 

## Creating GTFS-PLUS networks for Fast-Trips
NetworkWrangler is also a library that takes Cube networks prepared for SF-CHAMP,
along with various other (optional) inputs, and creates networks in [GTFS-PLUS](https://github.com/osplanning-data-standards/GTFS-PLUS), a [GTFS](https://developers.google.com/transit/gtfs/reference)-based network format developed for use with [Fast-Trips](https://github.com/BayAreaMetro/fast-trips), a dynamic transit 
passenger assignment model.  

Usage
=======
## Building Cube Networks for SF-CHAMP
Build a network by running the `build_network.py` script  in the `/scripts` folder.

	python build_network.py [-c configword] [-m test] network_specification.py

This will build a network using the specifications in `network_specification.py`, which should define the variables listed below (in this script)
  
If test mode is specified (with -m test), then the following happen:
  * networks are built in OUT_DIR\TEST_hwy and OUT_DIR\TEST_trn
  * RTP projects are not applied
  * TAG is not used for TEST_PROJECTS
    
The [-c configword] is if you want an optional word for your network_specification.py
  (e.g. to have multiple scenarios in one file).  Access it via CONFIG_WORD.

## Building GTFS-PLUS Networks for Fast-Trips
Build a GTFS-PLUS from the SFCTA's SF-CHAMP model inputs by running the `convert_cube_to_fasttrips.py` script in the `/scripts` folder.

	python NetworkWrangler\scripts\convert_cube_to_fasttrips.py NetworkWrangler\config\config_testnet.py

NOTE: This is still under development. If you have comments
or suggestions please file them in the [issue tracker][issues]. If you have
explicit changes please fork the [git repo][repo] and submit a pull request.

### Changelog
2.1 Adds ability to build GTFS-PLUS networks.
2.0 Made NetworkWrangler compatible with SF-CHAMP 5.0.  
