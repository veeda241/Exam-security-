
import sys
import os
# Add server to path so we can import services
sys.path.append(os.path.abspath("server"))

try:
    print("Attempting to import get_transformer_analyzer...")
    from services.transformer_analysis import get_transformer_analyzer
    print("Import successful.")
    
    print("Initializing analyzer...")
    analyzer = get_transformer_analyzer()
    status = analyzer.get_status()
    print(f"Analyzer status: {status}")
    
    if status.get('transformer_available'):
        print("SUCCESS: Transformer is available and loaded.")
        
        # Try a simple encoding
        print("Testing encoding...")
        emb = analyzer.encode_text("This is a test.")
        if emb is not None:
             print(f"Encoding successful. Shape: {emb.shape}")
        else:
             print("Encoding returned None.")
             
    else:
        print("FAILURE: Transformer not available.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
