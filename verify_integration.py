
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'server'))

try:
    print("Loading Transformer Analyzer...")
    from services.transformer_analysis import get_transformer_analyzer
    
    analyzer = get_transformer_analyzer()
    status = analyzer.get_status()
    
    print("\n=== Model Status ===")
    print(f"Initialized: {status.get('initialized')}")
    print(f"Transformer Available: {status.get('transformer_available')}")
    print(f"Model Loaded: {status.get('model_loaded')}")
    print(f"Device: {status.get('device')}")
    
    if status.get('model_loaded'):
        print("\nSUCCESS: Custom trained model loaded successfully!")
        
        # Test inference
        print("\nRunning test inference...")
        sim = analyzer.compute_similarity("The mitochondria is the powerhouse of the cell.", "Mitochondria produce energy.")
        print(f"Similarity Score: {sim.get('similarity'):.4f}")
    else:
        print("\nERROR: Model failed to load.")
        sys.exit(1)

except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
