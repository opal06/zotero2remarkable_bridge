import os
import zipfile
import json
import fitz
import yaml
import tempfile
import hashlib
from pathlib import Path
from shutil import rmtree
from pyzotero import zotero
from webdav3.client import Client as wdClient
from rmapy.document import ZipDocument
from rmrl import render
from time import sleep
from datetime import datetime


def check_auth(rm):
    if not rm.is_auth():
        token = input("Device not registered yet. Please enter token from https://my.remarkable.com/device/desktop/connect : ")
        rm.register_device(token)
        rm.renew_token()
        print("Registered new device!")
    else:
        rm.renew_token()
        print("Device already registered!")


def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            config_dict = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    zot = zotero.Zotero(config_dict["LIBRARY_ID"], config_dict["LIBRARY_TYPE"], config_dict["API_KEY"]) 
    if config_dict["USE_WEBDAV"] == "True":
        webdav_data = {
            "webdav_hostname": config_dict["WEBDAV_HOSTNAME"],
            "webdav_login": config_dict["WEBDAV_USER"],
            "webdav_password": config_dict["WEBDAV_PWD"],
            "webdav_timeout": 300
            }   
        webdav = wdClient(webdav_data)
    else:
        webdav = False
    return (zot, webdav)
    

def write_config(file_name):
    config_data = {}
    input("Couldn't find config file. Let's create one! Press Enter to continue...")
    config_data["LIBRARY_ID"] = input("Enter Zotero library ID: ")
    config_data["LIBRARY_TYPE"] = input("Enter Zotero library type (user/group): ")
    config_data["API_KEY"] = input("Enter Zotero API key: ")
    config_data["USE_WEBDAV"] = input("Does Zotero use WebDAV storage for file sync (True/False)? ")
    if config_data["USE_WEBDAV"] == "True":
        config_data["WEBDAV_HOSTNAME"] = input("Enter path to WebDAV folder (same as in Zotero config): ")
        config_data["WEBDAV_USER"] = input("Enter WebDAV username: ")
        config_data["WEBDAV_PWD"] = input("Enter WebDAV password (consider creating an app token as password is safed in clear text): ")
    
    with open(file_name, "w") as file:
        yaml.dump(config_data, file)
    print("Config written to " + file_name + "\n If something went wrong, please edit config manually.")


def get_scale(page_rect):
    """ This part was inspired by rmrl's implementation"""
    display = {
        "screenwidth": 1404,
        "screenheight": 1872,
        "realwidth": 1408,
        "dpi": 226
    }    
    ptperpx = display["dpi"] / 72
    pdf_height = display["screenheight"] * ptperpx
    #pdf_width = display["screenwidth"] * ptperpx
    scale = round(page_rect.y1) / pdf_height
    return scale


def sync_to_rm(item, zot, rm):
    temp_path = Path(tempfile.gettempdir())
    item_id = item["key"]
    attachments = zot.children(item_id)
    for entry in attachments:
        if "contentType" in entry["data"] and entry["data"]["contentType"] == "application/pdf":
            attachment_id = attachments[attachments.index(entry)]["key"]
            attachment_name = zot.item(attachment_id)["data"]["filename"]
            print("Processing " + attachment_name + "...")
                
            # Get actual file and repack it in reMarkable's file format
            file_name = zot.dump(attachment_id, path=temp_path)
            if file_name:
                raw_document = ZipDocument(doc=file_name)
            else:
                print("Error downloading file! Abborting...")
                break
                
            # Get the folder ID for upload dir
            parent_id = str([p for p in rm.get_meta_items() if p.VissibleName == "Zotero"][0]).strip("<>").split(" ")[1]
            folder_id = [f for f in rm.get_meta_items() if f.VissibleName == "Ungelesen" and f.Parent == parent_id][0]
    
            # Upload to reMarkable and set tag in Zotero
            rm.upload(raw_document, folder_id)
            zot.add_tags(item, "synced")
            os.remove(file_name)
            print("Uploaded " + attachment_name + " to reMarkable.")
        else:
            print("Found attachment, but it's not a PDF, skipping...")
        
       
def sync_to_rm_webdav(item, zot, rm, webdav):
    temp_path = Path(tempfile.gettempdir())
    item_id = item["key"]
    attachments = zot.children(item_id)
    for entry in attachments:
        if "contentType" in entry["data"] and entry["data"]["contentType"] == "application/pdf":
            attachment_id = attachments[attachments.index(entry)]["key"]
            attachment_name = zot.item(attachment_id)["data"]["filename"]
            print("Processing " + attachment_name + "...")
    
            # Get actual file from webdav, extract it and repack it in reMarkable's file format
            file_name = attachment_id + ".zip"
            file_path = Path(temp_path / file_name)
            unzip_path = Path(temp_path / "unzipped")     
            webdav.download_sync(remote_path=file_name, local_path=file_path)
            with zipfile.ZipFile(file_path) as zf:
                zf.extractall(unzip_path)
            if (unzip_path / attachment_name ).is_file():
                raw_document = ZipDocument(doc=str(unzip_path / attachment_name))
            else:
                """ #TODO: Sometimes Zotero does not seem to rename attachments properly,
                    leading to reported file names diverging from the actual one. 
                    To prevent this from stopping the whole program due to missing
                    file errors, skip that file. Probably it could be worked around better though.""" 
                print("PDF not found in downloaded file. Filename might be different. Try renaming file in Zotero, sync and try again.")
                break
    
            # Get the folder ID for upload dir
            parent_id = str([f for f in rm.get_meta_items() if f.VissibleName == "Zotero"][0]).strip("<>").split(" ")[1]
            folder_id = [e for e in rm.get_meta_items() if e.VissibleName == "Ungelesen" and e.Parent == parent_id][0]
    
            # Upload to reMarkable and set tag in Zotero
            rm.upload(raw_document, folder_id)
            zot.add_tags(item, "synced")
            file_path.unlink()
            rmtree(unzip_path)
            print("Uploaded " + attachment_name + " to reMarkable.")
        else:
            print("Found attachment, but it's not a PDF, skipping...")


def get_from_rm(entity, rm, folder):
    temp_path = Path(tempfile.gettempdir())
    parent_id = str([p for p in rm.get_meta_items() if p.VissibleName == folder][0]).strip("<>").split(" ")[1]
    
    if entity.Parent == parent_id:
        print("Processing " + entity.VissibleName + "...")
        content_id = str(rm.download(entity)).strip("<>").split(" ")[1]
        zip_name = entity.VissibleName + ".zip"
        file_path = temp_path / zip_name
        unzip_path = temp_path / "unzipped"
        rm.download(rm.get_doc(content_id)).dump(file_path)
        print("File downloaded")
            
        
        with zipfile.ZipFile(file_path, "r") as zf:
            zf.extractall(unzip_path)
        (unzip_path / (content_id + ".pagedata")).unlink()
        with zipfile.ZipFile(file_path, "w") as zf:
            for entry in sorted(unzip_path.glob("**/*")):
                zf.write(unzip_path / entry, arcname=entry)
                
        output = render(str(file_path))
        print("PDF rendered")
        pdf_name = entity.VissibleName + ".pdf"
        with open(temp_path / pdf_name, "wb") as outputFile:
            outputFile.write(output.read())
        print("PDF written")
        file_path.unlink()
        
        return (content_id, pdf_name)
    else:
        return False
    

def add_highlights_simple(entity, content_id, pdf_name):
    temp_path = Path(tempfile.gettempdir())
    work_dir = temp_path / "unzipped"
    highlights_dir = work_dir / (content_id + ".highlights")
    
    # Highlighter colors are saved as integers by ReMarkable: 0 = yellow, 4 = green, 5 = pink
    colors = {0 : [1.0, 1.0, 0.0], 4 : [0.0, 1.0, 0.3], 5 : [1.0, 0.0, 0.7]}
    
    if highlights_dir.is_dir():
         
        pdf = fitz.open(temp_path / pdf_name)            
        
        for highlights_file in highlights_dir.iterdir():
            highlights_id = highlights_file.stem
                    
            with open(highlights_file, "r", encoding="utf-8") as hl:
                hl_json = json.load(hl)
            hl_list = hl_json["highlights"][0]
                            
            with open(work_dir / (content_id + ".content"), "r") as content_file:
                content_json = json.load(content_file)
            page_nr = content_json["pages"].index(highlights_id)
                                                 
            page = pdf.load_page(page_nr)
                
            for hl in hl_list:
                if "\u0002" in hl["text"]:
                    search_text = hl["text"].replace("\u0002", "")
                else:
                    search_text = hl["text"]
                quads = page.search_for(search_text, quads=True)                  
                    
                if quads != []:                    
                    highlight = page.add_highlight_annot(quads)
                else:
                    print("Failed to create highlight on " + str(page_nr + 1) + "...")
                
                if "color" in hl:
                    highlight_color = colors[hl["color"]]
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
            
        print("Added annotations to file")
        
        if pdf.can_save_incrementally():
            pdf.save(temp_path / pdf_name, incremental=True, encryption=0)
            pdf.close()
        else:
            pdf_hl = (temp_path / pdf_name).with_suffix(".pdf.hl")
            pdf.save(pdf_hl)
            pdf.close()
            (temp_path / pdf_name).unlink()
            pdf_name = pdf_hl.with_suffix(".pdf")
        print("Saved PDF as " + str(pdf_name))
        #rmtree(work_dir)
                
    else:
        print("No highlights found, skipping...")                     
            

def zotero_upload(pdf_name, zot):
    for item in zot.items(tag="synced"):
        item_id = item["key"]
        for attachment in zot.children(item_id):
            if "filename" in attachment["data"] and attachment["data"]["filename"] == pdf_name:
                #zot.delete_item(attachment)
                # Keeping the original seems to be the more sensible thing to do
                new_pdf_name = pdf_name.with_stem("(Annot) " + pdf_name.stem)
                pdf_name.rename(new_pdf_name)
                upload = zot.attachment_simple([new_pdf_name], item_id)                
                
                if upload["success"] != []:
                    print(pdf_name + " uploaded to Zotero.")
                else:
                    print("Upload of " + pdf_name + " failed...")
                return
                                  

def zotero_upload_webdav(pdf_name, zot, webdav):
    print(pdf_name)
    temp_path = Path(tempfile.gettempdir())
    for item in zot.items(tag="synced"):
        item_id = item["key"]
        for attachment in zot.children(item_id):
            if "filename" in attachment["data"] and attachment["data"]["filename"] == pdf_name:
                # Fix the need to create an attchment in the first place, as it uploads a file to 
                # Zotero's internal storage.
                pdf_name = temp_path / pdf_name
                new_pdf_name = pdf_name.with_stem("(Annot) " + pdf_name.stem)
                pdf_name.rename(new_pdf_name)
                upload = zot.attachment_simple([str(new_pdf_name)], item_id)
                
                if upload["success"] != []:
                    key = upload["success"][0]["key"]                    
                else:
                    print("Failed to create attachment, aborting...")
                    break
                
                attachment_zip = temp_path / (key + ".zip")
                with zipfile.ZipFile(attachment_zip, "w") as zf:
                    zf.write(new_pdf_name, arcname=new_pdf_name.name)
                remote_attachment_zip = attachment_zip.name
                
                for i in range(3):
                    try:
                        webdav.upload_sync(remote_path=remote_attachment_zip, local_path=attachment_zip)
                    except:
                        print("Error uploadinng file, retrying in 5 seconds")
                        sleep(5)
                    else:
                        print("Upload successful, proceding...")
                        break
                
                """For the file to be properly recognized in Zotero, a propfile needs to be 
                uploaded to the same folder with the same ID. The content needs 
                to match exactly Zotero's format."""
                mtime = datetime.now().strftime('%s')
                with open(new_pdf_name, "rb") as f:
                    bytes = f.read()
                    md5 = hashlib.md5(bytes).hexdigest()
                propfile_content = '<properties version="1"><mtime>' + mtime + '</mtime><hash>' + md5 + '</hash></properties>'
                print(propfile_content)
                propfile = temp_path / (key + ".prop")
                with open(propfile, "w") as pf:
                    pf.write(propfile_content)
                remote_propfile = key + ".prop"
                
                for i in range(3):
                    try:
                        webdav.upload_sync(remote_path=remote_propfile, local_path=propfile)
                    except:
                        print("Error uploadinng file, retrying in 5 seconds")
                        sleep(5)
                    else:
                        print("Upload successful, proceding...")
                        break
                            
                zot.add_tags(item, "gelesen")
                print(new_pdf_name.name + " uploaded to Zotero.")
                (temp_path / new_pdf_name).unlink()
                return new_pdf_name
            
def get_sync_status(zot):
    red_list = []
    for item in zot.items(tag="gelesen"):
        for attachment in zot.children(item["key"]):
            if "contentType" in attachment["data"] and attachment["data"]["contentType"] == "application/pdf":
                red_list.append(attachment["data"]["filename"])
    
    return red_list
                  
