import requests
import time
import threading
from flask import Flask
import google.generativeai as genai

# ===== Cấu hình =====
GEMINI_API_KEY = "AIzaSyDm_-uOIOn12Eexup3cFBpzHuRDDjUCKgg"
BLYNK_TOKEN = "DTvoVQ9dmAIpfwvUATHcSVw8fwx23L0V"
BLYNK_BASE_URL = "https://blynk.cloud/external/api"

# Cấu hình Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Flask app (để Render nhận diện port)
app = Flask(__name__)

# ==== Hàm Blynk API ====
def get_value(pin):
    """Lấy dữ liệu từ Blynk Cloud"""
    url = f"{BLYNK_BASE_URL}/get?token={BLYNK_TOKEN}&{pin}"
    res = requests.get(url)
    if res.status_code == 200 and res.text.strip() != "":
        return res.text.strip()
    return ""


def set_value(pin, val):
    """Gửi dữ liệu lên Blynk Cloud"""
    url = f"{BLYNK_BASE_URL}/update?token={BLYNK_TOKEN}&{pin}={val}"
    requests.get(url)


def write_output_long(msg, chunk_size=200):
    """Chia nhỏ và gửi tin nhắn dài vào Terminal Output (V6)"""
    parts = [msg[i:i + chunk_size] for i in range(0, len(msg), chunk_size)]
    for p in parts:
        set_value("V6", p)
        time.sleep(0.2)


def clear_input():
    """Xóa nội dung ô nhập V5 sau khi xử lý"""
    set_value("V5", "")


# ==== Hàm Gemini ====
def ask_gemini(prompt_text, history):
    model = genai.GenerativeModel("models/gemini-pro-latest")

    # Ghép toàn bộ lịch sử hội thoại
    full_prompt = ""
    for item in history:
        full_prompt += f"{item['role'].capitalize()}: {item['content']}\n"
    full_prompt += f"User: {prompt_text}"

    response = model.generate_content(full_prompt)
    return response.text


# ==== Vòng lặp chính ====
def main_loop():
    conversation_history = []
    print("🤖 Bot đã khởi động. Hãy nhập câu hỏi vào V5 hoặc bật công tắc V7 để gửi dữ liệu cảm biến.")

    while True:
        try:
            # Đọc dữ liệu cảm biến
            temp = get_value("V1")
            hum = get_value("V2")
            soil = get_value("V3")

            # Kiểm tra switch V7 (kích hoạt AI tự động)
            switch_state = get_value("V7")
            if switch_state == "1":
                prompt = f"""
                Đây là dữ liệu cảm biến:
                - Nhiệt độ: {temp} °C
                - Độ ẩm không khí: {hum} %
                - Độ ẩm đất: {soil} %

                Hãy phân tích và đưa ra gợi ý điều khiển hệ thống tưới cây.
                """
                reply = ask_gemini(prompt, conversation_history)
                write_output_long(reply)

                conversation_history.append({'role': 'user', 'content': prompt})
                conversation_history.append({'role': 'assistant', 'content': reply})

                set_value("V7", "0")  # reset công tắc

            # Kiểm tra xem có câu hỏi thủ công nào từ V5 không
            user_input = get_value("V5")
            if user_input and user_input.strip() != "":
                reply = ask_gemini(user_input, conversation_history)
                write_output_long(reply)

                conversation_history.append({'role': 'user', 'content': user_input})
                conversation_history.append({'role': 'assistant', 'content': reply})

                clear_input()
            time.sleep(1)

        except Exception as e:
            print("⚠️ Lỗi:", e)
            time.sleep(2)


# ==== Flask route để Render nhận diện port ====
@app.route("/")
def home():
    return "✅ Bot Blynk + Gemini đang chạy ổn định trên Render!"


# ==== Chạy Flask + Thread song song ====
if __name__ == "__main__":
    # Chạy bot trong luồng riêng
    bot_thread = threading.Thread(target=main_loop, daemon=True)
    bot_thread.start()

    # Flask server mở cổng cho Render
    app.run(host="0.0.0.0", port=10000)
