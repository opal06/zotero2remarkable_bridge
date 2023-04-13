import subprocess
import json


class Rmapi:
    def __init__(self, working_dir):
        self.working_dir = str(working_dir)

    def check_rmapi(self):
        check = subprocess.run(["rmapi", "ls"])
        if check.returncode == 0:
            return True
        else:
            return False

    def get_files(self, folder):
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

    def download_file(self, file_path):
        # Downloads a file (consisting of a zip file) to a specified directory
        downloader = subprocess.run(["rmapi", "get", file_path], cwd=self.working_dir)
        if downloader.returncode == 0:
            return True
        else:
            return False

    def get_metadata(self, file_path):
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

    def upload_file(self, file_path, target_folder):
        # Upload a file to its destination folder
        uploader = subprocess.run(["rmapi", "put", file_path, target_folder])
        if uploader.returncode == 0:
            return True
        else:
            return False
