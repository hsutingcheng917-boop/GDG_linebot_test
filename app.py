import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, abort

# 統一使用 line-bot-sdk v2 穩定版，避免與 v3 混淆造成運作失敗
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 載入環境變數 (請確保目錄下有 .env 檔案)
load_dotenv()

# 2. 取得設定資訊
# 建議將金鑰都移入 .env 以策安全
genai_key = os.getenv('GOOGLE_API_KEY') or "AIzaSyBcSLZ73afUx3WjhaQZrhCW6GEerXgJJqc" # 暫時保留你原本的金鑰，但建議移至 .env
line_token = os.getenv('LINE_TOKEN')
line_secret = os.getenv('LINE_SECRET')

# 3. 初始化 Gemini 模型
genai.configure(api_key=genai_key)
# 修正：模型名稱必須是小寫且格式正確，例如 'gemini-1.5-flash'
# 目前最推薦開發者使用的是 1.5 系列
model = genai.GenerativeModel('gemini-1.5-flash') 

# 4. 初始化 LINE API
if not line_token or not line_secret:
    raise ValueError("請檢查 .env 檔案中的 LINE_TOKEN 與 LINE_SECRET 是否設定正確")

line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

# 5. 建立 Flask 應用
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭
    signature = request.headers.get('X-Line-Signature')
    # 取得請求內容
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("LINE 簽名驗證失敗，請檢查 Channel Secret 是否正確")
        abort(400)
    except Exception as e:
        app.logger.error(f"Callback 發生錯誤: {e}")
        abort(500)
        
    return 'OK'

# 6. 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    app.logger.info(f"收到使用者訊息: {user_text}")

    try:
        # 向 Gemini 發送請求
        response = model.generate_content(user_text)
        
        # 檢查回應是否包含有效的文字內容
        if response and response.text:
            reply_text = response.text
        else:
            # 如果被安全過濾器擋掉，response.text 會是空的
            reply_text = "抱歉，這方面的內容我無法提供回應。"
            
    except Exception as e:
        app.logger.error(f"Gemini 運作錯誤: {e}")
        # 這就是你提到的「思考時發生錯誤」的來源，現在我們捕捉它並回報
        reply_text = f"機器人思考時發生錯誤：{str(e)[:50]}..." 

    # 執行回覆
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        app.logger.error(f"LINE 回傳訊息失敗: {e}")

# 7. 啟動程式
if __name__ == "__main__":
    # 使用環境變數中的 PORT，這對部署到雲端平台（如 Render）很重要
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
