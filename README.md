# device-check

**Abrí el link en tu celular y mirá qué dispositivo tenés.** Sin instalar nada.

👉 **https://bridemirci.github.io/device-check/**

La página detecta tu sistema y te abre la versión que corresponde, cada una con su estilo:

| Versión | Estilo | Link |
|---|---|---|
| **Android** | Terminal estilo Termux, con neofetch | [/android](https://bridemirci.github.io/device-check/android/) |
| **iOS** | Minimalista, widgets de vidrio (glassmorphism) | [/ios](https://bridemirci.github.io/device-check/ios/) |
| **macOS** | Escritorio con ventana de Terminal flotante y Dock | [/macos](https://bridemirci.github.io/device-check/macos/) |
| **Windows** | Windows 11 Fluent: Windows Terminal, widgets y blur azul | [/windows](https://bridemirci.github.io/device-check/windows/) |

Podés abrir cualquier versión desde cualquier dispositivo; los datos siempre son los del equipo que la abre. Para elegir a mano: [?elegir](https://bridemirci.github.io/device-check/?elegir).

## Qué muestra

- **Modelo**, sistema y navegador
- **Chip**: exacto en Mac con Chrome (M1, M2…); deducido de la GPU en celulares Snapdragon
- **Versión del sistema**: distingue Windows 10 de 11 y el nombre de macOS (Sequoia, Tahoe…) en Chrome y Edge
- **Modelo de iPhone** probable según el tamaño de pantalla
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

## Wallpaper

También hay una versión para usar **de fondo de pantalla en Windows**, con:
- neofetch con los datos de tu PC
- reloj
- **widget de música** con la canción que suena, la portada y el progreso
- **visualizador de audio** que se mueve con lo que escuchás

Cada parte respeta el estilo elegido: Android, iOS, macOS o Windows 11.

👉 [Vista previa en el navegador](https://bridemirci.github.io/device-check/wallpaper/) (con música de ejemplo)

### Wallpaper Engine
1. Descargá `device-check-wallpaper.zip` de [Releases](https://github.com/BriDemirci/device-check/releases/latest) y descomprimilo.
2. En Wallpaper Engine: **Abrir wallpaper → Abrir desde archivo** y elegí `index.html` de esa carpeta.
3. Para ver la canción: **Configuración → General → activar "Integración multimedia"** (funciona con Spotify, YouTube en el navegador y cualquier app que use los controles multimedia de Windows).
4. En las propiedades del wallpaper elegís el estilo, el lado de la terminal, los colores, la opacidad y qué widgets mostrar.

### Lively Wallpaper (gratis)
Arrastrá el `.zip` a la ventana de [Lively](https://www.rocksdanister.com/lively/). Las mismas opciones aparecen en "Personalizar".

> El widget de música **muestra** lo que suena; los wallpapers no pueden pausar ni cambiar de canción.

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
