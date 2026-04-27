# AdbHunter

Herramienta de escritorio para monitorear y eliminar aplicaciones maliciosas en dispositivos Android via ADB.

## Objetivo

Detectar en tiempo real qué app está en foreground cuando aparece un anuncio/adware, y permitir desinstalarla con un click.

## Funcionalidades

- **Monitoreo en tiempo real**: Detecta qué app está en primer plano
- **Force Stop**: Forzar cierre de apps maliciosas
- **Desinstalar**: Eliminar apps del dispositivo
- **Whitelist**: Proteger apps para que no se puedan desinstalar por accidente
- **Refresh**: Reiniciar el escaneo desde cero
- **Conexión WiFi**: Soporte para Wireless Debugging (sin cable USB)
- **Sistema de licencias**: Activación online via Firebase

## Stack Tecnológico

- **Lenguaje**: Python 3
- **GUI**: Tkinter
- **ADB**: Platform Tools (instalado en el sistema)
- **Licencias**: Firebase Firestore
- **Compatibilidad**: macOS, Windows, Linux

## Requisitos

1. Python 3.8+
2. ADB Platform Tools en PATH
3. Device Android con Debug USB o Wireless Debugging habilitado

### Instalación de ADB

**macOS:**
```bash
brew install android-platform-tools
```

**Windows:**
Descargar SDK Platform Tools de https://developer.android.com/studio/releases/platform-tools

## Uso

```bash
# 1. Ejecutar
python main.py
# O usando el alias
adbhunter
```

## Conexión del dispositivo

### Opción 1: USB
1. Conectar por USB
2. Habilitar Debug USB en opciones de desarrollador
3. Autorizar el equipo en el dispositivo

### Opción 2: WiFi (Wireless Debugging)
1. En el dispositivo: Developer Options → Wireless Debugging → Pair device with pairing code
2. En AdbHunter: Click **WiFi**, ingresar IP:Puerto y código de pairing
3. ¡Listo! Sin cable USB

### Opción 3: USB → WiFi (primera vez)
1. Conectar por USB
2. Click **WiFi** en AdbHunter para habilitar modo TCP
3. Desconectar cable y usar wireless

## Controles

| Botón | Función |
|------|---------|
| **START/STOP** | Iniciar/detener monitoreo |
| **FORCE STOP** | Forzar cierre de la app seleccionada |
| **DESINSTALAR** | Eliminar la app seleccionada |
| **+ Whitelist** | Proteger/remover protección de app |
| **REFRESH** | Reiniciar escaneo desde cero |
| **WiFi** | Configurar conexión wireless |
| **ⓘ** | Información del desarrollador |

## Arquitectura

```
AdbHunter/
├── main.py           # Entry point (GUI Tkinter)
├── firebase-creds.json  # Credenciales Firebase
├── src/
│   ├── core/       # Lógica de ADB
│   │   ├── adb.py  # Comandos ADB
│   │   └── watcher.py # Loop de monitoreo
│   ├── ui/         # Interfaz alternativa (CustomTkinter)
│   └── config/      # Configuración
│       └── settings.py
├── requirements.txt
└── README.md
```

## Cómo usar

1. Ejecutá `adbhunter`
2. Conectá tu dispositivo (USB o WiFi)
3. Click **START** para comenzar a monitorear
4. Cuando aparezca una app sospechosa, seleccioná del historial
5. Elegí **FORCE STOP** (cerrar) o **DESINSTALAR** (eliminar)

## Licencia

AdbHunter requiere una licencia válida para funcionar.

- **Modo demo**: Funcionalidades limitadas si no hay licencia activa
- ** Activación**: Key en formato `ADH-YYMMDD-XXXX`

Para obtener una licencia, contactá al desarrollador.

## Desarrollador

[@Est3banj](https://github.com/Est3banj) - [Telegram](https://t.me/Est3banj)

## MIT License