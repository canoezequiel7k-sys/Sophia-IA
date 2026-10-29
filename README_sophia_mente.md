# Sophia IA — Compañera digital de escritorio

Sophia IA es una compañera digital diseñada para conversar, acompañar y mantenerse en una segunda
pantalla. Cuenta con dos modalidades:
1. **Modo Escritorio interactivo (recomendado):** ventana nativa con avatar, expresiones dinámicas y animaciones de conversación.
2. **Modo Terminal:** interfaz de consola conservada para comandos y compatibilidad.

Sophia se conecta a **Google Gemini API** para conversar con naturalidad y recordar los intercambios previos
mediante `data/memoria.json`. Puede hablar sobre cualquier tema y no está limitada a una tutoría técnica.

---

## Iniciar

### 1. Modo Escritorio (Ventana con avatar y expresiones)
- **Windows:** Doble clic en `iniciar_sophia_desktop.bat`.
- **Comando:** `python main.py --desktop`

### 2. Modo Terminal
- **Windows:** Doble clic en `iniciar_sophia_ia.bat`.
- **Comando:** `python main.py`

---

## Configurar el Cerebro Gratuito (Google Gemini API)

1. Obtené tu clave gratuita en [Google AI Studio](https://aistudio.google.com/).
2. Creá un archivo `.env` en la raíz del proyecto (podés copiar `.env.example`).
3. Agregá tu clave:
   ```env
   GEMINI_API_KEY=tu_clave_aqui
   ```
¡Listo! Sophia usará Gemini para responder de forma natural, cambiar sus expresiones y animar sus escenas de pensamiento y conversación.

---

## Comandos en Terminal

- `/ayuda` o `sop -help`: mostrar comandos.
- `/memoria`: ver los intercambios guardados.
- `/borrar`: borrar todos los recuerdos (pide confirmación).
- `clear`: limpiar la terminal.
- `sop -close` o `salir`: cerrar la aplicación.
- `sop -new`: abrir otra sesión en Windows Terminal.
- `sop -terminal`: abrir una terminal limpia de Windows.

---

## Capas del Proyecto (Clean Architecture)

```
interface ──► application ──► domain
infrastructure ──► domain
main.py es la raíz de composición y conecta las piezas.
```

| Carpeta/archivo | Responsabilidad |
|---|---|
| `companera/domain/` | Modelos de ánimos, temas e intercambios guardados (`models.py`). |
| `companera/application/` | Lógica de conversación, búsqueda y puertos abstractos (`ports.py`). |
| `companera/infrastructure/` | Cliente de Google Gemini API, persistencia en JSON, búsqueda Markdown y reloj. |
| `companera/interface/` | Interfaz de escritorio nativa (`desktop_pet.py`) y consola de terminal (`console.py`). |
| `companera/assets/sophia/` | Sprites, expresiones faciales e iconos de Sophia. |
| `main.py` | Entrada principal del programa (soporta `--desktop` o modo terminal). |

---

## Pruebas

Para ejecutar la suite de pruebas unitarias:

```bash
python -m unittest discover -s tests -v
```
