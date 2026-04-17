import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 v2 穩定版導入，確保與你的 reply_message 邏輯相容
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 設定 Gemini 模型
# 使用 1.5-flash 以解決 404 找不到模型的問題，這是目前最穩定的 Flash (Lite) 模型
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 初始化 LINE API
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')

if not line_token or not line_secret:
    raise ValueError("環境變數 LINE_TOKEN 或 LINE_SECRET 缺失，請在 Render 後台設定。")

line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

# 4. 建立 Flask 應用
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("LINE 簽名驗證失敗，請檢查 Channel Secret")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    try:
        # 呼叫 Gemini
        response = model.generate_content(user_text)
        
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "機器人目前無法產生回應，請換個方式問問看。"
            
    except Exception as e:
        app.logger.error(f"Gemini 錯誤: {e}")
        # 將錯誤訊息簡化回傳，方便你即時除錯
        reply_text = f"思考發生錯誤：{str(e)[:50]}"

    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # Render 部署關鍵：讀取動態 PORT 並監聽 0.0.0.0
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
