<#
  device-check · controles de música para el wallpaper

  Los wallpapers web de Wallpaper Engine y Lively solo pueden LEER qué canción suena.
  Este script escucha en http://localhost:8977 y, cuando tocás un botón del wallpaper,
  aprieta las teclas multimedia de Windows (anterior, play/pausa, siguiente).
  Funciona con Spotify, YouTube en el navegador y cualquier app que use esos controles.

  Uso:
    iniciar.bat       lo arranca ahora, oculto
    instalar.bat      lo arranca ahora y cada vez que prendés la PC
    desinstalar.bat   lo cierra y lo saca del inicio
#>
param([switch]$Instalar, [switch]$Desinstalar, [int]$Puerto = 8977)

$ErrorActionPreference = 'Stop'
$argumentos = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`""

function Cerrar-Otros {
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*device-check-media.ps1*' -and $_.ProcessId -ne $PID } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

if ($Instalar -or $Desinstalar) {
  $acceso = Join-Path ([Environment]::GetFolderPath('Startup')) 'device-check controles.lnk'
}

if ($Instalar) {
  $shell = New-Object -ComObject WScript.Shell
  $lnk = $shell.CreateShortcut($acceso)
  $lnk.TargetPath = (Get-Command powershell.exe).Source
  $lnk.Arguments = $argumentos
  $lnk.WindowStyle = 7
  $lnk.Description = 'device-check: controles de música para el wallpaper'
  $lnk.Save()
  Cerrar-Otros
  Start-Process -FilePath $lnk.TargetPath -ArgumentList $argumentos -WindowStyle Hidden
  Write-Host 'Listo: los controles ya están andando y van a arrancar solos con Windows.'
  return
}

if ($Desinstalar) {
  Remove-Item $acceso -ErrorAction SilentlyContinue
  Cerrar-Otros
  Write-Host 'Listo: los controles se cerraron y ya no arrancan con Windows.'
  return
}

Add-Type -Namespace DeviceCheck -Name Teclas -MemberDefinition @'
[DllImport("user32.dll")]
public static extern void keybd_event(byte vk, byte scan, uint flags, System.UIntPtr extra);
'@

# Códigos de las teclas multimedia de Windows
$TECLAS = @{ playpause = 0xB3; next = 0xB0; prev = 0xB1 }

function Apretar([byte]$tecla) {
  [DeviceCheck.Teclas]::keybd_event($tecla, 0, 0, [UIntPtr]::Zero)
  [DeviceCheck.Teclas]::keybd_event($tecla, 0, 2, [UIntPtr]::Zero)   # 2 = soltar la tecla
}

# Solo se aceptan pedidos del wallpaper (archivo local) o de esta misma PC.
# Las páginas web siempre tienen un origen http(s):// de otro sitio, así que no pueden usarlo.
function Origen-Permitido([string]$origen) {
  if (-not $origen -or $origen -eq 'null') { return $true }
  if ($origen -match '^https?://(localhost|127\.0\.0\.1)(:\d+)?$') { return $true }
  return $origen -notmatch '^https?://'
}

$http = New-Object System.Net.HttpListener
$http.Prefixes.Add("http://localhost:$Puerto/")
try { $http.Start() }
catch { Write-Host "El puerto $Puerto está ocupado. ¿Ya estaba corriendo?"; return }
Write-Host "Controles de música andando en http://localhost:$Puerto (cerrá esta ventana para apagarlos)"

while ($http.IsListening) {
  # Cualquier error en un pedido se ignora: el servidor tiene que seguir andando
  try {
    $ctx = $http.GetContext()
    $pedido = $ctx.Request
    $respuesta = $ctx.Response
    $origen = $pedido.Headers['Origin']
    $accion = $pedido.Url.AbsolutePath.Trim('/').ToLower()
    $codigo = 200
    $cuerpo = '{"ok":true}'

    if (-not (Origen-Permitido $origen)) {
      $codigo = 403; $cuerpo = '{"ok":false}'
    } else {
      if ($origen) {
        $respuesta.AddHeader('Access-Control-Allow-Origin', $origen)
        $respuesta.AddHeader('Access-Control-Allow-Headers', 'X-Device-Check')
        $respuesta.AddHeader('Access-Control-Allow-Methods', 'GET, POST')
        # Chrome pide permiso extra para que un archivo local hable con localhost
        $respuesta.AddHeader('Access-Control-Allow-Private-Network', 'true')
      }
      if ($pedido.HttpMethod -eq 'OPTIONS') { $codigo = 204; $cuerpo = '' }
      elseif ($accion -eq 'ping') { $cuerpo = '{"ok":true,"app":"device-check","version":1}' }
      elseif ($pedido.HttpMethod -eq 'POST' -and $pedido.Headers['X-Device-Check'] -eq '1' -and $TECLAS.ContainsKey($accion)) {
        # Un error al apretar la tecla no tiene que tirar abajo el servidor
        try { Apretar $TECLAS[$accion] } catch { $codigo = 500; $cuerpo = '{"ok":false}' }
      }
      else { $codigo = 404; $cuerpo = '{"ok":false}' }
    }

    $bytes = [Text.Encoding]::UTF8.GetBytes($cuerpo)
    $respuesta.StatusCode = $codigo
    $respuesta.ContentType = 'application/json'
    if ($bytes.Length) { $respuesta.OutputStream.Write($bytes, 0, $bytes.Length) }
    $respuesta.Close()
  } catch { }
}
