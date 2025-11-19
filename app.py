import os
import base64
import json
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("EDUCORE_GH_TOKEN")
REPO_OWNER   = os.getenv("EDUCORE_REPO_OWNER")
REPO_NAME    = os.getenv("EDUCORE_REPO_NAME")
FILE_PATH    = "licencias.json"

GH_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

def gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def obtener_licencias():
    r = requests.get(GH_API, headers=gh_headers())
    print("Respuesta de GitHub:", r.status_code)
    if r.status_code != 200:
        return None, None, "error_lectura"
    try:
        data = r.json()
        contenido_base64 = data["content"].replace("\n", "")
        contenido = base64.b64decode(contenido_base64).decode("utf-8")
        print("Contenido decodificado:\n", contenido)
        licencias = json.loads(contenido)
        return licencias, data["sha"], None
    except Exception as e:
        print("Error al decodificar JSON:", e)
        return None, None, "error_lectura"

def actualizar_licencias(licencias, sha):
    nuevo_contenido = json.dumps(licencias, indent=2)
    b64 = base64.b64encode(nuevo_contenido.encode("utf-8")).decode("utf-8")
    payload = {
        "message": "Activación de clave",
        "content": b64,
        "sha": sha
    }
    r = requests.put(GH_API, headers=gh_headers(), json=payload)
    return r.status_code in (200, 201)

@app.route("/validate", methods=["POST"])
def validar_clave():
    data = request.get_json()
    clave = data.get("clave", "").strip()

    if not clave:
        return jsonify({ "valida": False, "motivo": "clave_vacia" }), 400

    licencias, sha, error = obtener_licencias()
    if error:
        return jsonify({ "valida": False, "motivo": error }), 502

    entrada = licencias.get(clave)
    if not entrada:
        return jsonify({ "valida": False, "motivo": "inexistente" }), 200

    if not entrada.get("disponible", False):
        return jsonify({ "valida": False, "motivo": "ya_usada" }), 200

    entrada["disponible"] = False
    licencias[clave] = entrada

    if not actualizar_licencias(licencias, sha):
        return jsonify({ "valida": False, "motivo": "error_actualizacion" }), 502

    return jsonify({ "valida": True, "motivo": "activada" }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)