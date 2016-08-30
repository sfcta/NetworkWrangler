import sys, os
import numpy as np
import pandas as pd
sys.path.insert(r'Y:\champ\util\pythonlib-migration\master_version\gtfs_utils')
import gtfs_utils

if __name__=='__main__':
    args = sys.argv[1:]
    gtfs_path = args[0]

    gtfs = GTFSFeed(gtfs_path)
    gtfs.load()