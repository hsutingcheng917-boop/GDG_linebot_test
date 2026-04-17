import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 v2 穩定版
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 取得設定
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')
genai_key = os.getenv('GOOGLE_API_KEY')

# 3. 初始化 LINE API (必須在 handler.add 之前)
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

# 4. 初始化 Gemini
genai.configure(api_key=genai_key)

# 使用 'gemini-1.5-flash-latest' 通常比固定版本號更穩定
model = genai.GenerativeModel('gemini-1.5-flash-latest')

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
        # 呼叫 Gemini
        response = model.generate_content(user_text)
        
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "機器人目前無法產生內容，請換個問題試試。"
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Gemini Error: {error_msg}")
        
        # 錯誤診斷回覆
        if "404" in error_msg:
            reply_text = "系統錯誤(404)：請檢查 Render 的 google-generativeai 版本是否已更新。"
        elif "429" in error_msg:
            reply_text = "系統忙碌(429)：額度已達上限，請稍後再試。"
        else:
            reply_text = f"思考發生錯誤：{error_msg[:50]}"

    # 回覆 LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
