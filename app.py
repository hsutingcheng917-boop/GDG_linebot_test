import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 初始化 Gemini
genai_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=genai_key)

# 自動診斷：列出此 API Key 可用的所有模型
def get_available_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"此 API Key 可用的模型清單: {available_models}")
        
        # 優先順序：1.5-flash > 1.0-pro > 清單中的第一個
        if 'models/gemini-1.5-flash' in available_models:
            return 'gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            return 'gemini-pro'
        elif available_models:
            return available_models[0].replace('models/', '')
    except Exception as e:
        print(f"診斷失敗，無法取得模型清單: {e}")
    return 'gemini-1.5-flash' # 最終墊底方案

# 初始化模型
MODEL_NAME = get_available_model()
model = genai.GenerativeModel(MODEL_NAME)

# 3. 初始化 LINE API
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        # 使用偵測到的模型發送請求
        response = model.generate_content(user_text)
        reply_text = response.text if response.text else "模型未回傳文字。"
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Gemini Error: {error_msg}")
        # 如果還是報錯，把錯誤細節顯示在 LINE 上方便除錯
        reply_text = f"連線失敗！目前使用的模型是 {MODEL_NAME}。\n錯誤原因：{error_msg[:100]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
