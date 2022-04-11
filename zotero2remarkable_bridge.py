#!/usr/bin/python3

import sys
import getopt
from tqdm import tqdm
from rmapy.api import Client
from sync_functions import *
from pdf_functions import add_highlights_simple



def main(argv):
    config_path = Path.cwd() / "config.yml"
    rm = Client()
    check_auth(rm)
    if config_path.exists():
        zot, webdav, folders = load_config("config.yml")
    else:
        write_config("config.yml")
        zot, webdav, folders = load_config("config.yml")
    
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
                print("Found " + str(len(zot.items(tag="to_sync"))) + " elements to sync...") 
                for item in tqdm(zot.items(tag="to_sync")):
                    if webdav: 
                        sync_to_rm_webdav(item, zot, rm, webdav, folders)
                    else:
                        sync_to_rm(item, zot, rm, folders)
                zot.delete_tags("to_sync")

            elif arg == "pull":
                # Only get files from ReMarkable and upload to Zotero
                print("Pulling...")
                collection = rm.get_meta_items()
                children = get_children(folders["read"], collection)
                for entity in tqdm(children):
                    result = download_from_rm(entity, rm)
                    content_id, pdf_name = result
                    add_highlights_simple(entity, content_id, pdf_name)
                    if webdav:
                        zotero_upload_webdav(pdf_name, zot, webdav)
                    else:
                        zotero_upload(pdf_name, zot)
                
            elif arg == "both":
                # Do both
                print("Do both...")
                # Upload...
                for item in tqdm(zot.items(tag="to_sync")):
                    if webdav:
                        sync_to_rm_webdav(item, zot, rm, webdav, folders)
                    else:
                        sync_to_rm(item, zot, rm, folders)
                zot.delete_tags("to_sync")        
                
                # ...and download, add highlighting and sync to Zotero.

                collection = rm.get_meta_items()
                children = get_children(folders["read"], collection)
                for entity in tqdm(children):
                    result = download_from_rm(entity, rm)
                    content_id, pdf_name = result
                    add_highlights_simple(entity, content_id, pdf_name)
                    if webdav:
                        zotero_upload_webdav(pdf_name, zot, webdav)
                    else:
                        zotero_upload(pdf_name, zot)
                            
            else:
                print("Invalid argument")
                sys.exit()
        

main(sys.argv[1:])
