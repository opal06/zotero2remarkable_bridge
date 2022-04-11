import os
import zipfile
import yaml
import tempfile
import hashlib
from pathlib import Path
from shutil import rmtree
from pyzotero import zotero
from webdav3.client import Client as wdClient
from rmapy.document import ZipDocument
from rmapy.folder import Folder
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
    folders = {"unread": config_dict["UNREAD_FOLDER"], "read": config_dict["READ_FOLDER"]}
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
    return (zot, webdav, folders)
    

def write_config(file_name):
    config_data = {}
    input("Couldn't find config file. Let's create one! Press Enter to continue...")
    config_data["UNREAD_FOLDER"] = input("Which ReMarkable folder should files be synced to?")
    config_data["READ_FOLDER"] = input("Which ReMarkable folder should files be synced from?")
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


def sync_to_rm(item, zot, rm, folders):
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
            folder_id = [f for f in rm.get_meta_items() if f.VissibleName == folders["unread"] and f.Parent == parent_id][0]
    
            # Upload to reMarkable and set tag in Zotero
            rm.upload(raw_document, folder_id)
            zot.add_tags(item, "synced")
            os.remove(file_name)
            print("Uploaded " + attachment_name + " to reMarkable.")
        else:
            print("Found attachment, but it's not a PDF, skipping...")
        
       
def sync_to_rm_webdav(item, zot, rm, webdav, folders):
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
            folder_id = [e for e in rm.get_meta_items() if e.VissibleName == folders["unread"] and e.Parent == parent_id][0]
    
            # Upload to reMarkable and set tag in Zotero
            rm.upload(raw_document, folder_id)
            zot.add_tags(item, "synced")
            file_path.unlink()
            rmtree(unzip_path)
            print("Uploaded " + attachment_name + " to reMarkable.")
        else:
            print("Found attachment, but it's not a PDF, skipping...")


def get_children(folder, collection):
    folders = [f for f in collection if isinstance(f, Folder)]
    read_folder = [f for f in folders if f.VissibleName == folder][0]
    children = collection.children(read_folder)
    return children


def download_from_rm(entity, rm):
    temp_path = Path(tempfile.gettempdir())
    print("Processing " + entity.VissibleName + "...")
    content_id = entity.ID
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


# def get_from_rm(entity, rm, folder):
#     temp_path = Path(tempfile.gettempdir())
#     parent_id = [p.ID for p in rm.get_meta_items() if p.VissibleName == folder][0]
    
#     if entity.Parent == parent_id:
#         print("Processing " + entity.VissibleName + "...")
#         content_id = entity.ID
#         zip_name = entity.VissibleName + ".zip"
#         file_path = temp_path / zip_name
#         unzip_path = temp_path / "unzipped"
#         rm.download(rm.get_doc(content_id)).dump(file_path)
#         print("File downloaded")
            
#         with zipfile.ZipFile(file_path, "r") as zf:
#             zf.extractall(unzip_path)
#         (unzip_path / (content_id + ".pagedata")).unlink()
#         with zipfile.ZipFile(file_path, "w") as zf:
#             for entry in sorted(unzip_path.glob("**/*")):
#                 zf.write(unzip_path / entry, arcname=entry)
                
#         output = render(str(file_path))
#         print("PDF rendered")
#         pdf_name = entity.VissibleName + ".pdf"
#         with open(temp_path / pdf_name, "wb") as outputFile:
#             outputFile.write(output.read())
#         print("PDF written")
#         file_path.unlink()
        
#         return (content_id, pdf_name)
#     else:
#         return False
    

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


def get_md5(pdf):
    if pdf.is_file():
        with open(pdf, "rb") as f:
            bytes = f.read()
            md5 = hashlib.md5(bytes).hexdigest()
    else:
        md5 = None
    return md5


def get_mtime():
    mtime = datetime.now().strftime('%s')
    return mtime


def fill_template(item_template, pdf_name):
    item_template["title"] = pdf_name.stem
    item_template["filename"] = pdf_name.name
    item_template["md5"] = get_md5(pdf_name)
    item_template["mtime"] = get_mtime()
    return item_template


def webdav_uploader(webdav, remote_path, local_path):
    for i in range(3):
        try:
            webdav.upload_sync(remote_path=remote_path, local_path=local_path)
        except:
            sleep(5)
        else:
            return True
    else:
        return False


def zotero_upload_webdav(pdf_name, zot, webdav):
    temp_path = Path(tempfile.gettempdir())
    item_template = zot.item_template("attachment", "imported_file")
    for item in zot.items(tag="synced"):
        item_id = item["key"]
        for attachment in zot.children(item_id):
            if "filename" in attachment["data"] and attachment["data"]["filename"] == pdf_name:
                pdf_name = temp_path / pdf_name
                new_pdf_name = pdf_name.with_stem("(Annot) " + pdf_name.stem)
                pdf_name.rename(new_pdf_name)
                pdf_name = new_pdf_name
                filled_item_template = fill_template(item_template, pdf_name)
                create_attachment = zot.create_items([filled_item_template], item_id)
                
                if create_attachment["success"] != []:
                    key = create_attachment["success"]["0"]
                else:
                    print("Failed to create attachment, aborting...")
                    continue
                
                attachment_zip = temp_path / (key + ".zip")
                with zipfile.ZipFile(attachment_zip, "w") as zf:
                    zf.write(pdf_name, arcname=pdf_name.name)
                remote_attachment_zip = attachment_zip.name
                
                attachment_upload = webdav_uploader(webdav, remote_attachment_zip, attachment_zip)
                if attachment_upload:
                    print("Attachment upload successfull, proceeding...")
                else:
                    print("Failed uploading attachment, skipping...")
                    continue

                """For the file to be properly recognized in Zotero, a propfile needs to be
                uploaded to the same folder with the same ID. The content needs 
                to match exactly Zotero's format."""
                propfile_content = '<properties version="1"><mtime>' + item_template["mtime"] + '</mtime><hash>' + item_template["md5"] + '</hash></properties>'
                propfile = temp_path / (key + ".prop")
                with open(propfile, "w") as pf:
                    pf.write(propfile_content)
                remote_propfile = key + ".prop"
                
                propfile_upload = webdav_uploader(webdav, remote_propfile, propfile)
                if propfile_upload:
                    print("Propfile upload successful, proceeding...")
                else:
                    print("Propfile upload failed, skipping...")
                    continue
                            
                zot.add_tags(item, "read")
                print(pdf_name.name + " uploaded to Zotero.")
                (temp_path / pdf_name).unlink()
                (temp_path / attachment_zip).unlink()
                (temp_path / propfile).unlink()
                return pdf_name
            

def get_sync_status(zot):
    read_list = []
    for item in zot.items(tag="read"):
        for attachment in zot.children(item["key"]):
            if "contentType" in attachment["data"] and attachment["data"]["contentType"] == "application/pdf":
                read_list.append(attachment["data"]["filename"])
    
    return read_list
                  
