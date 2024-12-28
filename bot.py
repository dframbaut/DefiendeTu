from flask import Flask, request
import requests
import json
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Configuración para el chatbot de Chatbase
CHATBASE_URL = 'https://www.chatbase.co/api/v1/chat'
HEADERS = {
    'Authorization': 'Bearer c70ef81a-5160-482d-81f4-20443332b562',  # Reemplaza <API-KEY> con tu API Key de Chatbase
    'Content-Type': 'application/json'
}
CHATBOT_ID = 'hWky5EsMRfHuh3fXJEcad'

# Mensaje predeterminado
DEFAULT_MESSAGE = (
    "¡Hola! Bienvenido/a a Defiendetetú, donde te ayudamos a generar tutelas de calidad profesional para proteger tu "
    "derecho a la salud, de manera rápida, sencilla y económica. 😊\n"
    "Por favor, responde SÍ si deseas comenzar, y te guiaremos paso a paso para crear tu tutela."
)

# Diccionario para almacenar los datos del usuario
datos_usuario = {}

# Lista de preguntas y campos
preguntas = [
    "¿Cuál es tu nombre completo?",  # Campo 1
    "¿Cuál es tu número de cédula de ciudadanía y en qué lugar fue expedida?",  # Campo 2
    "¿Dónde resides actualmente? (Ciudad o municipio)",  # Campo 3
    "¿Cuál es tu correo electrónico en el que puedes recibir notificaciones?",  # Campo 4
    "¿Cuál es tu número de celular para contactarte o enviarte notificaciones?",  # Campo 5
    "¿Cuál es el nombre de la EPS o IPS en contra de la que estás presentando la tutela?",  # Campo 6
    "¿Tienes el correo electrónico de la EPS o IPS para enviar notificaciones? (Si no lo sabes, escribe 'No sé'.)",  # Campo 7
    "¿Qué patología o diagnóstico médico tienes?",  # Campo 8
    "¿Qué consecuencias o efectos en tu salud has tenido debido a esta patología?",  # Campo 9
    "¿Lo que requieres, según el médico tratante, es un medicamento, un tratamiento, una consulta o un insumo?",  # Campo 10
    "¿Qué tratamiento médico o insumo específico te recetó tu médico tratante?",  # Campo 11
    "¿Qué solicitud hiciste ante la EPS o IPS y por cuál vía la hiciste?",  # Campo 12
    "¿En qué fecha realizaste esa solicitud?",  # Campo 13
    "¿La EPS o IPS te respondió a esta solicitud? Si es sí, ¿qué fecha recibiste la respuesta y fue positiva o negativa?",  # Campo 14
]

# Estado para rastrear la pregunta actual
datos_usuario_estado = {}

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()  # Captura el mensaje recibido
    user_number = request.values.get('From')  # Identifica al usuario
    resp = MessagingResponse()  # Inicia una respuesta Twilio
    msg = resp.message()  # Prepara un mensaje de respuesta

    if user_number not in datos_usuario:
        datos_usuario[user_number] = {}
        datos_usuario_estado[user_number] = 0

    # Si es el mensaje inicial
    if incoming_msg.lower() in ["hola", "inicio"]:
        datos_usuario_estado[user_number] = 0
        msg.body(DEFAULT_MESSAGE)
        return str(resp)

    # Si el usuario responde "SÍ" o "NO"
    if incoming_msg.lower() in ["sí", "si"]:
        msg.body(preguntas[0])  # Primera pregunta
        return str(resp)
    elif incoming_msg.lower() == "no":
        msg.body("Entendido. Si cambias de opinión, no dudes en escribirnos. ¡Estamos aquí para ayudarte!")
        return str(resp)

    # Procesar la respuesta del usuario
    estado = datos_usuario_estado[user_number]
    if estado < len(preguntas):
        # Almacenar la respuesta en el campo correspondiente
        datos_usuario[user_number][estado] = incoming_msg
        datos_usuario_estado[user_number] += 1

        # Verificar si hay más preguntas
        if datos_usuario_estado[user_number] < len(preguntas):
            siguiente_pregunta = preguntas[datos_usuario_estado[user_number]]
            msg.body(siguiente_pregunta)
        else:
            msg.body("¡Gracias! Hemos recibido toda la información necesaria. Estamos generando tu tutela.")
            tutela_generada = generar_tutela(user_number)  # Llama a la función para generar la tutela
            if tutela_generada:
                print("Entro AQUI!!")
                # Dividir la tutela si es demasiado larga
                fragmentos = dividir_mensaje(tutela_generada)
                for fragmento in fragmentos:
                    msg.body(fragmento)
                msg.body("Si necesitas algo más, no dudes en escribirnos.")
            else:
                msg.body("Hubo un problema al generar la tutela. Por favor, inténtalo nuevamente más tarde.")
    else:
        msg.body("Hemos recibido todas tus respuestas. Si deseas realizar algún cambio, escríbenos.")

    return str(resp)

def generar_tutela(user_number):
    """Función para generar la tutela con la información del usuario."""
    user_data = datos_usuario[user_number]

    # Aquí puedes realizar la lógica para enviar los datos a la IA o procesarlos
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
            return json_data.get('text', None)  # Devuelve la tutela generada por la IA
        else:
            print("Error al generar la tutela. Código de estado:", response.status_code)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def dividir_mensaje(mensaje, max_len=1600):
    """Divide un mensaje largo en fragmentos más pequeños."""
    return [mensaje[i:i+max_len] for i in range(0, len(mensaje), max_len)]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)