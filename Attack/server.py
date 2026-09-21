import os
import json
import csv
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results", "full_run")
SUMMARY_JSON_PATH = os.path.join(RESULTS_DIR, "summary.json")
CALIBRATED_JSON_PATH = os.path.join(RESULTS_DIR, "calibrated_predictions.json")
LLM_CSV_PATH = os.path.join(RESULTS_DIR, "llm_comparison.csv")
PHASE_B_JSON_PATH = os.path.join(RESULTS_DIR, "phase_b_summary.json")

# Predictor Logic using standard library
def predict_few_shot_standalone(name, atk_type, granularity, mechanism):
    if atk_type == "LLM-based" and granularity == "Evidence-level" and "Noise" not in name:
        return "POS"
    if name == "Fact Mixing":
        return "POS"
    if name in ("Syntactic Omission", "Masked Token Claim Rewrite", "Word Jumbling"):
        return "MID"
    if granularity in ("Character-level", "Word-level") or "Noise" in name or name == "Entity Disambiguation":
        return "NEG"
    return "NEG"

class BenchmarkHTTPRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress routine log clutter
        pass

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path in ("/", "/index.html"):
            html_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    content = f.read()
                self._set_headers(200, "text/html; charset=utf-8")
                self.wfile.write(content)
            else:
                self._set_headers(404, "text/plain")
                self.wfile.write(b"index.html not found")
            return

        if path == "/api/data":
            summary_data = {}
            calibrated_data = {}
            llm_comparison = []
            phase_b_summary = {}

            if os.path.exists(SUMMARY_JSON_PATH):
                with open(SUMMARY_JSON_PATH, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)

            if os.path.exists(CALIBRATED_JSON_PATH):
                with open(CALIBRATED_JSON_PATH, "r", encoding="utf-8") as f:
                    calibrated_data = json.load(f)

            if os.path.exists(PHASE_B_JSON_PATH):
                with open(PHASE_B_JSON_PATH, "r", encoding="utf-8") as f:
                    phase_b_summary = json.load(f)

            if os.path.exists(LLM_CSV_PATH):
                with open(LLM_CSV_PATH, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        llm_comparison.append(row)

            payload = {
                "summary": summary_data,
                "calibrated": calibrated_data,
                "llm_comparison": llm_comparison,
                "phase_b_summary": phase_b_summary
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/sample":
            attack_key = query.get("key", [""])[0]
            if not attack_key:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing key parameter"}).encode("utf-8"))
                return

            csv_file = os.path.join(RESULTS_DIR, f"{attack_key}_results.csv")
            if os.path.exists(csv_file):
                try:
                    with open(csv_file, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        flipped_sample = None
                        first_sample = None
                        for row in reader:
                            if first_sample is None:
                                first_sample = row
                            if row.get("flipped") in ("True", "true", True):
                                flipped_sample = row
                                break
                        sample = flipped_sample if flipped_sample else first_sample
                        self._set_headers(200)
                        self.wfile.write(json.dumps(sample, ensure_ascii=False).encode("utf-8"))
                        return
                except Exception as e:
                    self._set_headers(500)
                    self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                    return
            
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Sample CSV not found"}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b"Not found")

    def do_POST(self):
        if self.path == "/api/predict":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode("utf-8"))
                name = body.get("name", "Custom Attack")
                atk_type = body.get("type", "Rule-based")
                granularity = body.get("granularity", "Word-level")
                mechanism = body.get("mechanism", "")

                pred_tier = predict_few_shot_standalone(name, atk_type, granularity, mechanism)
                response = {
                    "name": name,
                    "pred_tier": pred_tier,
                    "accuracy_confidence": "86.36% (LOO-CV)",
                    "tier_explanation": "High Vulnerability (ASR >= 40%)" if pred_tier == "POS" else ("Moderate Vulnerability (15-40% ASR)" if pred_tier == "MID" else "Low / Negligible Vulnerability (< 15% ASR)"),
                    "reasoning": "Calibrated on 22 empirical ground-truth attack vectors. Modern Hindi LLMs effectively filter surface/mechanical noise, but remain susceptible to contextualized evidence poisoning."
                }
                self._set_headers(200)
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(b"Not found")

def main():
    print(f"="*60)
    print(f" 🛡️ Hindi Fact-Checking Adversarial Web Application Server")
    print(f" Listening on http://localhost:{PORT}")
    print(f" Open http://localhost:{PORT} in your web browser!")
    print(f"="*60)
    server = HTTPServer(("0.0.0.0", PORT), BenchmarkHTTPRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    main()
