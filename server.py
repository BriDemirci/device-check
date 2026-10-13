"""Panel Termux: muestra el hardware y el estado de un dispositivo Android desde el navegador.

Funciona en Termux directo o dentro de una distro PRoot (proot-distro).
Solo usa la librería estándar. Escucha únicamente en 127.0.0.1.
"""

import json
import os
import platform
import signal
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = "127.0.0.1", int(os.environ.get("PANEL_PORT", "8765"))
STATIC = Path(__file__).parent / "static"
CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")
NCPU = os.cpu_count() or 1
MY_UID = os.getuid()

TERMUX = "/data/data/com.termux/files/usr"
TERMUX_ENV = {
    "HOME": "/data/data/com.termux/files/home",
    "PREFIX": TERMUX,
    "PATH": f"{TERMUX}/bin:/system/bin",
    "LD_LIBRARY_PATH": f"{TERMUX}/lib",
    "TMPDIR": f"{TERMUX}/tmp",
}

# Procesos que no se pueden cerrar desde el panel
PROTEGIDOS = {"proot", "bash", "sh", "zsh", "fish", "login", "claude", "com.termux"}

# Nombre comercial de los chips Qualcomm más comunes (ro.board.platform)
CHIPS = {
    "msm8996": "Snapdragon 820/821", "msm8998": "Snapdragon 835", "sdm845": "Snapdragon 845",
    "msmnile": "Snapdragon 855", "kona": "Snapdragon 865", "lahaina": "Snapdragon 888",
    "taro": "Snapdragon 8 Gen 1", "kalama": "Snapdragon 8 Gen 2", "pineapple": "Snapdragon 8 Gen 3",
    "sun": "Snapdragon 8 Elite", "sdm660": "Snapdragon 660", "sdm670": "Snapdragon 670",
    "sm6150": "Snapdragon 675", "trinket": "Snapdragon 665", "bengal": "Snapdragon 662/680",
    "atoll": "Snapdragon 720G", "lito": "Snapdragon 765G", "holi": "Snapdragon 480",
    "msm8953": "Snapdragon 625", "sdm450": "Snapdragon 450", "msm8937": "Snapdragon 430",
}

SALUD = {
    "GOOD": "Buena", "OVERHEAT": "Sobrecalentada", "DEAD": "Agotada", "OVER_VOLTAGE": "Sobretensión",
    "COLD": "Fría", "UNSPECIFIED_FAILURE": "Falla", "UNKNOWN": "Desconocida",
}
ESTADO_BAT = {
    "CHARGING": "Cargando", "DISCHARGING": "Descargando", "FULL": "Completa",
    "NOT_CHARGING": "Sin cargar", "UNKNOWN": "Desconocido",
}
CONEXION = {"PLUGGED_AC": "Cargador", "PLUGGED_USB": "USB", "PLUGGED_WIRELESS": "Inalámbrica", "UNPLUGGED": "Desconectada"}

wakelock_activo = None  # Android no expone el estado; recordamos la última acción


def termux(*args, timeout=10):
    """Corre un comando de Termux (o de /system/bin) y devuelve su salida, o None si falla."""
    try:
        r = subprocess.run(args, env=TERMUX_ENV, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def comando_termux(nombre):
    ruta = f"{TERMUX}/bin/{nombre}"
    return [f"{TERMUX}/bin/sh", ruta] if os.path.exists(ruta) else None


def getprops():
    salida = termux("getprop") or ""
    props = {}
    for linea in salida.splitlines():
        # Formato: [clave]: [valor]
        if linea.startswith("[") and "]: [" in linea:
            clave, valor = linea[1:-1].split("]: [", 1)
            props[clave] = valor
    return props


def frecuencias_cpu():
    grupos = {}
    for n in range(NCPU):
        try:
            khz = int(Path(f"/sys/devices/system/cpu/cpu{n}/cpufreq/cpuinfo_max_freq").read_text())
        except (OSError, ValueError):
            continue
        grupos[khz] = grupos.get(khz, 0) + 1
    return [{"nucleos": c, "ghz": round(khz / 1e6, 2)} for khz, c in sorted(grupos.items())]


def entorno():
    if "PRoot" in platform.release() or os.environ.get("PROOT_TMP_DIR"):
        try:
            for linea in open("/etc/os-release"):
                if linea.startswith("PRETTY_NAME="):
                    return linea.split("=", 1)[1].strip().strip('"') + " (PRoot)"
        except OSError:
            pass
        return "Linux (PRoot)"
    return "Termux"


def leer_dispositivo():
    p = getprops()
    plataforma = p.get("ro.board.platform") or p.get("ro.hardware") or ""
    nombre_chip = CHIPS.get(plataforma) or p.get("ro.soc.model") or plataforma
    fabricante_soc = p.get("ro.soc.manufacturer") or ("Qualcomm" if plataforma in CHIPS else "")
    if fabricante_soc and fabricante_soc.lower() not in nombre_chip.lower():
        nombre_chip = f"{fabricante_soc} {nombre_chip}"
    return {
        "fabricante": p.get("ro.product.manufacturer", "").capitalize() or "Desconocido",
        "modelo": p.get("ro.product.marketname") or p.get("ro.product.model") or platform.node(),
        "codigo": p.get("ro.product.device", ""),
        "android": p.get("ro.build.version.release", ""),
        "sdk": p.get("ro.build.version.sdk", ""),
        "parche": p.get("ro.build.version.security_patch", ""),
        "build": p.get("ro.build.display.id", ""),
        "chip": nombre_chip,
        "plataforma": plataforma,
        "abi": p.get("ro.product.cpu.abi", platform.machine()),
        "densidad": p.get("ro.sf.lcd_density", ""),
        "nucleos": NCPU,
        "frecuencias": frecuencias_cpu(),
        "entorno": entorno(),
        "usuario": os.environ.get("USER") or os.environ.get("LOGNAME") or "termux",
        "termux_api": comando_termux("termux-battery-status") is not None,
    }


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
    st = os.statvfs(Path.home())
    total = st.f_blocks * st.f_frsize
    libre = st.f_bavail * st.f_frsize
    return {"total": total, "usado": total - libre, "libre": libre}


class Bateria:
    """termux-battery-status tarda (o se cuelga si falta la app Termux:API): se lee en segundo plano."""

    def __init__(self):
        self.datos = None
        self.error = None
        threading.Thread(target=self.bucle, daemon=True).start()

    def bucle(self):
        while True:
            cmd = comando_termux("termux-battery-status")
            if not cmd:
                self.error = "falta-paquete"
            else:
                salida = termux(*cmd, timeout=12)
                try:
                    b = json.loads(salida) if salida else None
                except json.JSONDecodeError:
                    b = None
                if b is None:
                    self.error = "falta-app"
                else:
                    self.error = None
                    self.datos = {
                        "porcentaje": b.get("percentage"),
                        "estado": ESTADO_BAT.get(b.get("status"), b.get("status")),
                        "salud": SALUD.get(b.get("health"), b.get("health")),
                        "salud_ok": b.get("health") == "GOOD",
                        "temperatura": b.get("temperature"),
                        "conexion": CONEXION.get(b.get("plugged"), b.get("plugged")),
                        "corriente_ma": round(b["current"] / 1000) if isinstance(b.get("current"), (int, float)) else None,
                        # Solo Android 14+ informa los ciclos de carga
                        "ciclos": b.get("cycle") if b.get("cycle", -1) not in (-1, None) else None,
                    }
            time.sleep(15)


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
            rss = int(campos[21]) * PAGE
            uid = os.stat(f"/proc/{pid}").st_uid
        except (OSError, IndexError, ValueError):
            continue
        procesos[pid] = {"pid": pid, "nombre": nombre, "ticks": ticks, "rss": rss, "uid": uid}
    return procesos


def es_cerrable(p):
    return p["uid"] == MY_UID and p["nombre"] not in PROTEGIDOS and p["pid"] != os.getpid()


class MuestreoCPU:
    """/proc/stat no es confiable en Android/PRoot: medimos la CPU sumando el tiempo de cada proceso."""

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
            delta = max(p["ticks"] - previos[pid]["ticks"], 0) if pid in previos else 0
            total += delta
            lista.append({
                "pid": pid,
                "nombre": p["nombre"],
                "rss": p["rss"],
                "cpu": round(100 * delta / ticks_disponibles, 1),
                "cerrable": es_cerrable(p),
            })
        lista.sort(key=lambda x: x["rss"], reverse=True)
        return round(100 * total / ticks_disponibles, 1), lista


cpu = MuestreoCPU()
bateria = Bateria()
dispositivo = leer_dispositivo()


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
        if self.path == "/api/dispositivo":
            return self.responder(200, dispositivo)
        if self.path == "/api/estado":
            uso_cpu, procesos = cpu.medir()
            return self.responder(200, {
                "ram": leer_meminfo(),
                "disco": leer_disco(),
                "cpu": {"uso": uso_cpu, "nucleos": NCPU},
                "bateria": bateria.datos,
                "bateria_error": bateria.error,
                "procesos": procesos[:12],
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
            cmd = comando_termux("termux-wake-lock" if activar else "termux-wake-unlock")
            ok = bool(cmd) and termux(*cmd) is not None
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
