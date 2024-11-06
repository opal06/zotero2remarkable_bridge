import subprocess
import json

def check_rmapi():
    check = subprocess.run(["rmapi", "ls"])
    if check.returncode == 0:
        return True
    else:
        return False


def get_files(folder):
    # Get all files from a specific folder. Output is sanetised and subfolders are excluded
    files = subprocess.run(["rmapi", "ls", folder], capture_output=True, text=True)
    if files.returncode == 0:
        files_list = files.stdout.split("\n")
        files_list_new = []
        for file in files_list:
            if file[:5] != " Time" and file[:3] != "[d]" and file != "":
                files_list_new.append(file[4:])
        return files_list_new
    else:
        return False


def download_file(file_path, working_dir):
    # Downloads a file (consisting of a zip file) to a specified directory
    downloader = subprocess.run(["rmapi", "geta", file_path], cwd=working_dir)
    if downloader.returncode == 0:
        return True
    else:
        return False


def get_metadata(file_path):
    # Get the file's metadata from reMarkable cloud and return it in metadata format
    metadata = subprocess.run(["rmapi", "stat", file_path], capture_output=True, text=True)
    if metadata.returncode == 0:
        metadata_txt = metadata.stdout
        json_start = metadata_txt.find("{")
        json_end = metadata_txt.find("}") + 1
        metadata = json.loads(metadata_txt[json_start:json_end])
        return metadata
    else:
        return False


def upload_file(file_path, target_folder):
    # Upload a file to its destination folder
    uploader = subprocess.run(["rmapi", "put", file_path, target_folder])
    if uploader.returncode == 0:
        return True
    else:
        return False
