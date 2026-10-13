# Panel Tab S4

Panel web para ver en vivo cómo anda la tablet (Samsung Galaxy Tab S4 con Ubuntu en PRoot sobre Termux).

- **RAM y almacenamiento** de la tablet
- **CPU** de los procesos de Ubuntu (en PRoot, `/proc/stat` es falso, así que se mide proceso por proceso)
- **Procesos** de Ubuntu ordenados por RAM, con botón para cerrar los propios
- **Wake lock** de Termux para que Android no suspenda la CPU

Solo usa la librería estándar de Python: no hay nada que instalar.

## Uso

```bash
python3 server.py
```

Abrí <http://localhost:8765> en Chrome. Para usar otro puerto: `PANEL_PORT=9000 python3 server.py`.

## Seguridad

- Escucha solo en `127.0.0.1`: no es accesible desde otros dispositivos de la red.
- Las acciones exigen la cabecera `X-Panel`, así ninguna página web externa puede dispararlas.
- No deja cerrar `proot`, `bash`, `sh`, `claude` ni `com.termux`.
