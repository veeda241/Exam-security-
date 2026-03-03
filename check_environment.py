
import os
try:
    with open(r'c:\hackathon\Gemini_CLI\Exam-security-\env_check.txt', 'w') as f:
        f.write('It works!\n')
        f.write(f"CWD: {os.getcwd()}\n")
except Exception as e:
    print(f"Failed: {e}")
