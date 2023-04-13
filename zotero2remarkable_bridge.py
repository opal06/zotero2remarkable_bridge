#!/usr/bin/python3

import sys
import getopt
import rmapi_shim as rmapi
from tqdm import tqdm
from config_functions import write_config
from sync_functions import SyncFile


def main(argv):
    config_path = Path.cwd() / "config.yml"
    if config_path.exists():
        sf = SyncFile(config_path)
    else:
        write_config(config_path)
        sf = SyncFile(config_path)
    
    try:
        opts, args = getopt.getopt(argv, "m:")
    except getopt.GetoptError:
        print("No argument recognized")
        sys.exit()
    
    for opt, arg in opts:
        if opt == "-m":
            if arg == "push":
                # Only sync files from Zotero to reMarkable
                print("Pushing...")
                sf.push()

            elif arg == "pull":
                # Only get files from ReMarkable and upload to Zotero
                print("Pulling...")
                sf.pull()
                
            elif arg == "both":
                # Do both
                print("Do both...")
                # Upload...
                sf.push()
                
                # ...and download, add highlighting and sync to Zotero.

                sf.pull()

            else:
                print("Invalid argument")
                sys.exit()
        

main(sys.argv[1:])
