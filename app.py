import google.generativeai as genai
import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 基礎設定
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# 2. 取得環境變數 (請確認 Render 後台已設定這些變數)
LINE_TOKEN = os.environ.get('LINE_TOKEN')
LINE_SECRET = os.environ.get('LINE_SECRET')
API_KEY = os.environ.get('GOOGLE_API_KEY')

# 3. 初始化工具
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)
genai.configure(api_key=API_KEY)

# 這裡使用最穩定的 ID，避開 2.0-lite 導致的 404
model = genai.GenerativeModel('gemini-1.5-flash')

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
    try:
        # 直接呼叫，不進行預先測試
        response = model.generate_content(event.message.text)
        reply_text = response.text if response.text else "抱歉，我暫時無法回答這個問題。"
    except Exception as e:
        reply_text = f"錯誤提示：{str(e)[:50]}"
        logging.error(f"Error: {e}")

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
