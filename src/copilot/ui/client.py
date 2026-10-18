"""Typed client for the copilot HTTP API (used by the Streamlit app, usable by any script).

The UI talks to the agent only through this client, exactly like an external system would.
"""

import httpx

DEFAULT_URL = "http://localhost:8000"
TIMEOUT_S = 180  # an agent answer can take tens of seconds when it calls many tools


class ApiError(Exception):
    """The API answered with an error; `str(err)` is the server's readable message."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status


class CopilotClient:
    def __init__(self, base_url: str = DEFAULT_URL, api_key: str | None = None,
                 http: httpx.Client | None = None):
        headers = {"X-API-Key": api_key} if api_key else {}
        # `http` lets tests pass FastAPI's TestClient instead of a real network client
        self.http = http or httpx.Client(base_url=base_url, timeout=TIMEOUT_S)
        self.http.headers.update(headers)

    def _call(self, method: str, path: str, json: dict | None = None) -> dict:
        try:
            res = self.http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise ApiError(0, f"Cannot reach the API ({exc.__class__.__name__}). "
                              "Is the server running?") from exc
        if res.status_code >= 400:
            try:
                detail = res.json().get("detail", res.text)
            except ValueError:
                detail = res.text or res.reason_phrase
            raise ApiError(res.status_code, str(detail))
        return res.json()

    def health(self) -> dict:
        return self._call("GET", "/health")

    def ask(self, question: str, thread_id: str | None = None) -> dict:
        return self._call("POST", "/ask", {"question": question, "thread_id": thread_id})

    def approve(self, thread_id: str, approved: bool, comment: str = "",
                edited_body: str | None = None, approver: str = "streamlit user") -> dict:
        return self._call("POST", f"/threads/{thread_id}/approve",
                          {"approved": approved, "comment": comment,
                           "edited_body": edited_body, "approver": approver})
