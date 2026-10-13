"""Panel de la tablet: muestra RAM, disco, CPU y procesos de Ubuntu (PRoot en Termux).

Solo usa la librería estándar. Escucha únicamente en 127.0.0.1.
"""

import json
import os
import signal
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = "127.0.0.1", int(os.environ.get("PANEL_PORT", "8765"))
STATIC = Path(__file__).parent / "static"
CLK_TCK = os.sysconf("SC_CLK_TCK")
NCPU = os.cpu_count() or 1
MY_UID = os.getuid()

TERMUX = "/data/data/com.termux/files/usr"
TERMUX_ENV = {
    "HOME": f"{TERMUX}/../home",
    "PREFIX": TERMUX,
    "PATH": f"{TERMUX}/bin",
    "LD_LIBRARY_PATH": f"{TERMUX}/lib",
}

# Procesos que no se pueden cerrar desde el panel
PROTEGIDOS = {"proot", "bash", "sh", "claude", "com.termux"}

wakelock_activo = None  # Android no expone el estado; recordamos la última acción


def leer_meminfo():
    datos = {}
    with open("/proc/meminfo") as f:
        for linea in f:
            clave, valor = linea.split(":", 1)
            datos[clave] = int(valor.split()[0]) * 1024
    total = datos["MemTotal"]
    disponible = datos.get("MemAvailable", datos["MemFree"])
    return {"total": total, "usado": total - disponible, "disponible": disponible}


def leer_disco():
    st = os.statvfs("/")
    total = st.f_blocks * st.f_frsize
    libre = st.f_bavail * st.f_frsize
    return {"total": total, "usado": total - libre, "libre": libre}


def leer_procesos():
    procesos = {}
    for entrada in os.scandir("/proc"):
        if not entrada.name.isdigit():
            continue
        pid = int(entrada.name)
        try:
            with open(f"/proc/{pid}/stat") as f:
                cabeza, resto = f.read().rsplit(")", 1)
            campos = resto.split()
            nombre = cabeza.split("(", 1)[1]
            ticks = int(campos[11]) + int(campos[12])
            rss = int(campos[21]) * os.sysconf("SC_PAGE_SIZE")
            uid = os.stat(f"/proc/{pid}").st_uid
        except (OSError, IndexError, ValueError):
            continue
        procesos[pid] = {"pid": pid, "nombre": nombre, "ticks": ticks, "rss": rss, "uid": uid}
    return procesos


def es_cerrable(p):
    return p["uid"] == MY_UID and p["nombre"] not in PROTEGIDOS and p["pid"] != os.getpid()


class MuestreoCPU:
    """/proc/stat es falso en PRoot: medimos la CPU sumando el tiempo de cada proceso."""

    def __init__(self):
        self.lock = threading.Lock()
        self.anterior = (time.monotonic(), leer_procesos())

    def medir(self):
        with self.lock:
            t0, previos = self.anterior
            t1, actuales = time.monotonic(), leer_procesos()
            self.anterior = (t1, actuales)
        ticks_disponibles = max(t1 - t0, 0.001) * CLK_TCK * NCPU
        lista, total = [], 0
        for pid, p in actuales.items():
            delta = p["ticks"] - previos[pid]["ticks"] if pid in previos else 0
            total += max(delta, 0)
            lista.append({
                "pid": pid,
                "nombre": p["nombre"],
                "rss": p["rss"],
                "cpu": round(100 * max(delta, 0) / ticks_disponibles, 1),
                "cerrable": es_cerrable(p),
            })
        lista.sort(key=lambda x: x["rss"], reverse=True)
        return round(100 * total / ticks_disponibles, 1), lista


cpu = MuestreoCPU()


def ejecutar_termux(comando):
    binario = f"{TERMUX}/bin/{comando}"
    if not os.path.exists(binario):
        return False
    r = subprocess.run([f"{TERMUX}/bin/sh", binario], env=TERMUX_ENV,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    return r.returncode == 0


class Panel(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, *args):
        pass

    def responder(self, codigo, cuerpo):
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path == "/api/estado":
            uso_cpu, procesos = cpu.medir()
            return self.responder(200, {
                "ram": leer_meminfo(),
                "disco": leer_disco(),
                "cpu": {"uso": uso_cpu, "nucleos": NCPU},
                "procesos": procesos[:15],
                "wakelock": wakelock_activo,
            })
        return super().do_GET()

    def do_POST(self):
        # Cabecera propia: obliga a un preflight CORS, así ninguna web externa puede llamar acá
        if self.headers.get("X-Panel") != "1":
            return self.responder(403, {"error": "prohibido"})
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return self.responder(400, {"error": "JSON inválido"})

        global wakelock_activo
        if self.path == "/api/wakelock":
            activar = bool(cuerpo.get("activar"))
            ok = ejecutar_termux("termux-wake-lock" if activar else "termux-wake-unlock")
            if ok:
                wakelock_activo = activar
            return self.responder(200 if ok else 500, {"ok": ok, "wakelock": wakelock_activo})

        if self.path == "/api/cerrar":
            pid = cuerpo.get("pid")
            objetivo = leer_procesos().get(pid) if isinstance(pid, int) else None
            if not objetivo or not es_cerrable(objetivo):
                return self.responder(403, {"error": "Ese proceso no se puede cerrar"})
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as e:
                return self.responder(500, {"error": str(e)})
            return self.responder(200, {"ok": True})

        return self.responder(404, {"error": "no existe"})


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, PORT), Panel)
    print(f"Panel en http://localhost:{PORT}  (Ctrl+C para cerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
