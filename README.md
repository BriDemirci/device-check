# Panel Termux

Un panel con estética de terminal que te muestra **qué celular o tablet tenés y cómo está**, desde el navegador del mismo dispositivo.

```
u0@gts4lwifi:~$ neofetch
Dispositivo: Samsung SM-T830 (gts4lwifi)
Android: 10 · API 29
Chip: Qualcomm Snapdragon 835
CPU: 4×1.90GHz + 4×2.36GHz · arm64-v8a
Pantalla: 2560x1600 @ 60Hz · 360dpi
Batería: 87% · salud buena
```

## Qué muestra

- **Dispositivo:** fabricante, modelo, versión de Android, parche de seguridad, chip y frecuencias de la CPU
- **Pantalla:** resolución, frecuencia de refresco y densidad
- **Batería** (con Termux:API): carga, salud, temperatura, corriente y ciclos (solo Android 14 o superior)
- **RAM, almacenamiento y CPU** en vivo
- **Procesos** de Termux ordenados por memoria, con opción de cerrarlos
- **Wake lock** para que Android no suspenda Termux

No necesita root. Solo usa la librería estándar de Python.

## Instalación (en tu celular)

1. Instalá **Termux** y **Termux:API** desde [F-Droid](https://f-droid.org/packages/com.termux/) o desde GitHub ([Termux](https://github.com/termux/termux-app/releases), [Termux:API](https://github.com/termux/termux-api/releases)).
   Las dos apps tienen que venir de la **misma fuente**. La versión de Play Store no es compatible.
2. Abrí Termux y pegá:

```bash
pkg install -y python git termux-api
git clone https://github.com/BriDemirci/panel-tablet.git
bash panel-tablet/iniciar.sh
```

Se abre el navegador con el panel. Las próximas veces, con `bash panel-tablet/iniciar.sh` alcanza.

Sin la app Termux:API anda igual, pero no muestra la batería.

## Uso avanzado

- Otro puerto: `PANEL_PORT=9000 bash iniciar.sh`
- Cerrar el panel: `pkill -f server.py`
- También funciona dentro de una distro de `proot-distro` (Ubuntu, Debian…).

## Seguridad

- Escucha solo en `127.0.0.1`: nadie más en tu red Wi-Fi puede verlo.
- Las acciones (cerrar procesos, wake lock) exigen una cabecera propia, así ninguna página web externa puede dispararlas.
- No deja cerrar la shell, `proot`, `claude` ni la app Termux.
- No envía datos a ningún lado. La única conexión externa es la fuente tipográfica de Google Fonts; sin internet usa la fuente monoespaciada del sistema.
