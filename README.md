NetworkWrangler
===============

NetworkWrangler is a python library that enables users to define roadway
and transit projects as collection of data files in a local git repository,
and then create networks by starting with a base network and applying a
set of projects to that base network.

The base network and resulting network are in the Citilabs Cube format (http://www.citilabs.com/software/cube/)

Contributors
=======
NetworkWrangler is the brainchild of Billy Charlton, who was the Deputy Director for Technology Services at SFCTA through 2011.
Contributors include:
* Elizabeth Sall, 2010-2014
* Lisa Zorn, 2010-2014
* Dan Tischler, 2011-Present
* Drew Cooper, 2013-Present
* Bhargava Sana, 2015-Present

Usage
=======

Build a network by running the `build_network.py` script  in the `/scripts` folder.

   python build_network.py [-c configword] [-m test] network_specification.py


This will build a network using the specifications in `network_specification.py`, which should define the variables listed below (in this script)
  
If test mode is specified (with -m test), then the following happen:
  * networks are built in OUT_DIR\TEST_hwy and OUT_DIR\TEST_trn
  * RTP projects are not applied
  * TAG is not used for TEST_PROJECTS
    
The [-c configword] is if you want an optional word for your network_specification.py
  (e.g. to have multiple scenarios in one file).  Access it via CONFIG_WORD.