import os
import tempfile
import zipfile
import remarks
from pathlib import Path
from shutil import rmtree
from tqdm import tqdm
from config_functions import load_config
from rmapi_shim import Rmapi
from utils import *


class SyncFile:
    def __init__(self, conf_file):
        self.temp_path = Path(tempfile.gettempdir() / "zot2rm")
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.zot, self.webdav, self.folders = load_config(conf_file)
        self.rmapi = Rmapi(self.temp_path)
        self.read_folder_path = f"/Zotero/{self.folders['read']}/"
        self.unread_folder_path = f"/Zotero/{self.folders['unread']}/"

    def sync_to_rm(self, item):
        item_id = item["key"]
        attachments = self.zot.children(item_id)
        for entry in attachments:
            if "contentType" in entry["data"] and entry["data"]["contentType"] == "application/pdf":
                attachment_id = attachments[attachments.index(entry)]["key"]
                attachment_name = self.zot.item(attachment_id)["data"]["filename"]
                print(f"Processing {attachment_name}...")

                # Get actual file and repack it in reMarkable's file format
                file_name = self.zot.dump(attachment_id, path=self.temp_path)
                if file_name:
                    upload = self.rmapi.upload_file(file_name, self.unread_folder_path)
                else:
                    upload = False
                if upload:
                    self.zot.add_tags(item, "synced")
                    os.remove(file_name)
                    print(f"Uploaded {attachment_name} to reMarkable.")
                    return True
                else:
                    print(f"Failed to upload {attachment_name} to reMarkable.")
                    return False
            else:
                print("Found attachment, but it's not a PDF, skipping...")
                return False

    def sync_to_rm_webdav(self, item):
        item_id = item["key"]
        attachments = self.zot.children(item_id)
        for entry in attachments:
            if "contentType" in entry["data"] and entry["data"]["contentType"] == "application/pdf":
                attachment_id = attachments[attachments.index(entry)]["key"]
                attachment_name = self.zot.item(attachment_id)["data"]["filename"]
                print(f"Processing {attachment_name}...")

                # Get actual file from webdav, extract it and repack it in reMarkable's file format
                file_name = f"{attachment_id}.zip"
                file_path = Path(self.temp_path / file_name)
                unzip_path = Path(self.temp_path / f"{file_name}-unzipped")
                self.webdav.download_sync(remote_path=file_name, local_path=file_path)
                with zipfile.ZipFile(file_path) as zf:
                    zf.extractall(unzip_path)
                if (unzip_path / attachment_name).is_file():
                    uploader = self.rmapi.upload_file(str(unzip_path / attachment_name), self.unread_folder_path)
                else:
                    """ #TODO: Sometimes Zotero does not seem to rename attachments properly,
                        leading to reported file names diverging from the actual one.
                        To prevent this from stopping the whole program due to missing
                        file errors, skip that file. Probably it could be worked around better though."""
                    print("PDF not found in downloaded file. Filename might be different. Try renaming file in Zotero, sync and try again.")
                    break
                if uploader:
                    self.zot.add_tags(item, "synced")
                    file_path.unlink()
                    rmtree(unzip_path)
                    print(f"Uploaded {attachment_name} to reMarkable.")
                    return True
                else:
                    print(f"Failed to upload {attachment_name} to reMarkable.")
                    return False
            else:
                print("Found attachment, but it's not a PDF, skipping...")
                return False

    def download_from_rm(self, entity, folder):
        print(f"Processing {entity}...")
        zip_name = f"{entity}.zip"
        file_path = self.temp_path / zip_name
        unzip_path = self.temp_path / f"{entity}-unzipped"
        download = self.rmapi.download_file(f"{folder}{entity}")
        if download:
            print("File downloaded")
        else:
            print("Failed to download file")

        with zipfile.ZipFile(file_path, "r") as zf:
            zf.extractall(unzip_path)

        renderer = remarks
        args = {"combined_pdf": True, "combined_md": False, "ann_type": ["scribbles", "highlights"]}
        renderer.run_remarks(unzip_path, self.temp_path, **args)
        print("PDF rendered")
        pdf = (self.temp_path / f"{entity} _remarks.pdf")
        pdf = pdf.rename(pdf.with_stem(f"{entity}"))
        pdf_name = pdf.name

        print("PDF written")
        file_path.unlink()
        rmtree(unzip_path)
        return pdf_name

    def zotero_upload(self, pdf_name):
        for item in self.zot.items(tag="synced"):
            item_id = item["key"]
            for attachment in self.zot.children(item_id):
                if "filename" in attachment["data"] and attachment["data"]["filename"] == pdf_name:
                    #zot.delete_item(attachment)
                    # Keeping the original seems to be the more sensible thing to do
                    new_pdf_name = pdf_name.with_stem(f"(Annot) {pdf_name.stem}")
                    pdf_name.rename(new_pdf_name)
                    upload = self.zot.attachment_simple([new_pdf_name], item_id)

                    if upload["success"]:
                        print(f"{pdf_name} uploaded to Zotero.")
                        return True
                    else:
                        print(f"Upload of {pdf_name} failed...")
                        return False

    def zotero_upload_webdav(self, pdf_name):
        item_template = self.zot.item_template("attachment", "imported_file")
        for item in self.zot.items(tag=["synced", "-read"]):
            item_id = item["key"]
            for attachment in self.zot.children(item_id):
                if "filename" in attachment["data"] and attachment["data"]["filename"] == pdf_name:
                    pdf_name = self.temp_path / pdf_name
                    new_pdf_name = pdf_name.with_stem(f"(Annot) {pdf_name.stem}")
                    pdf_name.rename(new_pdf_name)
                    pdf_name = new_pdf_name
                    filled_item_template = fill_template(item_template, pdf_name)
                    create_attachment = self.zot.create_items([filled_item_template], item_id)

                    if create_attachment["success"]:
                        key = create_attachment["success"]["0"]
                    else:
                        print("Failed to create attachment, aborting...")
                        continue

                    attachment_zip = self.temp_path / f"{key}.zip"
                    with zipfile.ZipFile(attachment_zip, "w") as zf:
                        zf.write(pdf_name, arcname=pdf_name.name)
                    remote_attachment_zip = attachment_zip.name

                    attachment_upload = webdav_uploader(self.webdav, remote_attachment_zip, attachment_zip)
                    if attachment_upload:
                        print("Attachment upload successfull, proceeding...")
                    else:
                        print("Failed uploading attachment, skipping...")
                        continue

                    """For the file to be properly recognized in Zotero, a propfile needs to be
                    uploaded to the same folder with the same ID. The content needs
                    to match exactly Zotero's format."""
                    propfile_content = f'<properties version="1"><mtime>{item_template["mtime"]}</mtime><hash>{item_template["md5"]}</hash></properties>'
                    propfile = self.temp_path / f"{key}.prop"
                    with open(propfile, "w") as pf:
                        pf.write(propfile_content)
                    remote_propfile = f"{key}.prop"

                    propfile_upload = webdav_uploader(self.webdav, remote_propfile, propfile)
                    if propfile_upload:
                        print("Propfile upload successful, proceeding...")
                    else:
                        print("Propfile upload failed, skipping...")
                        continue

                    self.zot.add_tags(item, "read")
                    print(f"{pdf_name.name} uploaded to Zotero.")
                    (self.temp_path / pdf_name).unlink()
                    (self.temp_path / attachment_zip).unlink()
                    (self.temp_path / propfile).unlink()
                    return pdf_name

    def get_sync_status(self):
        read_list = []
        for item in self.zot.items(tag="read"):
            for attachment in self.zot.children(item["key"]):
                if "contentType" in attachment["data"] and attachment["data"]["contentType"] == "application/pdf":
                    read_list.append(attachment["data"]["filename"])

        return read_list

    def push(self):
        sync_items = self.zot.items(tag="to_sync")
        print(f"Found {len(sync_items)} elements to sync...")
        for item in tqdm(sync_items):
            if self.webdav:
                self.sync_to_rm_webdav(item)
            else:
                self.sync_to_rm(item)
        self.zot.delete_tags("to_sync")

    def pull(self):
        files_list = self.rmapi.get_files(self.read_folder_path)
        if files_list:
            for entity in tqdm(files_list):
                pdf_name = self.download_from_rm(entity, self.read_folder_path)
                if self.webdav:
                    self.zotero_upload_webdav(pdf_name)
                else:
                    self.zotero_upload(pdf_name)
        else:
            print("No files to pull found")
