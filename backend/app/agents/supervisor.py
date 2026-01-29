from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from app.agents.pandas_worker import pandas_node
from app.agents.viz_worker import viz_node
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    file_id: str
    answer: str
    plot_json: dict
    executed_code: str
    next: str

def supervisor_node(state: AgentState):
    """
    Supervisor decides next step: 'pandas' or 'viz' or 'finish'.
    """
    llm = get_llm()
    last_message = state['messages'][-1].content
    
    prompt = f"""
    You are a supervisor.
    User request: {last_message}
    
    Decide if we need to:
    1. 'pandas': Process data / answer text questions.
    2. 'viz': Generate a plot (if user asks for chart/graph/plot).
    3. 'finish': If the task is done.
    
    Return ONLY one word: 'pandas', 'viz', or 'finish'.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    decision = response.content.strip().lower()
    
    if "viz" in decision:
        return {"next": "viz"}
    elif "pandas" in decision:
        return {"next": "pandas"}
    else:
        return {"next": "finish"}

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("pandas_worker", pandas_node)
    workflow.add_node("viz_worker", viz_node)
    
    workflow.set_entry_point("supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x.get("next", "finish"),
        {
            "pandas": "pandas_worker",
            "viz": "viz_worker",
            "finish": END
        }
    )
    
    workflow.add_edge("pandas_worker", "supervisor")
    workflow.add_edge("viz_worker", END) # End after viz usually
    
    return workflow.compile()

# Singleton
graph_runner = build_graph()
