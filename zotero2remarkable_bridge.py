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
                read_list = get_sync_status(zot)
                for entity in tqdm(rm.get_meta_items()):
                    if entity.VissibleName + ".pdf" not in read_list:
                        result = get_from_rm(entity, rm, folders["read"])
                        if result:
                            content_id, pdf_name = result
                            add_highlights_simple(entity, content_id, pdf_name)
                            if webdav:
                                zotero_upload_webdav(pdf_name, zot, webdav)
                            else:
                                zotero_upload(pdf_name, zot)
                    else:
                        continue
                
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

                read_list = get_sync_status(zot)
                for entity in tqdm(rm.get_meta_items()):
                    if entity.VissibleName + ".pdf" not in read_list:
                        result = get_from_rm(entity, rm, folders["read"])
                        if result:
                            content_id, pdf_name = result
                            add_highlights_simple(entity, content_id, pdf_name)
                            if webdav:
                                zotero_upload_webdav(pdf_name, zot, webdav)
                            else:
                                zotero_upload(pdf_name, zot)
                    else:
                        continue
                    
            elif arg == "hl-test":
                for entity in tqdm(rm.get_meta_items()):
                    result = get_from_rm(entity, rm, "Test")
                    if result:
                        content_id, pdf_name = result
                        add_highlights_simple(entity, content_id, pdf_name)
                        zotero_upload_webdav(pdf_name, zot, webdav)
                    else:
                        continue
                
                            
                
            else:
                print("Invalid argument")
                sys.exit()
        


main(sys.argv[1:])
