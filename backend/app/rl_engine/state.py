from typing import Dict
import pandas as pd

def analyze_dataframe_context(df: pd.DataFrame) -> Dict:
    """
    Extracts context features from a dataframe.
    """
    context = {}
    
    # 1. Row count
    context['row_count'] = len(df)
    
    # 2. Is Time Series?
    # Check if any column is datetime or looks like a date
    is_time_series = False
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            is_time_series = True
            break
        # Primitive check for string dates
        if df[col].dtype == 'object':
            try:
                pd.to_datetime(df[col], errors='raise')
                is_time_series = True
                break
            except:
                pass
                
    context['is_time_series'] = is_time_series
    
    return context
