import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 初始化與環境設定
load_dotenv()
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# 2. 初始化 Gemini (帶有自動偵測邏輯)
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def initialize_model():
    try:
        # 列出所有可用的模型
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        logging.info(f"可用模型清單: {available}")
        
        # 依照優先順序尋找模型
        # 3.1 目前不存在，我們尋找 2.0-flash-lite 或 1.5-flash
        target_models = [
            'models/gemini-2.0-flash-lite-preview-02-05',
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash',
            'models/gemini-pro'
        ]
        
        for target in target_models:
            if target in available:
                logging.info(f"成功選定模型: {target}")
                return genai.GenerativeModel(target)
        
        # 如果都沒找到，就用最通用的
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logging.error(f"初始化模型失敗: {e}")
        return genai.GenerativeModel('gemini-1.5-flash')

model = initialize_model()

# 3. 初始化 LINE API
line_bot_api = LineBotApi(os.getenv('LINE_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_SECRET'))

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
            reply_text = "模型未回傳文字，可能是觸發了安全過濾。"
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Gemini Error: {error_msg}")
        
        # 針對 404 顯示更細節的資訊
        if "404" in error_msg:
            reply_text = f"連線失敗(404)：API不支援此模型名稱。請檢查 Google AI Studio 是否有權限。"
        elif "429" in error_msg:
            reply_text = "額度用盡(429)：請稍等一分鐘後再試。"
        else:
            reply_text = f"思考錯誤：{error_msg[:100]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
