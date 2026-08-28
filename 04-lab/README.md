# Lab 04 — Weather Agent with Remote MCP Server

A weather agent built with Google ADK that connects to an MCP server via Streamable HTTP transport.

## Architecture

```
┌─────────────────┐   Streamable HTTP    ┌─────────────────┐      REST       ┌─────────────────┐
│   ADK Agent     │ ──────────────────── │   MCP Server    │ ─────────────── │  WeatherAPI.com │
│  (mcp-client)   │   localhost:8085/mcp │  (mcp-server)   │                 │                 │
└─────────────────┘                      └─────────────────┘                 └─────────────────┘
```

## Tools

The server publishes three MCP tools. Their input/output contracts are:

### `get_current_weather`

- **Input:** `city: string` — city name, for example `Hanoi` or `Sydney`.
- **Output:** `string` containing the location, temperature in Celsius and
  Fahrenheit, feels-like temperature, condition, humidity, wind, pressure, UV,
  visibility, and last-updated time.
- **Error output:** a readable error string when `WEATHERAPI_KEY` is missing,
  the city is invalid, or WeatherAPI cannot be reached.

Example success output:

```text
Current Weather for Hanoi, Hanoi, Vietnam:
Temperature: 29.0°C (84.2°F)
Condition: Partly cloudy
Humidity: 70%
Wind: 12.0 km/h (7.5 mph) SE
```

### `get_forecast`

- **Input:** `city: string` and optional `days: integer` (default `3`).
- **Validation:** `days` is limited to the free-tier range `1–3`.
- **Output:** `string` containing one forecast block per day, including date,
  high/low temperature, condition, chance of rain, maximum wind, and UV index.
- **Error output:** a readable error string when `WEATHERAPI_KEY` is missing,
  the city is invalid, or WeatherAPI cannot be reached.

### `health_check`

- **Input:** none.
- **Output:** the string
  `✅ Weather MCP Server is running and ready to provide worldwide weather data.`
- **Purpose:** verifies that the MCP server is running without calling
  WeatherAPI.

## ADK làm gì trong Lab này?

ADK (Agent Development Kit) đóng vai trò **MCP Client** 
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. KẾT NỐI tới MCP Server qua Streamable HTTP                  │
│     StreamableHTTPConnectionParams(url="http://localhost:8085/mcp") │
│                                                                 │
│  2. KHÁM PHÁ tools tự động (list_tools)                         │
│     McpToolset → tự hỏi server "anh có tool gì?"                │
│     → nhận về: get_current_weather, get_forecast, health_check  │
│                                                                 │
│  3. TRUYỀN tools cho LLM (Gemini)                               │
│     Agent(model="gemini-2.5-flash", tools=[weather_tools])      │
│     → Gemini biết nó có thể gọi 3 tools trên                    │
│                                                                 │
│  4. ĐIỀU PHỐI vòng lặp Function Calling                         │
│     User hỏi → Gemini chọn tool → ADK gọi MCP Server            │
│     → nhận kết quả → đưa lại cho Gemini tổng hợp                │
│                                                                 │
│  5. CUNG CẤP giao diện web (adk web)                            │
│     → http://localhost:8000 để chat với agent                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

So với bài 02 (viết client thủ công bằng `mcp.ClientSession`), ADK giúp bạn **không phải viết vòng lặp function calling thủ công** nữa. Toàn bộ luồng list_tools → model quyết định → call_tool → model tổng hợp được ADK xử lý tự động.

## Setup

### 1. MCP Server

```bash
cd mcp-server
uv sync

# Set your WeatherAPI key (get one free at https://weatherapi.com)
# macOS/Linux:
export WEATHERAPI_KEY="your_weatherapi_key"
# Windows PowerShell:
# $env:WEATHERAPI_KEY="your_weatherapi_key"

# Start the server (runs on port 8085 by default)
uv run python weather.py
```

The server will be available at `http://localhost:8085/mcp`.

### 2. ADK Agent (Client)

```bash
cd mcp-client
uv sync

# Copy .env.example to .env and fill in GOOGLE_API_KEY.
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env

# Start ADK web interface
uv run python verify_setup.py
uv run adk web
```

Open http://localhost:8000 in your browser, select `weather_agent`, and ask about the weather.

The server and client run in two terminals. To use a deployed server, set
`MCP_SERVER_URL` in `mcp-client/.env` to its `/mcp` endpoint.

## Configuration

| Variable | Where | Description |
|----------|-------|-------------|
| `WEATHERAPI_KEY` | mcp-server | API key from weatherapi.com |
| `GOOGLE_API_KEY` | mcp-client/.env | Gemini API key |
| `PORT` | mcp-server (env) | Override server port (default: 8085) |
| `MCP_SERVER_URL` | mcp-client/.env | MCP endpoint (default: `http://localhost:8085/mcp`) |
| `GEMINI_MODEL` | mcp-client/.env | Gemini model (default: `gemini-2.5-flash`) |
| `MCP_TRANSPORT` | mcp-server (env) | `streamable-http` or `stdio` |
