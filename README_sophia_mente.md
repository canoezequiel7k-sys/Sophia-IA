# Sophia IA — Asistente y compañera de escritorio en Python

Sophia IA es una compañera y tutora de programación en Python diseñada para dejar abierta en una segunda
pantalla. Cuenta con dos modalidades:
1. **Modo Escritorio interactivo (Recomendado):** Una ventana nativa flotante con avatar y expresiones dinámicas inspiradas en Capri, fijable sobre otras ventanas y arrastrable a tu segundo monitor.
2. **Modo Terminal:** Una interfaz conversacional clásica de consola.

Sophia se conecta de forma opcional y gratuita a **Google Gemini API** (Gemini Flash) para conversar fluidamente y ayudarte a programar, integrando tus apuntes locales de `companera/python context/` y recordando tus charlas en `data/memoria.json`. Si no configuras la API, sigue funcionando con su motor local de reglas y búsqueda de apuntes.

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
¡Listo! Sophia usará Gemini para responder de forma natural, cambiar sus expresiones en pantalla y consultar tus apuntes.

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
