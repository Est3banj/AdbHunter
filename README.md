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
- **Busca ADB automáticamente**: Detecta ADB en varias ubicaciones del sistema
- **Rate limiting**: Máximo 3 desinstalaciones/hora por seguridad

## Modo Demo (Sin Licencia)

El repositorio incluye una versión gratuita que funciona sin licencia:
- Todas las funcionalidades activas
- Rate limit de 3 desinstalaciones/hora
- No requiere conexión a internet

**Para funcionalidad completa sin límites, se puede adquirir una licencia del desarrollador.**

## Stack Tecnológico

- **Lenguaje**: Python 3
- **GUI**: Tkinter
- **ADB**: Platform Tools (se detecta automáticamente)
- **Compatibilidad**: macOS, Windows, Linux

## Requisitos

1. Python 3.8+
2. Device Android con Debug USB o Wireless Debugging habilitado
3. ADB se detecta automáticamente (no requiere PATH)

### Instalación de ADB (si no se detecta solo)

**macOS:**
```bash
brew install android-platform-tools
```

**Windows:**
Descargar SDK Platform Tools de https://developer.android.com/studio/releases/platform-tools

## Uso

```bash
# Ejecutar
python main.py
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
├── main.py              # Entry point (GUI Tkinter)
├── src/
│   ├── core/
│   │   ├── adb.py       # Comandos ADB + detección automática
│   │   └── watcher.py   # Loop de monitoreo
│   ├── ui/              # Interfaz alternativa
│   └── config/
│       └── settings.py  # Configuración
├── requirements.txt
└── README.md
```

## Compilar ejecutable

### macOS
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name AdbHunter --iconfile=AdbHunter.icns main.py
```

### Windows
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name AdbHunter --iconfile=AdbHunter.ico main.py
```

Los ejecutables se generan en la carpeta `dist/`.

## Licencia (Opcional)

- **Gratis**: Todas las funcionalidades con rate limit de 3 desinstalaciones/hora
- **Comprada**: Sin límites + soporte del desarrollador
- **Formato de key**: `ADH-YYMMDD-XXXX`

Para adquirir una licencia, contactá al desarrollador.

## Desarrollador

[@Est3banj](https://github.com/Est3banj) - [Telegram](https://t.me/Est3banj)

## MIT License