# Sophia IA — Plan de implementación para agente Copilot

*Preparado el 29/10/2026 a partir de la lectura del código real del proyecto (`C:\Users\SystemAncestral\Documents\Sophia IA`).*

## 0. Cómo usar este documento

Este documento está escrito para que lo ejecute un agente de código (GitHub Copilot). Contiene fases ordenadas por dependencias. Cada tarea indica archivos, qué hacer y cómo saber que terminó.

### Reglas obligatorias

1. Trabajar **por fases, en orden**. Dentro de cada fase, tarea por tarea. Al terminar una fase, **detenerse y reportar** antes de seguir.
2. Un commit local por tarea, con prefijo `fix:`, `feat:`, `refactor:`, `test:` o `docs:`. **Prohibido** `git push`, `--force`, `reset --hard` o reescribir historial sin autorización explícita.
w4. **No agregar dependencias** que no figuren en este documento sin preguntar.
5. Antes de usar una API externa (Gemini, edge-tts, pygame-ce, pystray), **consultar su documentación oficial y la versión instalada**. Este plan nombra campos y parámetros según lo conocido, pero pueden haber cambiado; no inventar nombres.
6. Cambios mínimos y enfocados. **No reescribir el proyecto.** No tocar nada fuera del alcance de la tarea.
7. Respetar la arquitectura en capas: `domain` ← `application` ← `infrastructure` / `interface`. Las dependencias apuntan hacia adentro.
8. Cada tarea lleva tests. Correr `python -m unittest discover -s tests -v` antes de cada commit. Los tests **no** deben abrir ventanas, reproducir audio ni usar la red (usar fakes y mocks).
9. Textos que ve o escucha el usuario, y el prompt de Sophia: **español rioplatense** (vos, tenés, sos). Docstrings en español.
10. Si algo es ambiguo o el código real contradice este documento, **preguntar** en lugar de suponer.

### Plantilla de reporte por tarea

- **Tarea:** ID y título.
- **Qué cambió:** resumen en 2–4 líneas.
- **Archivos:** creados / modificados.
- **Cómo probar:** comandos o pasos manuales.
- **Pendientes o dudas:** lo que no se pudo cerrar.

## 1. Estado actual (punto de partida)

| Módulo | Función |
| --- | --- |
| `main.py` | Entry point. Tiene 4 imports sin uso; el `.bat` no lo usa |
| `interface/desktop_pet.py` | UI Tkinter, animaciones, hilos, orquestación y composición de dependencias |
| `infrastructure/gemini_service.py` | Prompt, HTTP con `urllib`, fallback de modelo, regex de `[EXPR: x]`, parser de `.env` |
| `infrastructure/json_memory_repository.py` | Historial en `data/memoria.json` con escritura atómica |
| `infrastructure/voice_service.py` | TTS con `edge-tts` (`es-AR-ElenaNeural`, +15%) y reproducción con `pygame`; caché de mp3 en `data/voice_cache/` |
| `infrastructure/sound_effects.py` | Tonos procedurales (`hello`, `blip`, `thinking`, `done`, `error`) con `pygame` |
| `application/ports.py` | Protocolos `MemoryRepository` y `Clock` (la UI no los usa; depende de clases concretas) |
| `domain/models.py` | `Mood`, `Topic`, `CheckIn`. Mood y Topic se guardan siempre como `CALM` y `GENERAL` |
| `tests/test_sophia.py` | 19 tests de memoria, `.env` y Gemini. Sin tests de UI, voz ni sonido |

Assets sin usar: `intro-*.webp` (9), `capri*.png`, `capri.ico`, `tray.png`.

---

## Fase 1 — Correcciones (prioridad máxima)

### T1.1 — La voz congela la ventana · `voice_service.py`

- **Problema:** `_play` mantiene `self._lock` durante toda la reproducción y `stop()` pide ese mismo lock desde el hilo de la UI (`_send`). Al escribir mientras Sophia habla, la ventana se congela hasta que termina el audio.
- **Hacer:** el lock solo protege la inicialización del mixer y las llamadas `load`/`play`. Nunca debe mantenerse durante la espera. Agregar un contador de generación (`self._generation`) que se incrementa en `speak()` y `stop()`. `_speak_sync` lo compara después de generar el mp3 y dentro del bucle de reproducción, y aborta si cambió.
- **Aceptación:** `stop()` vuelve de inmediato aunque haya audio sonando. Un audio cuya generación terminó después de un `stop()` **no** se reproduce. Tests con un backend de audio y un generador TTS falsos inyectados por constructor.

### T1.2 — `pygame` obligatorio en efectos · `sound_effects.py`

- **Problema:** `import pygame` sin protección. Si falta, la app entera falla al importar. `is_available()` chequea `pygame is not None`, que siempre es verdadero.
- **Hacer:** mismo patrón `try/except` que `voice_service.py`, con bandera `_PYGAME_AVAILABLE`, y que `is_available()` la use.
- **Aceptación:** con `pygame` ausente (simulado en test) la app importa y arranca sin sonido.

### T1.3 — Resultado tipado en lugar de errores como texto · `domain`, `gemini_service.py`, `desktop_pet.py`

- **Problema:** `generate_reply` devuelve `(texto, expr)` también para errores. La UI los guarda en memoria, los reenvía a Gemini como turnos `model` y ahora los **lee en voz alta**.
- **Hacer:** crear en `domain/models.py`:

```python
@dataclass(frozen=True)
class Reply:
    text: str
    expression: str = "calm"
    ok: bool = True
    error_code: str | None = None  # "no_key", "invalid_key", "quota", "network", "parse"
```

`generate_reply` devuelve `Reply`. Si `ok` es `False`: mostrar el mensaje en el chat con estilo de error, reproducir el sonido `error`, **no** guardar en memoria y **no** hablar.

- **Aceptación:** tests que verifican que un error no se persiste, no se habla y no entra al historial enviado a Gemini.

### T1.4 — Lock `_busy` y cierre seguro · `desktop_pet.py`

- **Problema:** `_busy.release()` es lo último de `_render`. Si algo falla antes, el chat queda bloqueado para siempre. Cerrar la ventana mientras hay un hilo trabajando puede dar `TclError`.
- **Hacer:** `try/finally` alrededor del cuerpo de `_render`. Agregar bandera `_closing`, handler `WM_DELETE_WINDOW` que cancela los `after` pendientes, y proteger `root.after` en `_process`.
- **Aceptación:** una excepción forzada en `_render` no deja el lock tomado. Cerrar con una respuesta en curso no imprime tracebacks.

### T1.5 — Manejo correcto de errores HTTP y clave en header · `gemini_service.py`

- **Problema:** 400 se trata como "modelo descontinuado" (incluye clave inválida). 429 no prueba el modelo de respaldo ni reintenta. La clave viaja en la URL (`?key=`).
- **Hacer:** enviar la clave en el header que indique la documentación oficial (`x-goog-api-key`) y sacarla de la URL. Mapeo: 404 → probar siguiente modelo; 429 y 5xx → un reintento corto (≈1 s) y luego siguiente modelo; 400/401/403 con clave inválida → `Reply(ok=False, error_code="invalid_key")` con mensaje claro.
- **Aceptación:** tests con `HTTPError` simulados por código; ningún mensaje ni log contiene la clave.

### T1.6 — Memoria dañada · `json_memory_repository.py`, `desktop_pet.py`

- **Problema:** si `memoria.json` se corrompe, `history()` y `save()` fallan; el `except: pass` oculta la pérdida y Sophia queda inutilizable.
- **Hacer:** al detectar JSON inválido, renombrar el archivo a `memoria.corrupta-<timestamp>.json` (cuarentena), empezar con memoria vacía y avisar en el chat. Los errores de `save()` se registran (ver T2.1), no se silencian. Un registro con campos faltantes se omite, no tumba la lectura completa.
- **Aceptación:** tests con archivo corrupto y con un registro incompleto.

### T1.7 — Limpiar el texto antes de hablar · `infrastructure/speech_text.py` (nuevo)

- **Problema:** `speak(reply)` envía el texto tal cual y lee asteriscos, URLs y código.
- **Hacer:** función `clean_for_speech(text: str) -> str`: quita marcas markdown (`*`, `_`, `#`, `` ` ``), reemplaza URLs por "un enlace", bloques de código por "te dejé el código en el chat" y elimina emojis. Se aplica solo al audio; el chat muestra el texto original.
- **Aceptación:** tests con ejemplos de cada caso.

### T1.8 — Estados de la UI · `desktop_pet.py`

- **Hacer:** que "Conectada" dependa de `GeminiService.is_configured` (si no, "⚠️ Sin clave"). Que el clic en el avatar mientras habla o piensa deje el estado coherente (hoy puede quedar en "Hablando…"). Que el clic también dispare el sonido/voz, como el saludo.

### T1.9 — Un solo punto de entrada · `main.py`, `iniciar_sophia_desktop.bat`

- **Hacer:** eliminar los imports sin uso de `main.py` y que el `.bat` ejecute `python main.py`. Mantener `python -m companera.interface.desktop_pet` funcionando mientras no se complete la T3.3.

### T1.10 — Renombrar tests engañosos · `tests/test_sophia.py`

- `test_falls_back_to_calm_for_unknown_expression` prueba ausencia de etiqueta: renombrarlo y agregar uno que pruebe una etiqueta desconocida (`[EXPR: xyz]`).
- `test_topic_migration_defaults_to_general` incluye el campo `topic`: cambiarlo para que realmente omita el campo.

**Cierre de Fase 1:** todos los tests pasan y la app arranca sin clave, sin `pygame` y sin `edge-tts`. Reportar y esperar autorización.

---

## Fase 2 — Fundaciones: logging, configuración y entorno

### T2.1 — Logging · `infrastructure/logging_config.py` (nuevo)

- Usar `logging` con `RotatingFileHandler` en `data/logs/sophia.log` (1 MB × 3 archivos). Reemplazar **todos** los `except: pass` / `except Exception: pass` por `logger.warning/exception` con contexto.
- Nivel INFO por defecto. El texto de las conversaciones solo a nivel DEBUG y desactivado por defecto. Nunca loguear la clave ni URLs con credenciales.
- **Aceptación:** `grep` de `except.*:\s*pass` sin resultados; un fallo de voz deja una línea en el log.

### T2.2 — Configuración central · `infrastructure/settings.py` (nuevo)

- Dataclass `Settings` cargada desde `data/settings.json` (ya ignorada por `.gitignore` al estar en `data/`) con valores por defecto, validación y guardado atómico. El `.env` queda **solo** para secretos.
- Campos iniciales: `voice_enabled`, `voice_name`, `voice_rate`, `voice_pitch`, `volume` (0–1), `sfx_enabled`, `speak_welcome`, `model`, `always_on_top`, `theme`, `avatar_size`, `allowed_folders` (lista, vacía por defecto).
- **Aceptación:** archivo ausente o inválido usa defaults sin fallar; tests de carga, validación y guardado.

### T2.3 — Controles de audio en la barra · `desktop_pet.py`

- Botones 🔊/🔇 (voz), 🔔 (efectos) y ⏹ (callar ahora), más un control de volumen. Los cambios se persisten en `Settings`. El `blip` no suena cuando la voz está activa.

### T2.4 — Dependencias y arranque · `requirements.txt`, `pyproject.toml`, `.bat`

- Fijar rangos de `edge-tts` y `pygame-ce` según las **versiones instaladas** (`pip show`), igual que Pillow. Crear `requirements-dev.txt` (`ruff`, `mypy`) y `pyproject.toml` con `requires-python = ">=3.10"` y la configuración de ruff/mypy.
- El `.bat` crea `.venv` si no existe, instala `requirements.txt` y ejecuta `main.py`.

### T2.5 — Limpieza de `voice_cache` · `voice_service.py`

- Al iniciar, borrar mp3 con más de 14 días y, si la carpeta supera 100 MB, los más antiguos hasta bajar del límite. Ambos valores van en `Settings`. Opción para desactivar la caché.

### T2.6 — Documentación

- Actualizar `README_sophia_mente.md` (hoy dice que solo requiere Pillow) y `CONTEXTO_PROYECTO_SOPHIA.md` (la voz ya no es idea futura; estructura y dependencias nuevas). Crear `CHANGELOG.md` y subir la versión a v0.3 al cerrar la Fase 6.

### T2.7 — Tests de voz y sonido

- Inyectar por constructor el generador TTS y el backend de audio para poder probar con fakes. Cubrir caché, cancelación, `clean_for_speech` y la degradación sin dependencias.

**Cierre de Fase 2:** reportar y esperar autorización.

---

## Fase 3 — Arquitectura (prerrequisito de la IA avanzada)

### T3.1 — Puertos nuevos · `application/ports.py`

- Agregar `LanguageModel` (generar una respuesta a partir de historial, mensaje y system prompt, devolviendo `Reply`), `Speaker` (`speak`, `stop`, `is_speaking`) y `SoundPlayer` (`play`, `stop`). Implementarlos con `GeminiService`, `VoiceService` y `SoundEffectService`, más `NullSpeaker` y `NullSoundPlayer` para cuando no estén disponibles.

### T3.2 — `ChatService` · `application/chat_service.py` (nuevo)

- Orquesta: leer historial → pedir respuesta al `LanguageModel` → persistir solo si `ok` → devolver `Reply`. No conoce Tkinter ni `pygame`. Recibe `MemoryRepository`, `Clock` y `LanguageModel` por constructor.
- **Aceptación:** tests del flujo completo con fakes, incluyendo error y memoria vacía. `desktop_pet._process` pasa a ser una llamada a `ChatService`.

### T3.3 — Raíz de composición en `main.py`

- `main.py` construye todas las dependencias y se las pasa a `SophiaDesktopApp`. `start_desktop()` se elimina o queda como alias. La UI depende de los puertos, no de las clases concretas.

### T3.4 — Cola de eventos hilo → UI · `desktop_pet.py`

- Reemplazar las llamadas a `root.after` desde hilos secundarios por una `queue.Queue` que el hilo principal consulta periódicamente (cada \~50 ms con `after`). Eventos: respuesta lista, error, fragmento de streaming, voz terminada.
- **Aceptación:** ningún hilo secundario llama a métodos de Tkinter. Es requisito de la T4.2 (streaming) y de la T5.5 (bandeja).

### T3.5 — Dividir la UI solo si hace falta

- Si `desktop_pet.py` supera \~400 líneas tras las Fases 4–5, separar en `avatar_animator.py` (sprites y animación) y `chat_view.py` (chat, burbujas, markdown). No hacerlo antes.

**Cierre de Fase 3:** la app se comporta igual que antes pero con la UI desacoplada. Reportar y esperar autorización.

---

## Fase 4 — Funcionalidades de IA

Requiere completas las Fases 1 a 3. Antes de cada tarea, consultar la documentación oficial de Gemini para los campos exactos de `generationConfig`, `responseSchema`, streaming y function calling.

### T4.1 — Respuestas estructuradas · `gemini_service.py`, `domain/models.py`

- **Hacer:** pedir salida JSON (`responseMimeType` + `responseSchema`) con los campos `text`, `expression` (enum de las 7 expresiones), `mood` (enum `Mood`), `topic` (enum `Topic`) y `facts` (lista opcional de frases cortas, ver T4.4). Quitar del prompt la instrucción de la etiqueta `[EXPR: x]`.
- **Compatibilidad:** si el JSON viene inválido, intentar el regex anterior y, si tampoco sirve, usar el texto crudo con `calm`.
- **Persistencia:** guardar el `mood` y `topic` reales en `CheckIn` (hoy son siempre `CALM`/`GENERAL`). Al construir el historial para Gemini, enviar solo el texto.
- **Aceptación:** tests con JSON válido, JSON roto, campos faltantes y valores fuera de enum. El catálogo de expresiones queda definido en un único lugar (`domain`) y lo usan el prompt, la validación y la UI.

### T4.2 — Streaming y voz por frases · `gemini_service.py`, `desktop_pet.py`, `voice_service.py`

- **Hacer:** usar el endpoint de streaming de Gemini y mostrar el texto de forma incremental en el chat vía la cola de eventos (T3.4). Un `SentenceSplitter` emite oraciones completas; el `Speaker` las encola y reproduce en orden mientras genera el audio de la siguiente.
- **Condición:** con salida estructurada (T4.1), definir cómo se transmite el JSON parcial. Si no es viable, hacer streaming solo del campo `text` o mantener el modo no-streaming como alternativa en `Settings`.
- **Aceptación:** el primer audio empieza antes de que termine la respuesta completa; `stop()` corta la cola entera; tests del splitter con abreviaturas, números decimales y puntos suspensivos.

### T4.3 — Voz según emoción · `voice_service.py`

- **Hacer:** tabla `expresión → (rate, pitch, volume)` aplicada sobre los valores base de `Settings` (por ejemplo `laugh` más rápida y aguda, `aside` más pausada). Verificar que `edge-tts` acepta esos parámetros en la versión instalada. Incluirlos en la clave de caché.

### T4.4 — Perfil y memoria de largo plazo · `domain`, `infrastructure/json_profile_repository.py` (nuevo)

- **Hacer:** `UserProfile(facts: list[str], updated_at)` guardado en `data/perfil.json`. Agregar los `facts` que devuelve el modelo (sin duplicados, máximo 50, cada uno de hasta \~120 caracteres) e inyectarlos en el system prompt como bloque "Lo que sabés del usuario".
- **Control del usuario:** comandos `/perfil` (ver), `/olvidar <n>` y `/olvidar todo`. El usuario siempre puede ver y borrar lo que Sophia sabe de él.
- **Resumen del historial (T4.4b, después):** cuando el historial supere \~40 intercambios, resumir los más viejos con una llamada al modelo y guardar el resumen en un campo aparte. La ventana de contexto pasa a ser `resumen + últimos N turnos`.
- **Aceptación:** tests de deduplicación, límite, borrado y construcción del prompt. No guardar datos sensibles (contraseñas, claves, documentos de identidad): filtrarlos y avisar.

### T4.5 — Personalidad en archivo · `companera/persona/sophia.md` (nuevo)

- **Hacer:** mover `SOPHIA_SYSTEM_PROMPT` a un archivo cargado al inicio, con el texto actual como valor de respaldo embebido. El prompt se arma con: persona + perfil (T4.4) + herramientas disponibles (T4.7).

### T4.6 — Comandos de barra · `application/commands.py` (nuevo)

- **Hacer:** si el mensaje empieza con `/`, se interpreta como comando local y **no** se envía al modelo. Iniciales: `/ayuda`, `/mute`, `/callate`, `/perfil`, `/olvidar`, `/limpiar` (borra el historial tras confirmar). Comandos desconocidos responden con la lista disponible.

### T4.7 — Herramientas (function calling) · `application/tools.py` (nuevo)

- **Diseño:** protocolo `Tool` (nombre, descripción, esquema de parámetros, nivel de permiso `SAFE` o `CONFIRM`, `run()`) y un `ToolRegistry`. El bucle de la conversación admite **como máximo 3 llamadas a herramientas por turno**.
- **Herramientas iniciales:**
  - `get_datetime` (`SAFE`).
  - `set_timer(minutes, label)` (`SAFE`): al vencer suena el efecto `done` y Sophia avisa.
  - `take_note(text)` (`SAFE`): agrega a `data/notas.md`.
  - `open_url(url)` (`CONFIRM`): solo `http`/`https`, con diálogo de confirmación que muestra la URL completa.
  - `read_text_file(path)` (`CONFIRM`): solo dentro de `allowed_folders` de `Settings` (vacío por defecto), tamaño máximo 50 KB, extensiones de texto, y **nunca** `.env`. Resolver la ruta real y rechazar cualquier intento de salir de la carpeta permitida (`..`, enlaces simbólicos).
- **Prohibido:** ejecutar comandos de shell, escribir fuera de `data/`, borrar archivos, acceder a la red desde una herramienta.
- **Seguridad:** el contenido que devuelve una herramienta (por ejemplo un archivo leído) es **dato, no instrucciones**; el prompt debe indicarlo. Cada ejecución queda en el log (T2.1) con nombre y argumentos.
- **Aceptación:** tests de permisos, de path traversal, del límite de 3 llamadas y de rechazo cuando el usuario no confirma.

### T4.8 — Proactividad · `application/` + `desktop_pet.py`

- **Hacer:** saludo inicial según la hora (`Clock`) y cuánto pasó desde la última charla (`latest()`). Modo "sleepy" (cara y estado) tras N minutos sin actividad, configurable. Todo respeta mute y no repite el saludo hablado si `speak_welcome` es falso.

### T4.9 — "Mirá mi pantalla" (opcional, requiere aprobación explícita) · `/pantalla`

- **Hacer:** captura con `PIL.ImageGrab` solo cuando el usuario lo pide (comando o botón), con indicación visible y confirmación. La imagen se envía a Gemini como dato en línea y **nunca se guarda en disco**. Aclarar en la UI que la imagen sale hacia Google.

### T4.10 — Entrada por voz (futuro, solo especificación)

- **No implementar sin aprobación.** Presentar primero una propuesta: push-to-talk, reconocimiento local (por ejemplo Whisper/faster-whisper), costo en dependencias y tamaño de modelo, y el efecto sobre la privacidad.

**Cierre de Fase 4:** reportar y esperar autorización.

---

## Fase 5 — Aspecto visual

### T5.1 — Nitidez en pantallas de alta densidad · `main.py`

- **Hacer:** en Windows, antes de crear `Tk()`, llamar a `ctypes.windll.shcore.SetProcessDpiAwareness(1)` dentro de `try/except` con log. Verificar que el avatar y las fuentes no queden desproporcionados.

### T5.2 — Ícono y título · `desktop_pet.py`

- **Hacer:** `iconbitmap` con `capri.ico` (con fallback si falta el archivo).

### T5.3 — Modo mascota: ventana sin borde y transparente · `desktop_pet.py`

- **Hacer:** `overrideredirect(True)` y color transparente (`-transparentcolor` en Windows) para que el avatar flote sobre el escritorio. Evaluar `capri-cutout.png` y los sprites `face-*`/`cutin-*` con fondo transparente. Arrastre desde el propio avatar y menú contextual (clic derecho): mute, siempre encima, mostrar/ocultar chat, modo mascota/modo chat, salir.
- **Cuidado:** los bordes suavizados (antialiasing) dejan un halo contra el color transparente; componer el sprite sobre ese color o usar un umbral de alfa. Sin barra de título la ventana pierde el botón de la barra de tareas, así que esta tarea **depende de la T5.5** (bandeja).
- **Aceptación:** el modo se elige en `Settings`; el modo chat actual sigue funcionando sin cambios.

### T5.4 — Burbuja de diálogo · `desktop_pet.py`

- **Hacer:** `Toplevel` sin borde junto al avatar con la última respuesta. Se cierra sola tras un tiempo proporcional al largo del texto, o con un clic. Debe reposicionarse si el avatar se arrastra o está cerca del borde de la pantalla (incluida la segunda pantalla).

### T5.5 — Bandeja del sistema · `interface/tray.py` (nuevo)

- **Dependencia permitida:** `pystray`. Usa `tray.png`. Menú: mostrar/ocultar, mute, salir. Al cerrar la ventana, opción de minimizar a la bandeja (en `Settings`).
- **Hilos:** `pystray` corre en su propio hilo; toda comunicación con la UI pasa por la cola de eventos (T3.4).

### T5.6 — Intro animada · `desktop_pet.py`

- **Antes de implementar:** **abrir y mirar los 9 archivos `intro-*.webp`** y proponer el orden y la duración de los frames. Los nombres sugieren `wave1-3`, `mouth1-3`, `happy`, `grab` y `smear`, pero no asumir qué muestran. Esperar confirmación del orden.
- **Hacer:** cargar los frames con Pillow (los `.webp` pueden ser animados; verificarlo), reproducirlos al iniciar junto con el sonido `hello`, y permitir saltarla y desactivarla en `Settings`.

### T5.7 — Animación atada al audio real · `desktop_pet.py`

- **Hacer:** hoy "hablando" dura `caracteres × 38 ms` (entre 1,8 y 7 s). Con voz activa debe durar mientras `Speaker.is_speaking()`; sin voz se mantiene el cálculo actual. Si, tras mirar los frames (T5.6), `intro-mouth1-3` sirven como bocas, evaluar alternarlas al ritmo del habla. Es una alternancia temporal simple, **no** análisis de audio.

### T5.8 — Vida en reposo · `avatar_animator.py`

- **Hacer:** variación aleatoria cada 4–9 s entre expresiones cercanas (parpadeo si los sprites lo permiten), leve movimiento vertical de 1–2 px y fundido corto entre expresiones con frames precalculados (`Image.blend`) y cacheados. Desactivable en `Settings`.

### T5.9 — Chat más legible · `chat_view.py`

- **Hacer, con tags de `tk.Text` y sin dependencias nuevas:** burbujas diferenciadas (márgenes y fondo por hablante), markdown mínimo (negrita, `código` y bloques), hora de cada mensaje, indicador animado "escribiendo…" y clic derecho → copiar.
- **Opcional, solo con aprobación:** evaluar `customtkinter` si el resultado con Tk puro no alcanza.

### T5.10 — Temas y tamaños · `interface/theme.py` (nuevo)

- **Hacer:** dataclass `Theme` con todos los colores que hoy están fijos en el código (`#0f111a`, `#161a29`, `#00f0ff`, etc.). Temas `oscuro` (por defecto), `claro` y color de acento configurable. Tamaño del avatar 120/160/220 px desde `Settings`.

### T5.11 — Sonido coherente

- **Hacer:** conectar `done` (fin de respuesta, temporizadores) y `error` (T1.3); evitar que `thinking` y `blip` se pisen con la voz; respetar el volumen global de `Settings`.

**Cierre de Fase 5:** capturas de pantalla de cada modo (chat, mascota, tema claro y oscuro) en el reporte. Esperar autorización.

---

## Fase 6 — Empaquetado y calidad

### T6.1 — Ejecutable · `Sophia.spec` (nuevo)

- **Hacer:** empaquetar con PyInstaller (`--onedir`, sin consola) incluyendo `companera/assets/` y el ícono. Agregar `build/` y `dist/` al `.gitignore`. Probar que arranca sin Python instalado y que `data/` se crea junto al ejecutable (no dentro del paquete temporal).

### T6.2 — Inicio con Windows (opt-in) · `Settings`

- **Hacer:** opción "Iniciar con Windows" que crea o borra un acceso directo en la carpeta Inicio del usuario. Desactivada por defecto y reversible desde la propia app.

### T6.3 — Integración continua (solo si el repo está en GitHub)

- **Hacer:** workflow en Windows que corre `ruff`, `mypy` y `unittest`. Las pruebas no deben requerir audio ni pantalla (variables `SDL_AUDIODRIVER=dummy` y omitir lo que necesite Tk).

### T6.4 — Cierre de versión

- **Hacer:** actualizar README, `CONTEXTO_PROYECTO_SOPHIA.md` y `CHANGELOG.md`; versión **v0.3**; correr la lista de verificación siguiente.

---

## Criterios de terminado (para todo el plan)

- `python -m unittest discover -s tests -v` pasa completo; `ruff` y `mypy` no reportan errores nuevos.
- La app arranca y se comporta bien **sin clave**, **sin `pygame`**, **sin `edge-tts`** y **sin internet** (degrada con mensajes claros).
- No quedan `except: pass` sin log. La clave no aparece en logs, URLs ni mensajes.
- Ningún hilo secundario toca widgets de Tkinter.
- `stop()` y el botón ⏹ cortan la voz de inmediato en cualquier estado.
- Las herramientas respetan permisos, confirmaciones y `allowed_folders`.
- La documentación coincide con el código.

## Riesgos y notas

- **APIs que cambian:** los modelos de Gemini usados son versiones *preview* y pueden retirarse; los nombres de campos de este plan hay que verificarlos en la documentación vigente.
- **`edge-tts` no es una API oficial de Microsoft:** puede cambiar o dejar de funcionar sin aviso. Por eso la voz debe degradar sin romper la app, y el puerto `Speaker` deja abierta la puerta a otro motor de voz.
- **Privacidad:** cada mensaje sale hacia Google (Gemini) y cada respuesta hablada hacia el servicio de voz de Microsoft. Las capturas de pantalla, los archivos leídos y el perfil del usuario son datos sensibles: siempre opt-in, visibles y borrables.
- **Solo Windows:** transparencia, DPI, bandeja e inicio automático están pensados para Windows. Aislar el código específico de plataforma detrás de funciones pequeñas con respaldo.
- **Orden de dependencias:** T3.4 (cola de eventos) es requisito de T4.2 y T5.5; T5.5 es requisito de T5.3; T4.1 antes de T4.4.
