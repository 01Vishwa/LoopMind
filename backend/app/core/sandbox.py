import pandas as pd
import io
import sys

# TODO: Replace with E2B
def execute_safe_code(code: str, df: pd.DataFrame) -> dict:
    """
    Executes pandas code. 
    Assumes code relies on a variable `df`.
    Returns {'output': str, 'error': str, 'result': any}
    """
    local_scope = {"df": df.copy(), "pd": pd}
    # Capture stdout
    old_stdout = sys.stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    error = None
    result = None
    
    try:
        exec(code, {}, local_scope)
        # We can look for specific variables if the code is meant to return something
        # For now, we assume it prints or modifies df.
        result = local_scope.get("result", None) # Convention: if code sets result=...
    except Exception as e:
        error = str(e)
    finally:
        sys.stdout = old_stdout
        
    return {
        "output": captured_output.getvalue(),
        "error": error,
        "result": result,
        "df_head": local_scope["df"].head().to_json() # Return partial df state
    }
