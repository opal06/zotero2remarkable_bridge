import subprocess

def check_rmapi():
    check = subprocess.run(["rmapi", "ls"])
    if check.returncode == 0:
        return True
    else:
        return False
