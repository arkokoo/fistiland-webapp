import threading
import time
from os import getenv
from flask import Flask, jsonify, render_template
from pymodbus.client import ModbusTcpClient

app = Flask(__name__)

# Configuration Modbus (à adapter à l'IP de votre OpenPLC)
PLC_IP = getenv("PLC_IP", "plc")
PLC_PORT = int(getenv("PLC_PORT", "502"))

# Mappage des adresses OpenPLC Standard
COILS = {
    "Train_En_Gare": 0,    # %QX0.0
    "Harnais_Baisse": 1,   # %QX0.1
    "Ordre_Lancement": 2,  # %QX0.2
    "Ordre_Freinage": 3,   # %QX0.3
    "Bouton_Start_IHM": 4  # %QX0.4
}

REGISTERS = {
    "Consigne_Vitesse": 0, # %MW0
    "Erreur_Rollback": 1,  # %MW1
    "Force_G": 10          # %MW10
}

# État interne partagé pour l'IHM
attraction_state = {
    "status_automatisme": "Initialisation",
    "train_en_gare": False,
    "harnais_baisse": False,
    "ordre_lancement": False,
    "ordre_freinage": True,
    "consigne_vitesse": 150,
    "erreur_rollback": 0,
    "force_g": 0,
    "wagons_lances": 0
}

def ensure_plc_connection(client):
    """Tente de (re)connecter le client Modbus jusqu'au retour du PLC."""
    while True:
        try:
            attraction_state["status_automatisme"] = "Connexion au PLC..."
            if client.connect():
                attraction_state["status_automatisme"] = "PLC connecté"
                return True
        except Exception as e:
            attraction_state["status_automatisme"] = f"Erreur Connexion PLC: {str(e)}"

        time.sleep(1)

def automation_worker():
    """Boucle principale d'automatisation en arrière-plan"""
    client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
    
    while True:
        try:
            if not client.connected:
                ensure_plc_connection(client)
                continue
            
            # 1. Lecture des états actuels du PLC
            coils_read = client.read_coils(0, count=5)
            regs_read = client.read_holding_registers(0, count=11)
            
            if coils_read.isError() or regs_read.isError():
                attraction_state["status_automatisme"] = "Erreur Communication PLC"
                client.close()
                time.sleep(1)
                continue

            # Mise à jour de l'état pour l'IHM
            attraction_state["train_en_gare"] = coils_read.bits[COILS["Train_En_Gare"]]
            attraction_state["harnais_baisse"] = coils_read.bits[COILS["Harnais_Baisse"]]
            attraction_state["ordre_lancement"] = coils_read.bits[COILS["Ordre_Lancement"]]
            attraction_state["ordre_freinage"] = coils_read.bits[COILS["Ordre_Freinage"]]
            attraction_state["consigne_vitesse"] = regs_read.registers[REGISTERS["Consigne_Vitesse"]]
            attraction_state["erreur_rollback"] = regs_read.registers[REGISTERS["Erreur_Rollback"]]
            attraction_state["force_g"] = regs_read.registers[REGISTERS["Force_G"]]

            # 2. Logique de Sécurité et Cycle Automatique
            if attraction_state["erreur_rollback"] == 9999:
                attraction_state["status_automatisme"] = "URGENCE : CRASH / ROLLBACK DÉTECTÉ !"
                time.sleep(0.5)
                continue

            # ÉTAPE A : Le train arrive ou est en gare, les harnais sont ouverts
            if attraction_state["train_en_gare"] and not attraction_state["harnais_baisse"]:
                attraction_state["status_automatisme"] = "En gare - Embarquement des passagers"
                # Simulation de l'automatisme : On baisse les harnais automatiquement après 5s
                time.sleep(5)
                client.write_coil(COILS["Harnais_Baisse"], True)
                
            # ÉTAPE B : Train prêt et harnais baissés -> On lance !
            elif attraction_state["train_en_gare"] and attraction_state["harnais_baisse"]:
                attraction_state["status_automatisme"] = "Prêt au lancement - Propulsion"
                time.sleep(1)
                # On donne l'ordre au PLC d'appuyer sur Start
                client.write_coil(COILS["Bouton_Start_IHM"], True)
                
                # Attente que le PLC valide le lancement
                time.sleep(0.5) 
                
            # ÉTAPE C : Le train est sur le parcours (quitte la gare)
            elif not attraction_state["train_en_gare"] and attraction_state["harnais_baisse"]:
                attraction_state["status_automatisme"] = "Train en cours de ride sur le circuit"
                
                # Tant que le train est sur la piste, on prépare la gare pour le prochain wagon
                # On réouvre les harnais virtuels de la gare pour accueillir le suivant
                client.write_coil(COILS["Harnais_Baisse"], False)
                
                # Simulation du temps de parcours (ex: 15 secondes de ride)
                # Dans la vraie vie, un capteur physique "Fin_De_Parcours" repasserait Train_En_Gare à TRUE.
                time.sleep(15)
                
                # Le wagon suivant arrive en gare
                client.write_coil(COILS["Train_En_Gare"], True)
                attraction_state["wagons_lances"] += 1

        except Exception as e:
            attraction_state["status_automatisme"] = f"Erreur Système: {str(e)}"
            client.close()
            time.sleep(1)
            continue
            
        time.sleep(0.1) # Cadencement de la logique (100ms)

# Démarrage du thread d'automatisation
threading.Thread(target=automation_worker, daemon=True).start()

# --- ROUTES FLASK ---

@app.route('/')
def index():
    return "Fistiland API"

@app.route('/api/status')
def get_status():
    """Route lue par le Frontend (Read-Only)"""
    return jsonify(attraction_state)

if __name__ == '__main__':
    # Rappel : N'est pas exposé à l'extérieur si Docker gère le port à l'intérieur du réseau
    app.run(host='0.0.0.0', port=5000)