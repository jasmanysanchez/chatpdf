from flask import Flask, request, jsonify
import os
import json

from google.generativeai.types.safety_types import SafetySettingOptions

from chatpdf import get_pdf_text, get_text_chunks, get_vectorstore, get_conversation_chain, handle_userinput
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
import base64

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/chatpdf", methods=['POST'])
def chatpdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        filename = os.path.join(BASE_DIR, app.config['UPLOAD_FOLDER'], f'{datetime.now().strftime("%d%m%Y%H%M%S%f")}_{file.filename}')
        file.save(filename)
        file.close()
        prompt = request.form['prompt']
        language = request.form.get('language') or 'es'

        # model = 'gemini-1.5-pro-002'
        # model = 'gemini-1.5-pro-latest'
        # model = 'gemini-2.0-flash-thinking-exp-1219'
        # model = 'gemma-2-27b-it'
        model = 'gemini-1.5-flash-8b'

        model = genai.GenerativeModel(model, safety_settings=SafetySettingOptions(temperature=0))

        with open(filename, "rb") as doc_file:
            doc_data = base64.standard_b64encode(doc_file.read()).decode("utf-8")

        response = model.generate_content([{'mime_type': 'application/pdf', 'data': doc_data}, prompt])

        # raw_text = get_pdf_text([filename])
        # text_chunks = get_text_chunks(raw_text)
        # vectorstore = get_vectorstore(text_chunks)
        # conversation = get_conversation_chain(vectorstore, language)
        # response = handle_userinput(prompt, conversation)
        answer = response.text
        answertext = answer
        if isinstance(answer, str):
            answer = answer.replace('\n', '')
            if answer.startswith('```json'):
                answer = answer.replace('```json', '', 1)
                answer = answer.replace('```', '', 1)
            try:
                d = json.loads(answer)
                os.path.exists(filename) and os.remove(filename)
                return jsonify(d)
            except Exception as ex:
                return jsonify({"answer": answertext})
        if isinstance(answer, list) or isinstance(answer, tuple):
            for i, x in enumerate(answer or []):
                text = x['text']
                text = text.replace('\n', '')
                if text.startswith('```json'):
                    text = text.replace('```json', '', 1)
                    text = text.replace('```', '', 1)
                try:
                    d = json.loads(text)
                    os.path.exists(filename) and os.remove(filename)
                    return jsonify(d)
                except Exception as ex:
                    return jsonify({"answer": answertext})
        return jsonify({'error': 'No se pudo leer el pdf'}), 400
    except Exception as ex:
        return jsonify({'error': str(ex)}), 400

if __name__ == '__main__':
    app.run()