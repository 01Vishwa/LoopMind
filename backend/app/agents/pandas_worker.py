from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_llm
from app.core.sandbox import execute_safe_code
from app.services.file_manager import FileManager

def pandas_node(state):
    """
    Pandas Worker Node.
    Generates and executes pandas code.
    """
    messages = state['messages']
    file_id = state['file_id']
    
    # Load Data
    df = FileManager.read_csv(file_id)
    
    llm = get_llm()
    prompt = f"""
    You are a Data Analyst. 
    The user asked: {messages[-1].content}
    The dataframe 'df' is loaded.
    Columns: {df.columns.tolist()}
    
    Write python code to answer the question or prepare data.
    Assign the result to variable `result`.
    Do NOT use print().
    Return ONLY the code.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    code = response.content.replace("```python", "").replace("```", "").strip()
    
    # Execute
    exec_result = execute_safe_code(code, df)
    
    output_msg = f"Executed code. Result: {exec_result['result']}\nOutput: {exec_result['output']}"
    if exec_result['error']:
        output_msg += f"\nError: {exec_result['error']}"
        
    return {
        "executed_code": code,
        "answer": str(exec_result['result']),
        "messages": [HumanMessage(content=output_msg)]
    }
