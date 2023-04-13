from hashlib import md5
from datetime import datetime
from time import sleep


def get_md5(pdf):
    if pdf.is_file():
        with open(pdf, "rb") as f:
            f_bytes = f.read()
            md5_sum = md5(f_bytes).hexdigest()
    else:
        md5_sum = None
    return md5_sum


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
