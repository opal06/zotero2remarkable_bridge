import subprocess

def check_rmapi():
    check = subprocess.run(["rmapi", "ls"])
    if check.returncode == 0:
        return True
    else:
        return False


def get_files(folder):
    # Get all files from a specific folder. Output is sanetised and subfolders are excluded
    files = subprocess.run(["rmapi", "find", folder], capture_output=True, text=True)
    if files.returncode == 0:
        files_list = files.stdout.split("\n")
        for file in files_list:
            if file[:5] == " Time":
                files_list.remove(file)
            elif file[:3] == "[d]":
                files_list.remove(file)
            else:
                files_list[files_list.index(file)] = file[4:]
        return files_list
    else:
        return False


def download_file(file_path, working_dir):
    # Downloads a file (consisting of a zip file) to a specified directory
    downloader = subprocess.run(["rmapi", "get", file_path], cwd=working_dir)
    if downloader.returncode == 0:
        return True
    else:
        return False
