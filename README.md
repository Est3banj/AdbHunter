# AdbHunter

Herramienta de escritorio para monitorear y eliminar aplicaciones maliciosas en dispositivos Android via ADB.

## Objetivo

Detectar en tiempo real qué app está en foreground cuando aparece un anuncio/adware, y permitir desinstalarla con un click.

## Funcionalidades

- **Monitoreo en tiempo real**: Detecta qué app está en primer plano
- **Force Stop**: Forzar cierre de apps maliciosas
- **Desinstalar**: Eliminar apps del dispositivo
- **Whitelist**: Proteger apps para que no se puedan.desinstalar por accidente
- **Refresh**: Reiniciar el escaneo desde cero

## Stack Tecnológico

- **Lenguaje**: Python 3
- **GUI**: Tkinter (versión principal)
- **ADB**: Platform Tools (instalado en el sistema)
- **Compatibilidad**: macOS, Windows, Linux

## Requisitos

1. Python 3.8+
2. ADB Platform Tools en PATH
3. Device Android con Debug USB habilitado

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

## Controles

| Botón | Función |
|------|---------|
| **START/STOP** | Iniciar/detener monitoreo |
| **FORCE STOP** | Forzar cierre de la app seleccionada |
| **DESINSTALAR** | Eliminar la app seleccionada |
| **+ WHITELIST** | Proteger/remover protección de app |
| **REFRESH** | Reiniciar escaneo desde cero |

## Arquitectura

```
AdbHunter/
├── main.py           # Entry point (GUI Tkinter)
├── src/
│   ├── core/        # Lógica de ADB
│   │   ├── adb.py   # Comandos ADB
│   │   └── watcher.py # Loop de monitoreo
│   ├── ui/          # Interfaz (CustomTkinter)
│   └── config/      # Configuración
│       └── settings.py
└── requirements.txt
```

## Cómo usar

1. Conectá tu dispositivo Android via USB
2. Habilitá Debug USB en opciones de desarrollador
3. Ejecutá `adbhunter`
4. Click **START** para comenzar a monitorear
5. Cuando aparezca una app sospechosa, seleccioná del historial
6. Elegí **FORCE STOP** (cerrar) o **DESINSTALAR** (eliminar)

## Licence

MIT