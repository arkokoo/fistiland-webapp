import time
import argparse
import logging
from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Fistiland_Actuators")

def run_actuator(actuator_type, target_host, target_port, default_speed=None):
    client = ModbusTcpClient(target_host, port=target_port)
    
    while not client.connect():
        logger.warning(f"En attente du PLC ({target_host}:{target_port})...")
        time.sleep(2)
        
    logger.info(f"Connecté ! Actionneur en écoute : {actuator_type}")

    # Initialisation de la vitesse par défaut dans le PLC si c'est le VFD
    if actuator_type == "vfd_launch" and default_speed:
        client.write_register(0, int(default_speed)) # Holding Register 0 = Vitesse cible
        logger.info(f"VFD initialisé à la vitesse nominale : {default_speed} km/h")

    try:
        while True:
            if actuator_type == "vfd_launch":
                # 1. On lit l'ordre de lancement (Coil 2)
                launch_cmd = client.read_coils(address=2, count=1)
                
                # 2. On lit la consigne de vitesse envoyée par le PLC/IHM (Holding Register 0)
                speed_reg = client.read_holding_registers(address=0, count=1)

                if launch_cmd.isError() or speed_reg.isError():
                    logger.error("Erreur de lecture Modbus.")
                    time.sleep(1)
                    continue

                is_launching = launch_cmd.bits[0]
                target_speed = speed_reg.registers[0]

                if target_speed < 80:
                    logger.critical("!!! ALARME FATALE !!!")
                    logger.critical(f"Vitesse trop faible ({target_speed} km/h). Énergie cinétique insuffisante.")
                    logger.critical("ROLLBACK EN COURS - IMPACT IMMINENT DANS LA GARE - APPEL DU MÉDECIN LÉGISTE")
                    client.write_register(1, 9999)
                    client.write_coil(2, False)
                    time.sleep(5)
                    continue

                if is_launching:
                    logger.info(f"ORDRE DE LANCEMENT REÇU ! Vitesse cible lue : {target_speed} km/h")

                    logger.info("Lancement réussi. Les passagers crient de terreur.")
                    client.write_register(1, 0) # Remise à zéro de l'erreur
                    time.sleep(3) # Temps du parcours
                    
                    # On remet le Coil de lancement à False pour attendre le prochain train
                    client.write_coil(2, False) 
                
                time.sleep(0.5)

            elif actuator_type == "dodgy_brakes":
                # Lit l'état des freins (Coil 3)
                brakes_cmd = client.read_coils(address=3, count=1)
                if not brakes_cmd.isError():
                    is_brakes_closed = brakes_cmd.bits[0]
                    state = "FERMÉS (Froissement de tôle)" if is_brakes_closed else "OUVERTS (Roue libre totale)"
                    logger.info(f"État des freins : {state}")
                time.sleep(1.5)

    except Exception as e:
        logger.error(f"Erreur de communication : {e}")
    finally:
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=['vfd_launch', 'dodgy_brakes'])
    parser.add_argument("--target", required=True, help="Host et port du PLC")
    parser.add_argument("--default_speed", type=int, help="Vitesse nominale pour la catapulte")
    args = parser.parse_args()

    host, port = args.target.split(':')
    run_actuator(args.type, host, int(port), args.default_speed)