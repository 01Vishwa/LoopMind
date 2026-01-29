from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_llm
from app.rl_engine.bandit import bandit
import json

def viz_node(state):
    """
    Visualization Worker Node.
    Decides chart type using RL Engine.
    Generates Plotly JSON.
    """
    messages = state['messages']
    file_id = state.get('file_id') # Not really used here unless we need to inspect file, 
                                   # but we assume previous step provided valid data or context.
    # We might need context for RL. 
    # For now, let's assume specific keys in state or just basic context
    context = {
        "row_count": 100, # Placeholder or from previous analysis state
        "columns": ["date", "sales"], # Placeholder
        "dtypes": {"date": "datetime", "sales": "int"}
    }
    
    # RL Step
    chart_type = bandit.get_action(context)
    
    # Gen AI Step
    llm = get_llm()
    prompt = f"""
    The user wants a visualization. 
    You MUST generate a Plotly JSON object for a {chart_type} chart.
    Return ONLY the JSON. No markdown, no explanations.
    
    Context from previous steps: {messages[-1].content}
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    content = response.content.replace("```json", "").replace("```", "").strip()
    
    try:
        plot_json = json.loads(content)
    except:
        plot_json = {}

    return {
        "plot_json": plot_json,
        "executed_code": f"# Generated {chart_type} chart",
        "messages": [HumanMessage(content=f"Generated {chart_type} chart.")]
    }
