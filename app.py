import google.generativeai as genai

# ... (前面的導入和 LINE 設定保持不變) ...

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# 終極暴力相容模式
def get_working_model():
    # 按照順序測試，只要有一個不報 404 就用它
    test_ids = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-pro',
        'models/gemini-1.5-flash',
        'models/gemini-pro'
    ]
    
    for model_id in test_ids:
        try:
            m = genai.GenerativeModel(model_id)
            # 嘗試發送一個極短的測試，確認模型是否存在
            m.generate_content("ping", generation_config={"max_output_tokens": 1})
            logging.info(f"成功連線！使用的模型 ID 是: {model_id}")
            return m
        except Exception as e:
            logging.warning(f"模型 {model_id} 測試失敗: {e}")
            continue
            
    # 如果全部失敗，回傳最後一個嘗試
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_working_model()

# ... (後面的 handler.add 保持不變) ...
