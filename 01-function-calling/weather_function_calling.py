"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

import argparse
import json
import os
import sys

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"
MAX_TOOL_ROUNDS = 5

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


def configure_console() -> None:
    """Keep Vietnamese output working on Windows' legacy console."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def create_client() -> genai.Client:
    """Create the Gemini client only when a request is actually made."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY. Hãy đặt biến môi trường trước khi chạy."
        )
    return genai.Client(api_key=api_key)


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run(prompt: str, client: genai.Client | None = None) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    if not prompt.strip():
        raise ValueError("Prompt không được để trống.")

    client = client or create_client()
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    def generate() -> types.GenerateContentResponse:
        # 3. Gọi model — model quyết định có gọi tool hay không
        return client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", MODEL),
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    for _ in range(MAX_TOOL_ROUNDS):
        resp = generate()
        if not resp.function_calls:
            return resp.text or "Model không trả về nội dung."

        # Thêm phản hồi của model vào lịch sử hội thoại
        if not resp.candidates:
            raise RuntimeError("Gemini trả về function call nhưng thiếu candidate.")
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            if fc.name != "get_weather":
                result = json.dumps(
                    {"error": f"Tool không được hỗ trợ: {fc.name}"},
                    ensure_ascii=False,
                )
            else:
                result = get_weather(**fc.args)  # <-- app chạy, không phải model
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))

    raise RuntimeError("Model vượt quá số vòng gọi tool cho phép.")


if __name__ == "__main__":
    configure_console()
    parser = argparse.ArgumentParser(description="Demo Gemini Function Calling")
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Câu hỏi thời tiết; bỏ trống để dùng câu hỏi mẫu",
    )
    args = parser.parse_args()
    question = " ".join(args.prompt) or "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    try:
        print("Trả lời:", run(question))
    except (RuntimeError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
