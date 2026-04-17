import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 使用穩定版 line-bot-sdk v2 導入方式
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數
load_dotenv()

# 2. 配置 Gemini 3.1 (即 2.0 Flash-Lite)
# 注意：API 正式識別碼為以下字串，請確保 google-generativeai 套件為最新版
MODEL_ID = 'gemini-2.0-flash-lite-preview-02-05' 

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
# 設定安全設定，避免模型因過度檢查而拒絕回答
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
model = genai.GenerativeModel(model_name=MODEL_ID, safety_settings=safety_settings)

# 3. 初始化 LINE API (從環境變數讀取)
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')

if not line_token or not line_secret:
    raise ValueError("請在環境變數中設定 LINE_TOKEN 與 LINE_SECRET")

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
        # 呼叫 Gemini 生成回應
        response = model.generate_content(user_text)
        
        # 檢查回應是否成功生成文字
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "核心模型未回傳文字，可能是內容觸發了安全過濾。"
            
    except Exception as e:
        app.logger.error(f"Gemini 發生錯誤: {e}")
        # 如果模型 ID 報錯，會顯示在這邊
        reply_text = f"機器人思考發生錯誤，原因：{str(e)[:50]}"

    # 回覆訊息給 LINE 使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # Render 環境必備：讀取動態 PORT
    port = int(os.environ.get('PORT', 10000))
    # host 必須為 0.0.0.0
    app.run(host='0.0.0.0', port=port)
