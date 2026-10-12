import json

transcript_path = r"C:\Users\ASUS\.gemini\antigravity-ide\brain\968d5c47-5a3c-495a-b1ae-c28132a2a1fb\.system_generated\logs\transcript.jsonl"
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        idx = data.get("step_index", 0)
        if idx >= 2530:
            src = data.get("source")
            typ = data.get("type")
            content = data.get("content", "")
            print(f"=== STEP {idx} [{src}] [{typ}] ===")
            if content:
                print(content[:1500])
            if "tool_calls" in data:
                print("TOOL CALLS:", [tc.get("name") for tc in data["tool_calls"]])
