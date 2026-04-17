# 修改 handle_message 中的 try 區塊
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    try:
        # 呼叫 Gemini
        response = model.generate_content(user_text)
        
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "機器人暫時無法回應，請稍後再試。"
            
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Gemini Error: {error_msg}")
        
        # 針對 429 錯誤進行友善回覆
        if "429" in error_msg:
            reply_text = "【系統忙碌中】目前使用人數較多或達到免費額度限制，請稍等一分鐘後再傳訊息給我。"
        elif "quota" in error_msg.lower():
            reply_text = "【額度用盡】API 額度已達上限，請檢查 Google AI Studio 的設定。"
        else:
            reply_text = f"思考發生錯誤：{error_msg[:50]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
