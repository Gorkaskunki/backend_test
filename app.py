from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# Configuración de Flask
app = Flask(__name__)

# Configuración de credenciales y acceso a Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
client = gspread.authorize(CREDS)

# Conectar a la hoja "Preguntas" para obtener los datos
try:
    sheet = client.open("BASE DE DATOS").worksheet("Preguntas")  # Cambia "Preguntas" si la pestaña tiene otro nombre
    datos = sheet.get_all_records()  # Obtener todas las preguntas
    print("Conexión exitosa. Datos de la hoja:")
    print(datos)
except Exception as e:
    print(f"Error al conectar con Google Sheets: {e}")

# Ruta para la página de inicio
@app.route("/")
def home():
    return "¡Hola! Tu servidor Flask está funcionando."

# Ruta para obtener las preguntas
@app.route("/preguntas", methods=["GET"])
def obtener_preguntas():
    try:
        return jsonify({"status": "success", "datos": datos}), 200
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# Ruta para registrar respuestas en la hoja "Respuestas"
@app.route("/responder", methods=["POST"])
def registrar_respuesta():
    try:
        data = request.json
        usuario = data.get("usuario")
        pregunta = data.get("id_pregunta")
        respuesta = data.get("respuesta")
        peso = data.get("peso", "")
        subtipo_actual = data.get("subtipo_actual", "")  # Subtipo más probable intermedio
        test_id = data.get("test_id", f"Test_{int(datetime.now().timestamp())}")  # ID único del test

        # Generar el timestamp actual
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        respuestas_sheet = client.open("BASE DE DATOS").worksheet("Respuestas")

        # Registrar la respuesta en la hoja
        respuestas_sheet.append_row([
            test_id,       # Test ID
            usuario,       # Usuario
            pregunta,      # Pregunta contestada
            respuesta,     # Respuesta del usuario
            peso,          # Peso asociado
            subtipo_actual,  # Subtipo más probable hasta el momento
            timestamp      # Timestamp
        ])

        return jsonify({"status": "success", "message": "Respuesta registrada correctamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Ruta para registrar usuarios en la hoja "Usuarios"
@app.route("/registrar_usuario", methods=["POST"])
def registrar_usuario():
    try:
        data = request.json
        nombre = data.get("nombre")
        correo = data.get("correo", "")
        fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generar un ID único
        id_usuario = f"Usuario_{int(datetime.now().timestamp())}"

        usuarios_sheet = client.open("BASE DE DATOS").worksheet("Usuarios")

        usuarios_sheet.append_row([
            id_usuario,          # Name
            f"{nombre}/{correo}",  # Nombre/Correo Electrónico
            "En curso",         # Estado del Test
            fecha_inicio,       # Fecha de Inicio
            "",                 # Última Pregunta Contestada
            "",                 # Respuestas
            "",                 # Resultados
            ""                  # Preguntas
        ])

        return jsonify({"status": "success", "message": f"Usuario {id_usuario} registrado correctamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Ruta para actualizar el progreso del usuario
@app.route("/actualizar_usuario", methods=["POST"])
def actualizar_usuario():
    try:
        data = request.json
        usuario = data.get("usuario")
        ultima_pregunta = data.get("ultima_pregunta", "")
        subtipo_actual = data.get("subtipo_actual", "")
        estado_test = data.get("estado_test", "En curso")

        usuarios_sheet = client.open("BASE DE DATOS").worksheet("Usuarios")
        registros = usuarios_sheet.get_all_records()
        encontrado = False
        for i, registro in enumerate(registros, start=2):  # La fila 1 es encabezado, comenzamos en 2
            if registro["Nombre/Correo Electrónico"] == usuario:
                usuarios_sheet.update(f"D{i}", ultima_pregunta)  # Última pregunta contestada
                usuarios_sheet.update(f"E{i}", subtipo_actual)   # Subtipo actual
                usuarios_sheet.update(f"F{i}", estado_test)      # Estado del test
                encontrado = True
                break

        if not encontrado:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        return jsonify({"status": "success", "message": "Usuario actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Ruta para calcular resultados
@app.route("/calcular_resultados", methods=["POST"])
def calcular_resultados():
    try:
        data = request.json
        respuestas = data.get("respuestas")  # Respuestas con subtipos y pesos
        preguntas_disponibles = data.get("preguntas_disponibles")  # Preguntas restantes

        pesos_acumulados = {}
        for respuesta in respuestas:
            intensidad = int(respuesta["respuesta"])
            for subtipo in respuesta["subtipos"]:
                if subtipo not in pesos_acumulados:
                    pesos_acumulados[subtipo] = 0
                pesos_acumulados[subtipo] += respuesta["peso"] * (intensidad / 5)

        subtipos_ordenados = sorted(pesos_acumulados.items(), key=lambda x: x[1], reverse=True)
        subtipo_principal = subtipos_ordenados[0][0] if subtipos_ordenados else None

        subtipo_sheet = client.open("BASE DE DATOS").worksheet("Subtipo")
        subtipo_data = subtipo_sheet.get_all_records()

        descripciones_subtipos = {
            row["Type Name"]: {
                "descripcion": row.get("Integracion ia", "No disponible."),
                "rasgos_clave": row.get("Rasgos Clave", "No disponible."),
                "virtudes": row.get("Virtudes", "No disponible."),
                "mecanismos_defensa": row.get("Mecanismo de defensa", "No disponible."),
                "motivacion_nuclear": row.get("Motivación", "No disponible."),
                "palabra_clave": row.get("Palabra Clave", "No disponible."),
            }
            for row in subtipo_data
        }

        datos_subtipo_principal = descripciones_subtipos.get(subtipo_principal, {
            "descripcion": "No disponible.",
            "rasgos_clave": "No disponible.",
            "virtudes": "No disponible.",
            "mecanismos_defensa": "No disponible.",
            "motivacion_nuclear": "No disponible.",
            "palabra_clave": "No disponible.",
        })

        preguntas_influyentes = []
        for respuesta in respuestas:
            if subtipo_principal in respuesta["subtipos"]:
                preguntas_influyentes.append({
                    "pregunta": respuesta["pregunta"],
                    "peso": respuesta["peso"],
                    "respuesta": respuesta["respuesta"]
                })

        return jsonify({
            "status": "success",
            "resultado": subtipo_principal,
            "descripcion": datos_subtipo_principal["descripcion"],
            "rasgos_clave": datos_subtipo_principal["rasgos_clave"],
            "virtudes": datos_subtipo_principal["virtudes"],
            "mecanismos_defensa": datos_subtipo_principal["mecanismos_defensa"],
            "motivacion_nuclear": datos_subtipo_principal["motivacion_nuclear"],
            "palabra_clave": datos_subtipo_principal["palabra_clave"],
            "pesos_acumulados": pesos_acumulados,
            "ranking": subtipos_ordenados,
            "preguntas_influyentes": preguntas_influyentes
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)


