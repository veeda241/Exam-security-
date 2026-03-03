
import sys
import os
import torch
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"Torch: {torch.__version__}")
print("CUDA Available:", torch.cuda.is_available())
with open("execution_check.txt", "w") as f:
    f.write("Execution successful\n")
print("File execution_check.txt created.")
