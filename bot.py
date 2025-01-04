from flask import Flask, request, send_from_directory
import requests
import json
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
from fpdf import FPDF

app = Flask(__name__)

# Configuración para el chatbot de Chatbase
CHATBASE_URL = 'https://www.chatbase.co/api/v1/chat'
HEADERS = {
    'Authorization': f'Bearer {os.getenv("API_KEY")}',  # Reemplaza <API-KEY> con tu API Key de Chatbase
    'Content-Type': 'application/json'
}
CHATBOT_ID = os.getenv("CHATBOT_ID")

DEFAULT_MESSAGE = (
    "¡Hola! Bienvenido/a a Defiendetetú, donde te ayudamos a generar tutelas de calidad profesional para proteger tu "
    "derecho a la salud, de manera rápida, sencilla y económica. 😊\n"
    "Por favor, responde SÍ si deseas comenzar, y te guiaremos paso a paso para crear tu tutela."
)

datos_usuario = {}
preguntas = [
    "¿Cuál es tu nombre completo?",
    "¿Cuál es tu número de cédula de ciudadanía y en qué lugar fue expedida?",
    "¿Dónde resides actualmente? (Ciudad o municipio)",
    "¿Cuál es tu correo electrónico en el que puedes recibir notificaciones?",
    "¿Cuál es tu número de celular para contactarte o enviarte notificaciones?",
    "¿Cuál es el nombre de la EPS o IPS en contra de la que estás presentando la tutela?",
    "¿Tienes el correo electrónico de la EPS o IPS para enviar notificaciones? (Si no lo sabes, escribe 'No sé'.)",
    "¿Qué patología o diagnóstico médico tienes?",
    "¿Qué consecuencias o efectos en tu salud has tenido debido a esta patología?",
    "¿Lo que requieres, según el médico tratante, es un medicamento, un tratamiento, una consulta o un insumo?",
    "¿Qué tratamiento médico o insumo específico te recetó tu médico tratante?",
    "¿Qué solicitud hiciste ante la EPS o IPS y por cuál vía la hiciste?",
    "¿En qué fecha realizaste esa solicitud?",
    "¿La EPS o IPS te respondió a esta solicitud? Si es sí, ¿qué fecha recibiste la respuesta y fue positiva o negativa?",
]

datos_usuario_estado = {}

UPLOAD_FOLDER = os.path.join(os.getcwd(), "pdfs")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Crea la carpeta si no existe
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()
    user_number = request.values.get('From')
    resp = MessagingResponse()
    msg = resp.message()

    if user_number not in datos_usuario:
        datos_usuario[user_number] = {}
        datos_usuario_estado[user_number] = 0

    if incoming_msg.lower() in ["hola", "inicio"]:
        datos_usuario_estado[user_number] = 0
        msg.body(DEFAULT_MESSAGE)
        return str(resp)

    if incoming_msg.lower() in ["sí", "si"]:
        msg.body(preguntas[0])
        return str(resp)
    elif incoming_msg.lower() == "no":
        msg.body("Entendido. Si cambias de opinión, no dudes en escribirnos. ¡Estamos aquí para ayudarte!")
        return str(resp)

    estado = datos_usuario_estado[user_number]
    if estado < len(preguntas):
        datos_usuario[user_number][estado] = incoming_msg
        datos_usuario_estado[user_number] += 1

        if datos_usuario_estado[user_number] < len(preguntas):
            siguiente_pregunta = preguntas[datos_usuario_estado[user_number]]
            msg.body(siguiente_pregunta)
        else:
            msg.body("¡Gracias! Hemos recibido toda la información necesaria. Estamos generando tu tutela.")
            tutela_generada = generar_tutela(user_number)
            if tutela_generada:
                pdf_path = crear_pdf(tutela_generada, user_number)
                if pdf_path:
                    # Genera la URL para acceder al archivo
                    pdf_url = f"{request.url_root}pdf/{os.path.basename(pdf_path)}"
                    msg.media(pdf_url)
                    msg.body("Aquí tienes tu tutela en formato PDF.")
                else:
                    msg.body("Hubo un problema al generar el archivo PDF. Por favor, inténtalo nuevamente más tarde.")
            else:
                msg.body("Hubo un problema al generar la tutela. Por favor, inténtalo nuevamente más tarde.")
    else:
        msg.body("Hemos recibido todas tus respuestas. Si deseas realizar algún cambio, escríbenos.")

    return str(resp)

@app.route('/pdf/<filename>', methods=['GET'])
def serve_pdf(filename):
    """Sirve el archivo PDF generado."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def generar_tutela(user_number):
    user_data = datos_usuario[user_number]
    try:
        data = {
            "messages": [
                {"content": "Genera una tutela basada en los siguientes datos:", "role": "assistant"},
                {"content": json.dumps(user_data), "role": "user"}
            ],
            "chatbotId": CHATBOT_ID,
            "stream": False,
            "temperature": 0
        }

        response = requests.post(CHATBASE_URL, headers=HEADERS, data=json.dumps(data))
        if response.status_code == 200:
            json_data = response.json()
            return json_data.get('text', None)
        else:
            print("Error al generar la tutela. Código de estado:", response.status_code)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def crear_pdf(texto, user_number):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for line in texto.split('\n'):
            pdf.cell(0, 10, txt=line, ln=True)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"tutela_{user_number}.pdf")
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)