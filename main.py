import json
import subprocess


def ejecutar_script():
    prompt = 'Using the following JSON schema, Please analise the pdf content with the keys and values. '
    prompt += 'Return: dict {"apellidos_completos": str, "nombres_completos": str, "placa": str, "marca": str, '
    prompt += '"modelo": str, "anio": int, "precio_vehiculo": float, "precio_vehiculo_adicional": float, "precio_sin_impuestos": float, "impuestos": float, "descuento": float, "prima_total": float}'
    completed_process = subprocess.run(
        [
            'D:\\WEB\\ENTORNOS_VIRTUALES\\venv_chatpdf\\Scripts\\python.exe', 'chatpdf.py', '--path_file', 'D:\\WEB\\chatpdf\\cotizacion.pdf',
            '--prompt', prompt
        ], timeout=10000, text=True, capture_output=True
    )
    stdout = completed_process.stdout
    for linea in stdout.strip().split('\n'):
        if linea.strip().startswith('{'):
            try:
                return json.loads(linea)
            except json.JSONDecodeError:
                continue
    return None


# Uso
if __name__ == '__main__':
    resultado = ejecutar_script()
    print(resultado)
