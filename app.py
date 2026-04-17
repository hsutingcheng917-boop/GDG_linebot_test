import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

load_dotenv()

# 1. 取得金鑰並初始化
genai_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=genai_key)

# 2. 初始化模型：改用完整路徑名稱
# 如果 1.5-flash 還是 404，請嘗試改回 'gemini-pro' (這是最舊但也最穩定的名稱)
try:
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro')

line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')
line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

app = Flask(__name__)

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
        # 產生內容
        response = model.generate_content(user_text)
        
        # 增加一個保險：如果 response 失敗的處理
        if hasattr(response, 'text'):
            reply_text = response.text
        else:
            reply_text = "模型目前沒有回傳文字，請稍後再試。"
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Gemini Error: {error_msg}")
        
        # 如果還是 404，回傳更直覺的檢查清單
        if "404" in error_msg:
            reply_text = "【連線失敗 404】請務必在 Render 執行 'Clear Cache & Deploy'。"
        else:
            reply_text = f"思考發生錯誤：{error_msg[:50]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
