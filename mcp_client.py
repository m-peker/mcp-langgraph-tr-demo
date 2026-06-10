import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, TypedDict

import requests
from dotenv import load_dotenv


load_dotenv()


def _schema_field_names(schema: Dict[str, Any]) -> List[str]:
    properties = schema.get("properties") or {}
    if set(properties.keys()) == {"input"} and isinstance(properties["input"], dict):
        nested = properties["input"].get("properties") or {}
        if nested:
            return list(nested.keys())
    return list(properties.keys())


def build_tool_call_arguments(arguments: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """FastMCP tools in this project accept one Pydantic model named input."""
    if set(arguments.keys()) == {"input"} and isinstance(arguments["input"], dict):
        return arguments
    return {"input": arguments}


def build_tool_catalog(tools: List[Dict[str, Any]]) -> str:
    """Render discovered MCP tools for the routing prompt."""
    if not tools:
        return "- No MCP tools discovered."

    lines = []
    for tool in tools:
        schema = tool.get("inputSchema") or {}
        fields = _schema_field_names(schema)
        field_names = ", ".join(fields) if fields else "no declared fields"
        description = tool.get("description") or "No description"
        lines.append(f"- {tool.get('name')}: {description}. Fields: {field_names}")
    return "\n".join(lines)


def deterministic_route(message: str) -> Optional[Dict[str, Any]]:
    """Catch common Turkish demo questions before asking the LLM router."""
    stripped = message.strip()
    lowered = stripped.lower()

    if "hava durumu" in lowered:
        city = re.sub(r"\bhava\s+durumu\b", "", stripped, flags=re.IGNORECASE).strip(" .,:;?")
        if city:
            return {"tool": "get_weather", "parameters": {"city": city}, "reasoning": "deterministic weather route"}

    if "karekök" in lowered or "karekok" in lowered:
        expression_part = re.split(r"\brakam[ıi]n[ıi]n\b|\bkarek[öo]k", stripped, flags=re.IGNORECASE)[0]
        expression = re.sub(r"[^0-9+\-*/().\s]", "", expression_part).strip()
        if expression:
            return {
                "tool": "calculate",
                "parameters": {"expression": f"sqrt({expression})"},
                "reasoning": "deterministic math route",
            }

    if re.search(r"\d\s*[+\-*/]\s*\d", stripped):
        expression = re.sub(r"[^0-9+\-*/().\s]", "", stripped).strip()
        if expression:
            return {"tool": "calculate", "parameters": {"expression": expression}, "reasoning": "deterministic math route"}

    return None


def _unwrap_mcp_result(tool_result: Any) -> Any:
    if isinstance(tool_result, dict) and isinstance(tool_result.get("content"), list):
        for item in tool_result["content"]:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text") or ""
                try:
                    return json.loads(text)
                except Exception:
                    return text
    return tool_result


def _format_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _translate_weather_condition(condition: str) -> str:
    translations = {
        "sunny": "Güneşli",
        "clear": "Açık",
        "partly cloudy": "Parçalı bulutlu",
        "cloudy": "Bulutlu",
        "overcast": "Kapalı",
        "patchy rain nearby": "Yakınlarda yer yer yağmur",
        "light rain": "Hafif yağmur",
        "moderate rain": "Orta şiddette yağmur",
        "heavy rain": "Şiddetli yağmur",
        "snow": "Kar",
        "mist": "Sisli",
        "fog": "Sisli",
    }
    return translations.get(condition.strip().lower(), condition)


def _format_percent(value: Any) -> str:
    text = str(value).strip()
    if text.endswith("%"):
        return f"%{text[:-1]}"
    return text


def format_tool_result(tool_name: Optional[str], tool_result: Any) -> Optional[str]:
    """Return deterministic answers for tools where LLM rephrasing can hurt correctness."""
    data = _unwrap_mcp_result(tool_result)
    if tool_name == "calculate" and isinstance(data, dict) and "result" in data:
        return f"{data.get('expression')} = {_format_number(data['result'])}"
    if tool_name == "get_weather" and isinstance(data, dict):
        if "error" in data:
            location = data.get("city") or data.get("location") or "Bu konum"
            return f"{location} için hava durumu alınamadı. Servis geçici hata döndürdü veya konum çok belirsiz olabilir."
        if "location" in data:
            condition = _translate_weather_condition(str(data.get("condition", "Bilinmiyor")))
            return (
                f"{data['location']} için hava durumu: {condition}. "
                f"Sıcaklık {data.get('temperature', 'bilinmiyor')}, hissedilen {data.get('feels_like', 'bilinmiyor')}. "
                f"Nem {_format_percent(data.get('humidity', 'bilinmiyor'))}, rüzgar {data.get('wind', 'bilinmiyor')}."
            )
    return None


def parse_routing_decision(raw: str) -> Dict[str, Any]:
    """Parse LLM routing JSON with a safe fallback."""
    try:
        data = json.loads(raw)
        return {
            "tool": data.get("tool") or "none",
            "parameters": data.get("parameters"),
            "reasoning": data.get("reasoning") or "",
        }
    except Exception:
        return {"tool": "none", "parameters": None, "reasoning": "Routing JSON could not be parsed."}


def build_ollama_chat_payload(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    json_mode: bool = False,
) -> Dict[str, Any]:
    """Build a non-streaming Ollama chat request payload."""
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"
    return payload


def extract_ollama_message(response_data: Dict[str, Any]) -> str:
    """Extract assistant content from an Ollama /api/chat response."""
    message = response_data.get("message") or {}
    return message.get("content") or ""


class OllamaChatClient:
    """Small adapter around Ollama's local /api/chat endpoint."""

    def __init__(self, model: str = "llama3:latest", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3, json_mode: bool = False) -> str:
        payload = build_ollama_chat_payload(self.model, messages, temperature, json_mode)
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        return extract_ollama_message(response.json())


class StdioMCPClient:
    """Small JSON-RPC client for an MCP server running over STDIO."""

    def __init__(self, server_script: str = "mcp_server.py") -> None:
        self.server_script = server_script
        self.server: Optional[subprocess.Popen[str]] = None
        self.request_id = 0

    def start(self) -> None:
        self.server = subprocess.Popen(
            [sys.executable, self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        time.sleep(0.5)

    def _drain_stderr(self) -> None:
        if not self.server or not self.server.stderr:
            return
        for _line in self.server.stderr:
            pass

    def stop(self) -> None:
        if self.server:
            self.server.terminate()
            self.server = None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.server or not self.server.stdin or not self.server.stdout:
            raise RuntimeError("MCP server is not running")

        self.request_id += 1
        request: Dict[str, Any] = {"jsonrpc": "2.0", "id": str(self.request_id), "method": method}
        if params is not None:
            request["params"] = params

        self.server.stdin.write(json.dumps(request) + "\n")
        self.server.stdin.flush()
        response = self.server.stdout.readline().strip()
        return json.loads(response)

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        if not self.server or not self.server.stdin:
            raise RuntimeError("MCP server is not running")

        notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            notification["params"] = params
        self.server.stdin.write(json.dumps(notification) + "\n")
        self.server.stdin.flush()

    def initialize(self) -> Dict[str, Any]:
        response = self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "turkce-mcp-client", "version": "1.0.0"},
            },
        )
        self.send_notification("initialized")
        return response

    def list_tools(self) -> List[Dict[str, Any]]:
        response = self.send_request("tools/list")
        result = response.get("result") or {}
        return result.get("tools") or []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        response = self.send_request(
            "tools/call",
            {"name": name, "arguments": build_tool_call_arguments(arguments)},
        )
        if "error" in response:
            return {"error": response["error"]}
        return response.get("result")


class AgentState(TypedDict, total=False):
    msg: str
    tools: List[Dict[str, Any]]
    selected_tool: Optional[str]
    tool_result: Any
    result: str


def build_graph(mcp_client: StdioMCPClient, llm_client: Optional[OllamaChatClient] = None):
    from langgraph.graph import END, StateGraph

    llm = llm_client or OllamaChatClient(
        model=os.getenv("OLLAMA_MODEL", "llama3:latest"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )

    def route_request(state: AgentState) -> AgentState:
        deterministic_decision = deterministic_route(state["msg"])
        if deterministic_decision:
            return {
                "msg": state["msg"],
                "tools": state.get("tools", []),
                "selected_tool": deterministic_decision["tool"],
                "tool_result": mcp_client.call_tool(
                    deterministic_decision["tool"],
                    deterministic_decision["parameters"],
                ),
            }

        catalog = build_tool_catalog(state.get("tools", []))
        routing_prompt = f"""Kullanici istegini analiz et ve gerekiyorsa bir MCP tool sec.

Kullanici istegi: {state["msg"]}

Kesfedilen MCP tool'lari:
{catalog}

Sadece asagidaki JSON formatinda cevap ver:
{{
  "tool": "tool_adi" veya "none",
  "parameters": {{}} veya null,
  "reasoning": "kisa gerekce"
}}
"""
        response = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": "Sen yalnizca gecerli JSON ureten bir tool routing asistanisin.",
                },
                {"role": "user", "content": routing_prompt},
            ],
            temperature=0.2,
            json_mode=True,
        )
        decision = parse_routing_decision(response)
        tool = decision["tool"]
        parameters = decision["parameters"]

        if tool != "none" and parameters:
            return {
                "msg": state["msg"],
                "tools": state.get("tools", []),
                "selected_tool": tool,
                "tool_result": mcp_client.call_tool(tool, parameters),
            }
        return {"msg": state["msg"], "tools": state.get("tools", []), "selected_tool": None, "tool_result": None}

    def generate_response(state: AgentState) -> AgentState:
        formatted = format_tool_result(state.get("selected_tool"), state.get("tool_result"))
        if formatted is not None:
            return {
                "msg": state["msg"],
                "tools": state.get("tools", []),
                "selected_tool": state.get("selected_tool"),
                "tool_result": state.get("tool_result"),
                "result": formatted,
            }

        tool_data = json.dumps(state.get("tool_result"), ensure_ascii=False, indent=2)
        if state.get("tool_result") is None:
            user_content = state["msg"]
        else:
            user_content = f"Kullanici sorusu: {state['msg']}\n\nTool sonucu:\n{tool_data}"

        response = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": "Turkce cevap veren, kisa ve ogretici bir asistansin.",
                },
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
        )
        return {
            "msg": state["msg"],
            "tools": state.get("tools", []),
            "selected_tool": state.get("selected_tool"),
            "tool_result": state.get("tool_result"),
            "result": response,
        }

    graph = StateGraph(AgentState)
    graph.add_node("route", route_request)
    graph.add_node("respond", generate_response)
    graph.set_entry_point("route")
    graph.add_edge("route", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def run_demo() -> None:
    mcp_client = StdioMCPClient()
    mcp_client.start()
    try:
        print("MCP handshake baslatiliyor...")
        init_response = mcp_client.initialize()
        print(json.dumps(init_response, ensure_ascii=False, indent=2))

        tools = mcp_client.list_tools()
        print("\nKesfedilen tool'lar:")
        print(build_tool_catalog(tools))

        graph = build_graph(mcp_client)
        examples = [
            "Istanbul hava durumu nasil?",
            "25 * 4 + 10 / 2 kac eder?",
            "Bu metni analiz et: MCP MCP LangGraph agent agent tool.",
            "MCP ve LangGraph ogrenmek icin 7 gunluk plan hazirla.",
        ]
        for message in examples:
            result = graph.invoke({"msg": message, "tools": tools})
            print("\nUSER:", message)
            print("AGENT:", result["result"])

        print("\nArtik soru sorabilirsin. Cikmak icin 'exit', 'quit' veya 'q' yaz.")
        while True:
            message = input("\nSEN: ").strip()
            if message.lower() in {"exit", "quit", "q"}:
                print("Gorusuruz.")
                break
            if not message:
                continue
            result = graph.invoke({"msg": message, "tools": tools})
            print("AGENT:", result["result"])
    finally:
        mcp_client.stop()


if __name__ == "__main__":
    run_demo()
