from scrum_team.graph import create_graph

def test_skeleton():
    graph = create_graph()
    thread_id = "test-project-001"
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "project_id": thread_id,
        "raw_input": "Build a gym tracker app."
    }
    
    print("Running skeleton graph...")
    for output in graph.stream(initial_state, config=config):
        print(output)
    
    print("Graph run complete.")

if __name__ == "__main__":
    test_skeleton()
