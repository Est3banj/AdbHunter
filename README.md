# AdbHunter

Herramienta de escritorio para monitorear y eliminar aplicaciones maliciosas en dispositivos Android via ADB.

## Objetivo

Detectar en tiempo real qué app está en foreground cuando aparece un anuncio/adware, y permitir desinstalarla con un click.

## Stack Tecnológico

- **Lenguaje**: Python 3
- **GUI**: CustomTkinter
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
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
python src/main.py
```

## Arquitectura

```
src/
├── core/           # Lógica de ADB
│   ├── adb.py      # Comandos ADB
│   └── watcher.py # Loop de monitoreo
├── ui/             # Interfaz
│   └── app.py      # GUI CustomTkinter
├── config/         # Configuración
│   └── settings.py # Settings
└── main.py         # Entry point
```

## Licence

MIT