#!/usr/bin/env python3

"""Remet Fistiland à l'état nominal.

Le script remet les registres/coil Modbus principaux à leurs valeurs de départ.
Par défaut, il redémarre aussi les services applicatifs pour réinitialiser l'état
mémoire du backend, comme lors du nettoyage manuel.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

from pymodbus.client import ModbusTcpClient


@dataclass(frozen=True)
class ResetConfig:
    host: str = "127.0.0.1"
    port: int = 502
    unit_id: int = 1
    consigne_vitesse: int = 150
    erreur_rollback: int = 0
    force_g: int = 0


def reset_modbus_state(config: ResetConfig) -> None:
    client = ModbusTcpClient(config.host, port=config.port)

    if not client.connect():
        raise RuntimeError(f"Impossible de se connecter à Modbus sur {config.host}:{config.port}")

    try:
        client.write_register(address=0, value=config.consigne_vitesse, device_id=config.unit_id)
        client.write_register(address=1, value=config.erreur_rollback, device_id=config.unit_id)
        client.write_register(address=10, value=config.force_g, device_id=config.unit_id)

        client.write_coil(address=0, value=False, device_id=config.unit_id)
        client.write_coil(address=1, value=True, device_id=config.unit_id)
        client.write_coil(address=2, value=False, device_id=config.unit_id)
        client.write_coil(address=3, value=True, device_id=config.unit_id)
        client.write_coil(address=4, value=False, device_id=config.unit_id)
    finally:
        client.close()


def restart_services() -> None:
    services = [
        # "back",
        "actuator-vfd-propulsion",
        "actuator-budget-brakes",
        "sensor-rusty-block-zone",
        "sensor-duct-tape-harness",
        "sensor-g-force-pain-index",
    ]

    subprocess.run(["docker", "compose", "restart", *services], check=True)
    wait_for_api_ready()


def wait_for_api_ready(timeout_seconds: int = 45) -> None:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with urlopen("http://localhost/api/status", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and "consigne_vitesse" in payload:
                    return
        except URLError:
            pass
        except Exception:
            pass

        time.sleep(1)

    raise RuntimeError("Le backend ne répond pas après le redémarrage des services")


def main() -> int:
    parser = argparse.ArgumentParser(description="Réinitialise l'état de la simulation Fistiland.")
    parser.add_argument("--host", default="127.0.0.1", help="Hôte Modbus/OpenPLC (défaut: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=502, help="Port Modbus (défaut: 502)")
    parser.add_argument("--unit-id", type=int, default=1, help="Identifiant Modbus du PLC (défaut: 1)")
    parser.add_argument("--no-restart", action="store_true", help="Ne redémarre pas les services Docker")
    args = parser.parse_args()

    config = ResetConfig(host=args.host, port=args.port, unit_id=args.unit_id)

    try:
        reset_modbus_state(config)
        if not args.no_restart:
            restart_services()
    except Exception as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 1

    print("Fistiland réinitialisé: registres Modbus remis au nominal.")
    if args.no_restart:
        print("Redémarrage Docker ignoré.")
    else:
        print("Services Docker redémarrés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())