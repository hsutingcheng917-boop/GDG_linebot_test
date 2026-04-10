import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 linebot v2 的導入方式
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 加載 .env 文件
load_dotenv()

# 設定 API Key 與 Token (請確保你的 .env 檔有這三項)
genai_key = os.getenv('GOOGLE_API_KEY')
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')

# 設定 Google Gemini
genai.configure(api_key=genai_key)
# 修正模型名稱為標準 ID
model = genai.GenerativeModel('gemini-1.5-flash') 

# 初始化 LINE API
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("無效的簽名，請檢查 Channel Secret")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    app.logger.info(f"收到的訊息: {user_message}")

    try:
        # 呼叫 Gemini 生成回應
        response = model.generate_content(user_message)
        
        # 檢查 response 是否有內容
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "抱歉，我暫時無法處理這段訊息。"
            
    except Exception as e:
        app.logger.error(f"Gemini API 錯誤: {e}")
        reply_text = "機器人思考時發生錯誤，請稍後再試。"

    # 回覆 LINE 訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # 確保埠號與 Render/Heroku 等平台相容
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
