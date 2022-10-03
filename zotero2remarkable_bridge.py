#!/usr/bin/python3

import sys
import getopt
import rmapi_shim as rmapi
from tqdm import tqdm
from sync_functions import *
from pdf_functions import add_highlights_simple


def push(zot, webdav, folders):
    sync_items = zot.items(tag="to_sync")
    print(f"Found {len(sync_items)} elements to sync...")
    for item in tqdm(sync_items):
        if webdav:
            sync_to_rm_webdav(item, zot, webdav, folders)
        else:
            sync_to_rm(item, zot, folders)
    zot.delete_tags("to_sync")


def pull(zot, webdav, read_folder):
    files_list = rmapi.get_files(read_folder)
    if files_list:
        for entity in tqdm(files_list):
            content_id = rmapi.get_metadata(f"{read_folder}{entity}")["ID"]
            pdf_name = download_from_rm(entity, read_folder, content_id)
            add_highlights_simple(entity, content_id, pdf_name)
            if webdav:
                zotero_upload_webdav(pdf_name, zot, webdav)
            else:
                zotero_upload(pdf_name, zot)
    else:
        print("No files to pull found")


def main(argv):
    config_path = Path.cwd() / "config.yml"
    if config_path.exists():
        zot, webdav, folders = load_config("config.yml")
    else:
        write_config("config.yml")
        zot, webdav, folders = load_config("config.yml")
    read_folder = f"/Zotero/{folders['read']}/"
    
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
                push(zot, webdav, folders)

            elif arg == "pull":
                # Only get files from ReMarkable and upload to Zotero
                print("Pulling...")
                pull(zot, webdav, read_folder)
                
            elif arg == "both":
                # Do both
                print("Do both...")
                # Upload...
                push(zot, webdav, folders)
                
                # ...and download, add highlighting and sync to Zotero.

                pull(zot, webdav, read_folder)

            else:
                print("Invalid argument")
                sys.exit()
        

main(sys.argv[1:])
