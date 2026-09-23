"""Local deterministic AI transport fixture, used only by test_frontend --browser.

The real catalog service still validates the response and stores questions/answers.
Never imported by a production service. No provider keys or internet required.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

QUESTIONS = {
    "Russian": ["Кто будет пользоваться решением?", "Какие данные доступны?", "Какой результат ожидается?"],
    "Kazakh": ["Шешімді кім пайдаланады?", "Қандай деректер бар?", "Қандай нәтиже күтіледі?"],
    "English": ["Who will use the solution?", "What data is available?", "What outcome is expected?"],
}


def create_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/api/v1/ai/generate":
                self.send_error(404)
                return
            prompt = body["prompt"]
            if "fixture-unavailable" in prompt:
                self.send_error(503, "Controlled AI outage")
                return
            assert 'predominant language of the original business draft' in body['instructions']
            language = "Kazakh" if prompt.startswith("Бізге") else "Russian" if prompt.startswith("Нам") else "English"
            questions = [{"field": field, "question": question, "position": i}
                         for i, (field, question) in enumerate(zip(
                             ["users", "data", "expected_result"], QUESTIONS[language]))]
            content = json.dumps({"content": json.dumps({"questions": questions}, ensure_ascii=False)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
