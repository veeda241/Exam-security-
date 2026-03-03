import subprocess
import os
import sys

# Paths
server_dir = os.path.join(r"c:\hackathon\Gemini_CLI\Exam-security-", "server")
python_exe = os.path.join(server_dir, ".venv", "Scripts", "python.exe")
main_py = os.path.join(server_dir, "main.py")

print("Starting:", python_exe, main_py)
try:
    result = subprocess.run(
        [python_exe, main_py],
        cwd=server_dir,
        capture_output=True,
        text=True,
        timeout=10
    )
    with open(r"c:\hackathon\Gemini_CLI\Exam-security-\debug.log", "w") as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write("\nRETURN CODE: " + str(result.returncode))
except subprocess.TimeoutExpired as e:
    with open(r"c:\hackathon\Gemini_CLI\Exam-security-\debug.log", "w") as f:
        f.write("Timed out. STDOUT:\n" + str(e.stdout) + "\nSTDERR:\n" + str(e.stderr))
except Exception as e:
    with open(r"c:\hackathon\Gemini_CLI\Exam-security-\debug.log", "w") as f:
        f.write("Exception: " + str(e))
