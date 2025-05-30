from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os
import json
import mimetypes
from google.generativeai.types import GenerationConfigType
from chatpdf import get_pdf_text, get_text_chunks, get_vectorstore, get_conversation_chain, handle_userinput
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
import base64
import re
import PyPDF2

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/chatpdf", methods=['POST'])
def chatpdf():
    try:
        load_dotenv()
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

        with open(filename, "rb") as doc_file:
            doc_data = base64.standard_b64encode(doc_file.read()).decode("utf-8")
            reader = PyPDF2.PdfReader(doc_file)
            cantidad_paginas = len(reader.pages)

        # model = 'gemini-1.5-pro-002'
        # model = 'gemini-1.5-pro-latest'
        # model = 'gemini-2.0-flash-thinking-exp-1219'
        # model = 'gemma-2-27b-it'
        model = 'gemini-2.0-flash'
        # if cantidad_paginas <= 2:
        #     model = 'gemini-1.5-flash-8b'
        # elif cantidad_paginas > 3 and cantidad_paginas <= 5:
        #     model = 'gemini-1.5-flash'

        # genai.configure(api_key='')
        model = genai.GenerativeModel(model, generation_config=genai.GenerationConfig(temperature=0))

        mime_type, encoding = mimetypes.guess_type(filename)
        response = model.generate_content([{'mime_type': mime_type, 'data': doc_data}, prompt])

        # raw_text = get_pdf_text([filename])
        # text_chunks = get_text_chunks(raw_text)
        # vectorstore = get_vectorstore(text_chunks)
        # conversation = get_conversation_chain(vectorstore, language)
        # response = handle_userinput(prompt, conversation)
        answer = response.text
        answertext = answer.replace('\n', '')
        patron = r'\{.*?\}'
        if isinstance(answer, str):

            busqueda = re.search(patron, answertext, re.DOTALL)
            resultado = answertext
            if busqueda:
                resultado = busqueda.group()
            # answer = answer.replace('\n', '')
            # if answer.startswith('```json'):
            #     answer = answer.replace('```json', '', 1)
            #     answer = answer.replace('```', '', 1)
            try:
                d = json.loads(resultado)
                os.path.exists(filename) and os.remove(filename)
                return jsonify(d)
            except Exception as ex:
                return jsonify({"answer": answertext})
        if isinstance(answer, list) or isinstance(answer, tuple):
            for i, x in enumerate(answer or []):
                text = x['text']
                busqueda = re.search(patron, text, re.DOTALL)
                resultado = text
                if busqueda:
                    resultado = busqueda.group()
                # text = text.replace('\n', '')
                # if text.startswith('```json'):
                #     text = text.replace('```json', '', 1)
                #     text = text.replace('```', '', 1)
                try:
                    d = json.loads(resultado)
                    os.path.exists(filename) and os.remove(filename)
                    return jsonify(d)
                except Exception as ex:
                    return jsonify({"answer": answertext})
        return jsonify({'error': 'No se pudo leer el pdf'}), 400
    except Exception as ex:
        return jsonify({'error': str(ex)}), 400

if __name__ == '__main__':
    app.run()