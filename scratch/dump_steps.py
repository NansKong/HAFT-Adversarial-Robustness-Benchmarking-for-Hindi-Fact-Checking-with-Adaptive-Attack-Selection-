import json

transcript_path = r"C:\Users\ASUS\.gemini\antigravity-ide\brain\968d5c47-5a3c-495a-b1ae-c28132a2a1fb\.system_generated\logs\transcript.jsonl"
steps_to_find = [2533, 2534, 2543, 2544]

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        idx = data.get("step_index", 0)
        if idx in steps_to_find:
            print(f"=== STEP {idx} ===")
            if "content" in data and data["content"]:
                print("CONTENT:\n", data["content"])
            if "tool_calls" in data:
                print("TOOL_CALLS:\n", json.dumps(data["tool_calls"], indent=2, ensure_ascii=False))
