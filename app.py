import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 v2 穩定版導入，確保變數名稱與邏輯一致
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 取得並驗證環境變數 (順序關鍵：必須先取得變數)
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')
genai_key = os.getenv('GOOGLE_API_KEY')

if not line_token or not line_secret:
    # 如果變數缺失，直接在啟動時報錯，防止後續 NameError
    raise ValueError("環境變數 LINE_TOKEN 或 LINE_SECRET 缺失，請檢查設定")

# 3. 定義 handler 與 line_bot_api (必須在 @handler.add 之前定義)
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret) 

# 4. 初始化 Gemini
genai.configure(api_key=genai_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# 5. 建立 Flask 應用
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("LINE 簽名驗證失敗")
        abort(400)
    return 'OK'

# 6. 處理訊息 (這裡會用到上面定義好的 handler)
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        # 呼叫 Gemini
        response = model.generate_content(user_text)
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "目前無法產生回應，請稍後再試。"
    except Exception as e:
        error_msg = str(e)
        # 針對之前的 429 錯誤做友善提示
        if "429" in error_msg:
            reply_text = "【系統忙碌】API 額度已達上限，請等一分鐘後再試。"
        else:
            reply_text = f"思考發生錯誤：{error_msg[:50]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # Render 環境設定
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
