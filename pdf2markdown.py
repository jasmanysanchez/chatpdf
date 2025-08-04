import os
from pdf2image import convert_from_path
import pytesseract
from pathlib import Path
import re
import cv2
import numpy as np
from PIL import Image
import logging
from typing import List, Tuple, Dict
import fitz  # PyMuPDF
import hashlib

class PDFToMarkdownConverter:
    def __init__(self, language: str = 'spa+eng'):
        """
        Inicializa el convertidor con configuraciones específicas.

        Args:
            language (str): Idiomas para OCR (default: 'spa+eng')
        """
        self.language = language
        self.setup_logging()
        self.image_counter = 0
        self.setup_tesseract_config()

    def setup_logging(self):
        """Configura el sistema de logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_tesseract_config(self):
        """Configura los parámetros de Tesseract OCR."""
        self.tesseract_config = r'--oem 3 --psm 6'

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocesa la imagen para mejorar el OCR.

        Args:
            image (np.ndarray): Imagen de entrada

        Returns:
            np.ndarray: Imagen procesada
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Binarización adaptativa
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Reducción de ruido
        denoised = cv2.fastNlMeansDenoising(binary)

        return denoised

    def detect_headers(self, text: str) -> str:
        """
        Detecta y formatea encabezados en el texto.

        Args:
            text (str): Texto a procesar

        Returns:
            str: Texto con encabezados formateados
        """
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detectar encabezados por patrones
            if line.isupper() and len(line) > 3:
                formatted_lines.append(f"\n### {line.title()}\n")
            elif re.match(r'^(?:CAPÍTULO|Capítulo|TÍTULO|Título|SECCIÓN|Sección)\s+\w+', line):
                formatted_lines.append(f"\n## {line}\n")
            elif re.match(r'^[\d\.]+\s+[A-Z]', line):
                formatted_lines.append(f"\n### {line}\n")
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def extract_images(self, pdf_path: str, output_folder: str) -> List[str]:
        """
        Extrae imágenes del PDF y las guarda.

        Args:
            pdf_path (str): Ruta del PDF
            output_folder (str): Carpeta de salida

        Returns:
            List[str]: Lista de rutas de imágenes guardadas
        """
        image_paths = []
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)

            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Generar nombre único para la imagen
                image_hash = hashlib.md5(image_bytes).hexdigest()[:10]
                image_filename = f"image_{page_num + 1}_{image_hash}.{base_image['ext']}"
                image_path = os.path.join(output_folder, image_filename)

                with open(image_path, "wb") as image_file:
                    image_file.write(image_bytes)
                image_paths.append(image_path)

        return image_paths

    def detect_lists(self, text: str) -> str:
        """
        Detecta y formatea listas en el texto.

        Args:
            text (str): Texto a procesar

        Returns:
            str: Texto con listas formateadas
        """
        lines = text.split('\n')
        formatted_lines = []
        in_list = False

        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    formatted_lines.append('')
                    in_list = False
                continue

            # Detectar elementos de lista
            if re.match(r'^[\•\-\*]\s', line) or re.match(r'^\d+[\.\)]\s', line):
                if not in_list:
                    formatted_lines.append('')
                    in_list = True
                formatted_lines.append(line)
            else:
                if in_list:
                    formatted_lines.append('')
                    in_list = False
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def convert_pdf_to_markdown(self, pdf_path: str, output_path: str, images_folder: str = None) -> None:
        """
        Convierte un PDF a Markdown.

        Args:
            pdf_path (str): Ruta del archivo PDF
            output_path (str): Ruta del archivo Markdown de salida
            images_folder (str, optional): Carpeta para guardar imágenes
        """
        try:
            self.logger.info(f"Iniciando conversión de {pdf_path}")

            # Crear carpeta para imágenes si no existe
            if images_folder:
                os.makedirs(images_folder, exist_ok=True)
                image_paths = self.extract_images(pdf_path, images_folder)

            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path, dpi=300)
            markdown_content = []

            for i, image in enumerate(images, 1):
                self.logger.info(f"Procesando página {i}/{len(images)}")

                # Convertir imagen PIL a array numpy
                image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # Preprocesar imagen
                processed_image = self.preprocess_image(image_np)

                # Extraer texto con OCR
                text = pytesseract.image_to_string(
                    processed_image,
                    lang=self.language,
                    config=self.tesseract_config
                )

                # Procesar el texto
                text = self.detect_headers(text)
                text = self.detect_lists(text)

                markdown_content.append(text)

            # Unir todo el contenido
            final_markdown = "\n\n".join(markdown_content)

            # Guardar archivo Markdown
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)

            self.logger.info(f"Conversión completada. Archivo guardado en {output_path}")

        except Exception as e:
            self.logger.error(f"Error durante la conversión: {str(e)}")
            raise

def main():
    # Ejemplo de uso
    converter = PDFToMarkdownConverter()

    pdf_path = "documento.pdf"
    output_path = "documento_convertido.md"
    images_folder = "imagenes_extraidas"

    converter.convert_pdf_to_markdown(
        pdf_path=pdf_path,
        output_path=output_path,
        images_folder=images_folder
    )

if __name__ == "__main__":
    main()

# Created/Modified files during execution:
print("documento_convertido.md")
print("imagenes_extraidas/")