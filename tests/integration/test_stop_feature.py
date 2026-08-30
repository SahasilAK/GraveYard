import threading
import time
from scrum_team.runner import run_project_graph, request_stop, get_project_state

def test_stop_feature():
    logs = []
    def logger(msg):
        logs.append(msg)
        print(f"[LOG] {msg}")

    proj_id = "test-stop-project"
    
    # 1. Trigger stop midway through graph run
    def trigger_stop_later():
        time.sleep(0.1)
        print("--> Triggering emergency stop signal...")
        request_stop()

    stop_thread = threading.Thread(target=trigger_stop_later)
    stop_thread.start()

    run_project_graph(proj_id, raw_input="Create complex multi-tier app", log_callback=logger)
    stop_thread.join()

    print("\nLogs recorded:")
    for l in logs:
        print("  -", l)
    
    assert any("halted by user request" in l for l in logs), "Expected stop signal log in execution output"
    print("\nSUCCESS: Emergency Stop feature verified successfully!")

if __name__ == "__main__":
    test_stop_feature()
