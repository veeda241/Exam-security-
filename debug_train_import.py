
import sys
import os
from pathlib import Path

# Add transformer dir to path
sys.path.insert(0, str(Path("transformer").resolve()))

print(f"Path: {sys.path[0]}")

try:
    print("Importing model...")
    import model
    print("Model imported.")
    
    print("Importing Transformer from model...")
    from model import Transformer
    print("Transformer imported.")
    
    t = Transformer(10, 10, 16, 2, 2, 2, 32, 10, 0)
    print("Transformer instantiated.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
