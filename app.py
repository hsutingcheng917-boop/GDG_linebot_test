import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 v2 穩定版導入
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 設定 Gemini 模型
# 嘗試使用 -latest 結尾，這通常能解決 404 找不到特定版本的問題
MODEL_NAME = 'gemini-1.5-flash-latest'

# 取得 API Key
genai_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=genai_key)

# 建立模型實例
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
            reply_text = "模型目前沒有回傳內容，請嘗試換個問題。"
            
    except Exception as e:
        app.logger.error(f"Gemini 錯誤: {e}")
        # 如果還是 404，回傳更具體的提示
        error_msg = str(e)
        if "404" in error_msg:
            reply_text = "連線失敗：請確認 Google API Key 是否有效並已更換新金鑰。"
        else:
            reply_text = f"思考發生錯誤：{error_msg[:50]}"

    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
