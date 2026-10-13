# device-check

**Abrí el link en tu celular y mirá qué dispositivo tenés.** Sin instalar nada.

👉 **https://bridemirci.github.io/device-check/**

Una página con estética de terminal Android que detecta tu equipo desde el navegador:

```
you@sm-t830:~$ neofetch
Dispositivo: SM-T830
Sistema: Android 10
Chip: Qualcomm Snapdragon 835 (probable)
GPU: Adreno 540
Pantalla: 2560x1600 @ 60Hz · x2.25
Batería: 87% · cargando
```

## Qué muestra

- **Modelo**, sistema y navegador
- **Chip**, deducido de la GPU en celulares con Snapdragon
- **GPU**, núcleos de CPU y RAM aproximada
- **Pantalla**: resolución, frecuencia de refresco (Hz) y HDR
- **Batería**: carga, si está cargando y tiempo estimado
- **Benchmark de CPU** (un núcleo y multinúcleo), comparado contra una Galaxy Tab S4
- Botón **SHARE** para mandar el informe por WhatsApp o donde quieras

Todo se calcula en tu navegador: la página no envía tus datos a ningún lado.

### Qué depende del navegador

| Dato | Chrome / Edge / Samsung Internet | Firefox | Safari (iPhone) |
|---|---|---|---|
| Modelo exacto | ✅ | ❌ | ❌ (solo "iPhone") |
| Batería | ✅ | ❌ | ❌ |
| RAM aproximada | ✅ (tope 8 GB) | ❌ | ❌ |
| GPU, pantalla, benchmark | ✅ | ✅ | ✅ |

Los navegadores no exponen la salud de la batería, los ciclos de carga ni el almacenamiento total del dispositivo.

## Modo avanzado: con Termux

Si usás [Termux](https://f-droid.org/packages/com.termux/), podés correr el servidor local. Suma datos que el navegador no puede ver:
- RAM, almacenamiento y CPU en vivo
- Salud, temperatura y corriente de la batería (con la app Termux:API)
- Chip exacto y parche de seguridad
- Lista de procesos y control del wake lock

```bash
pkg install -y python git termux-api
git clone https://github.com/BriDemirci/device-check.git
bash device-check/iniciar.sh
```

El servidor escucha solo en `127.0.0.1`, y las acciones exigen una cabecera propia para que ninguna página externa pueda dispararlas.
