from scrum_team.nodes.prompt_agent import generate_brief

def test_prompt():
    raw = "I want a simple web app that tracks my gym workouts. It needs to save to a file, look nice with CSS, and let me add sets/reps. Urgent and needs to be done fast."
    print(f"Testing input: {raw}\n")
    
    brief = generate_brief(raw)
    print("Generated Structured Brief:")
    print(brief.model_dump_json(indent=2))

if __name__ == "__main__":
    test_prompt()
