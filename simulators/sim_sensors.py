import time
import argparse
import random
import logging
from pymodbus.client import ModbusTcpClient

# Configuration du logging pour voir ce qui se passe dans Docker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Fistiland_Sensors")

def run_sensor(sensor_type, target_host, target_port):
    client = ModbusTcpClient(target_host, port=target_port)
    
    # Tentative de connexion en boucle (attend que le PLC soit prêt)
    while not client.connect():
        logger.warning(f"Impossible de se connecter au PLC ({target_host}:{target_port}). Nouvelle tentative...")
        time.sleep(2)
        
    logger.info(f"Connecté au PLC ! Démarrage du capteur : {sensor_type}")

    try:
        while True:
            if sensor_type == "position":
                # Simule un train qui passe sur un capteur (Coil 0) de façon aléatoire
                # À Fistiland, les capteurs clignotent un peu quand ils veulent.
                is_train_present = random.choice([True, False, False, False])
                client.write_coil(0, is_train_present)
                logger.info(f"Capteur de position (Coil 0) : {is_train_present}")
                time.sleep(2)

            elif sensor_type == "harness_bypassed":
                # La fameuse sécurité Fistiland : on force le Coil 1 à TRUE pour gagner du temps
                client.write_coil(1, True)
                logger.info("Capteur de harnais (Coil 1) : TRUE (Sécurité shuntée par la direction)")
                time.sleep(5)

            elif sensor_type == "g_force":
                # Écrit une valeur de Force G absurde dans le Holding Register 10
                # Valeur en dixièmes de G (ex: 45 = 4.5 G, 80 = 8.0 G -> mortel)
                g_force = random.randint(30, 95)
                client.write_register(10, g_force)
                logger.info(f"Capteur Force G (Register 10) : {g_force / 10.0} G encaissés par les passagers.")
                time.sleep(1)

    except Exception as e:
        logger.error(f"Erreur de communication : {e}")
    finally:
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=['position', 'harness_bypassed', 'g_force'])
    parser.add_argument("--target", required=True, help="Host et port du PLC, ex: plc:502")
    args = parser.parse_args()

    host, port = args.target.split(':')
    run_sensor(args.type, host, int(port))