# Correcciones del Plan 3: gestor de modelos y medidor de uso

*Preparado el 30/10/2026 tras revisar el código contra el informe del agente y la auditoría. Cada punto cita una causa verificada en el código.*

## 0. Resumen

| ID | Problema | Gravedad | Archivos |
| --- | --- | --- | --- |
| X1 | `/screen` libera dos veces `_busy` y corta el polling: la app deja de mostrar respuestas | Crítica | `desktop_pet.py` |
| X2 | `/screen` rechazado con Gemini porque `supports_vision` es `false` | Alta | `profile_store.py`, `gemini_client.py`, `models.json` |
| X3 | `is_configured` se usa sin llamar: siempre muestra «Conectada» | Alta | `ports.py`, `desktop_pet.py` |
| X4 | Un error de red bloquea el perfil 60 s y los mensajes de error engañan | Alta | `model_router.py`, `quota.py` |
| X5 | El router inventa tokens con `len/4` | Alta | `model_router.py`, `desktop_pet.py` |
| X6 | `/model` y el medidor no llegan a la terminal flotante | Alta | `terminal_window.py`, `desktop_pet.py` |
| X7 | La línea de uso está debajo del prompt y se repite en la de estado | Media | `terminal_view.py` |
| X8 | Restos rotos: `start_desktop()` y `GeminiService` sin uso | Media | `desktop_pet.py`, `main.py`, `secrets.py`, `profile_store.py` |
| R1 | Se perdió el respaldo entre modelos de Gemini y falta el aviso «↪ respondió X» | Media | `profile_store.py`, `model_router.py`, `desktop_pet.py`, `settings.py` |
| R2 | La UI usa miembros privados del router | Media | `model_router.py`, `desktop_pet.py` |
| R3 | Los perfiles por defecto reaparecen aunque se borren | Baja | `profile_store.py` |
| R4 | La zona de reinicio se decide por el prefijo del id | Baja | `usage_tracker.py` |
| R5 | Mensajes de comandos en inglés y `/model <id>` pierde mayúsculas | Baja | `commands.py` |
| R6 | Texto corrupto y código torpe | Baja | `openai_compat_client.py` |
| R7 | El router no tiene tests | Alta | `tests/` |

## 1. Reglas de trabajo

- Una tarea por vez, un commit por tarea (`fix:`, `refactor:`, `test:`). Sin `git push`.
- Leer cada archivo completo antes de editarlo. Tocar solo lo que nombra la tarea.
- No leer ni imprimir `.env`, `data/memoria.json` ni `data/voice_cache/`. Ninguna clave en logs, mensajes, archivos ni tests.
- **Cada tarea se cierra con evidencia:** el nombre del test que pasa o el paso manual probado con su resultado. Sin evidencia, no se marca como hecha.
- Los tests no dependen del entorno real: aislar variables como `GEMINI_API_KEY` (clave falsa o `SecretStore` falso) para que el resultado no cambie según la PC.
- Correr `python -m unittest discover -s tests -v` antes de cada commit.
- Si una tarea falla dos veces, parar y reportar qué se probó.

## 2. Fase 1: bloqueantes

**X1 — `/screen` y el lock `_busy`** · `interface/desktop_pet.py`

*Causa:* `_submit_text` hace `acquire`, ejecuta `_run_command` y siempre hace `release`. En `/screen` el hilo de captura sigue vivo y su respuesta llega a `_render`, cuyo `finally` vuelve a hacer `release()` sobre un lock ya liberado. Eso lanza `RuntimeError`, que escapa de `_poll_events`; como el `after(50)` está al final, el polling se corta y la app no vuelve a mostrar respuestas. Si el usuario escribió mientras tanto, ese `release` además libera el lock de otro pedido.

*Cambio:*

- `_run_command` devuelve `True` solo si dejó trabajo asíncrono corriendo (el hilo de captura) y `False` en todo lo demás. `_submit_text` libera `_busy` únicamente si devuelve `False`.
- Mientras corre el análisis de pantalla, la UI muestra el estado de «pensando» igual que con un mensaje normal.
- En `_render`, el `finally` libera solo si `self._busy.locked()`.
- En `_poll_events`, cada evento se procesa dentro de `try/except Exception` con `logger.exception`, y `after(50, ...)` se reprograma en un `finally`. Un error en un evento nunca debe cortar el polling.

*Listo cuando:* (a) `/screen` y cancelar, (b) `/screen` y aceptar, (c) un mensaje normal después: en los tres casos la app sigue respondiendo. También, escribir un mensaje mientras se analiza la pantalla no rompe nada. *Test:* extraer `release_if_locked(lock)` a una función pequeña y probar que con el lock ya liberado no lanza error.

**X2 — `/screen` con Gemini** · `profile_store.py`, `gemini_client.py`, `data/models.json`

*Causa:* `models.json` tiene `supports_vision: false` en `gemini-lite` y `default_profiles` no lo activa, así que `analyze_screen` siempre responde «Este modelo no puede ver imágenes». Además `ProfileStore.load` nunca actualiza perfiles ya guardados. Por otro lado, `GeminiClient.complete` agrega la imagen como un turno de usuario aparte, con un texto fijo, separado de la pregunta.

*Cambio:*

- `default_profiles`: `gemini-lite` con `supports_vision=True`.
- `ProfileStore`: agregar `schema_version` al archivo (valor actual: 2) y una migración: si falta o es menor a 2, poner `supports_vision=True` en todos los perfiles `kind == gemini`, subir la versión y guardar. R1 y R3 usan esta misma versión.
- `GeminiClient.complete`: si hay `image_b64`, adjuntarla al **último** mensaje del usuario (en el mismo `parts`, imagen más texto) en lugar de agregar un turno nuevo con texto fijo.

*Listo cuando:* con la clave de Gemini, `/screen` → confirmación → respuesta. Con `groq-free` activo, rechaza sin capturar. *Tests:* migración de un `models.json` viejo (sin `schema_version`); el payload de `GeminiClient` con imagen (usando un `post` falso) lleva la imagen y el texto en el mismo `content`.

**X3 — `is_configured`** · `application/ports.py`, `interface/desktop_pet.py`

*Causa:* `getattr(self._model, 'is_configured', False)` devuelve el **método** sin llamarlo, y un método siempre es verdadero. Aparece en `_build_ui` y en `_stop_speech`. Resultado: siempre «Conectada», incluso sin clave.

*Cambio:* agregar `is_configured(self) -> bool` al protocolo `LanguageModel`; en la UI llamar `self._model.is_configured()` y eliminar los `getattr`. Actualizar los fakes de los tests para que lo implementen.

*Listo cuando:* sin clave arranca en «⚠️ Sin clave»; con clave, en «🟢 Conectada». *Test:* `ModelRouter.is_configured()` con y sin clave (con `SecretStore` falso).

**X4 — Bloqueos y mensajes de error** · `application/model_router.py`, `application/quota.py`

*Causa:* en `generate_reply`, cualquier excepción cae en `code = getattr(err, 'code', 'network')`, y si el código es `server` o `network` se llama a `QuotaState.mark` con `classify_quota('')` (tipo `unknown`, 60 s). Así, un corte de internet, un error de programación o un 5xx bloquean el perfil: aunque vuelva la conexión, el router lo saltea y devuelve «No pude conectar» sin intentar. Cuando el perfil activo está bloqueado y no hay fallback, el mensaje también dice «network» en vez de «sin cupo».

*Cambio:*

- Marcar bloqueo **solo** para `quota`, `quota_minute` y `quota_day`. `server` y `network` no bloquean (con fallback activo, siguen pasando al siguiente perfil).
- Una excepción que no sea `ProviderError` se registra con `logger.exception` y devuelve un error nuevo `unexpected` («Algo salió mal con {perfil}. Revisá el log.»). No bloquea ni se confunde con red.
- `QuotaState` guarda también el tipo: agregar `blocked_info(profile_id, now) -> BlockInfo(until, kind) | None` (se mantiene `blocked_until`).
- Si el perfil activo está bloqueado y no hay otro candidato, devolver `quota_day` o `quota_minute` con la hora de regreso en hora local de la PC (por ejemplo, «Gemini Flash-Lite llegó al límite diario. Vuelve \~04:00») o los segundos restantes.
- El presupuesto de 40 s usa `time.monotonic()`, no `time.time()`.
- Eliminar el bloque `if pid != active.id: reply = Reply(...)`, que reconstruye el mismo `Reply` sin cambiar nada.
- Si `classify_quota` devuelve `unknown`, registrar con `logger.warning` el cuerpo del error recortado a 500 caracteres (nunca headers ni claves) para poder afinar el clasificador con un 429 real.

*Listo cuando:* desconectar internet, enviar un mensaje, reconectar y enviar otro: el segundo se responde sin esperar 60 s. *Tests (con clientes falsos, ver R7):* error de red no bloquea; `quota_day` del activo sin fallback devuelve el mensaje de límite diario; excepción inesperada devuelve `unexpected` y no bloquea.

**X5 — No inventar tokens** · `application/model_router.py`, `interface/desktop_pet.py`

*Causa:* si `usage.total <= 0`, `generate_reply` y `analyze_screen` estiman `len(texto) // 4` y lo registran como si fuera real. El plan prohibía estimar.

*Cambio:* quitar la estimación. Si el proveedor no informa uso, registrar el pedido con `TokenUsage()` (0 tokens). En `_refresh_model_usage`, si `today.requests > 0` y `today.total == 0`, mostrar solo `hoy: N pedidos` (sin números de tokens).

*Listo cuando:* con un cliente falso que devuelve `TokenUsage()`, `uso.json` cuenta el pedido con 0 tokens y la línea no muestra tokens. *Test:* `UsageTracker` y router con uso en cero.

**X6 — La terminal flotante no se entera** · `interface/terminal_window.py`, `interface/desktop_pet.py`

*Causa:* `_refresh_model_usage` solo actualiza `self._main_terminal`, que está oculta en modo mascota. `TerminalWindow` crea su propia `TerminalView` con `settings.model` fijo. En modo mascota ni se ve la línea de uso ni cambia «Sophia · modelo · proveedor» al usar `/model`.

*Cambio:*

- `TerminalWindow.set_model_label(label, provider)` y `TerminalWindow.set_usage(text, state)`: reenvían a `self.view` y **guardan el último valor**; `open()` los aplica a la vista recién creada.
- `_refresh_model_usage` actualiza las dos terminales (`_main_terminal` y `_pet_chat`).
- El texto inicial de la línea de estado usa la etiqueta del perfil activo, no `settings.model`.

*Listo cuando:* en modo mascota, abrir la terminal muestra el modelo y el uso actuales; tras `/model`, la línea cambia sin cerrar ni reabrir; cerrar y reabrir mantiene los valores.

**X7 — Posición y duplicado de la línea de uso** · `interface/terminal_view.py`

*Causa:* `usage_label` se empaqueta antes que `prompt_wrap`, así que queda entre el prompt y el pie. Lo pedido era **arriba** del campo de texto. Además `set_usage` también agrega el texto a la línea de estado y la pinta de rojo.

*Cambio:* el orden de `pack` (de abajo hacia arriba) pasa a ser: `footer`, `prompt_wrap`, `usage_label`, `scrollbar`, `log`. `set_usage` solo actualiza `usage_label`; la línea de estado conserva «Sophia · modelo · proveedor» en color tenue.

*Listo cuando:* de arriba hacia abajo se ve: log, línea de uso, prompt, línea de estado, pie. Con el modelo bloqueado, solo la línea de uso se pone roja.

**X8 — Restos rotos** · `interface/desktop_pet.py`, `main.py`, `infrastructure/secrets.py`, `infrastructure/profile_store.py`

*Causa:* `start_desktop()` al final de `desktop_pet.py` todavía llama al constructor con `gemini=` y falla con `TypeError`. `main.py` crea un `GeminiService` que no usa. `secrets.py` y `profile_store.py` importan `load_env_file` desde `gemini_service.py` (código viejo).

*Cambio:*

- Borrar `start_desktop()` y el bloque `if __name__ == '__main__'` de `desktop_pet.py`, junto con sus imports.
- En `main.py`, quitar la variable `gemini` y su import.
- Mover `load_env_file` a `secrets.py` y actualizar `profile_store.py`.
- **Antes de borrar `gemini_service.py`**, buscar en todo el proyecto (código y tests) las referencias a `gemini_service`, `GeminiService` y `SOPHIA_SYSTEM_PROMPT`, y mover lo que siga usándose. Si `prompt_builder.py` o un test las usan, migrarlas primero. Recien después eliminar el archivo.

*Listo cuando:* `python main.py` arranca, los tests pasan y una búsqueda de `gemini_service` no devuelve resultados.

## 3. Fase 2: resiliencia y limpieza

**R1 — Respaldo entre modelos de Gemini y aviso «↪»** · `profile_store.py`, `model_router.py`, `settings.py`, `desktop_pet.py`

*Causa:* antes se probaba `gemini-3-flash-preview` si el primer modelo daba 429 (el cupo es por modelo). Hoy `fallback_chain` trae solo `gemini-lite`, así que activar `auto_fallback` no hace nada. Además el aviso «↪ X sin cupo · respondió Y» no existe: el único `↪` que se muestra es el de privacidad.

*Cambio:*

- Agregar el perfil `gemini-flash` (`kind` gemini, modelo `gemini-3-flash-preview`, `key_env` `GEMINI_API_KEY`, visión `true`) a los perfiles por defecto y dejar `fallback_chain = [gemini-lite, gemini-flash]`. La migración (`schema_version` 2) lo agrega a los archivos existentes y ajusta la cadena si era `[gemini-lite]`.
- **Reconocimiento por proveedor, no por id:** función `provider_key(profile)` (`gemini` para los de tipo Gemini; el host de `base_url` para los demás). `acknowledged_providers` guarda esas claves. Migrar los ids ya guardados. Un perfil del **mismo proveedor** que el activo se considera permitido sin pedir confirmación.
- Aviso en la UI: en `_render`, si `reply.ok` y `reply.model_label` es distinto de la etiqueta del perfil activo, agregar al historial un mensaje `system`: «↪ {activo} sin cupo · respondió {model\_label}».

*Listo cuando:* con `auto_fallback` activo y `gemini-lite` bloqueado por cupo, responde `gemini-flash` y aparece el aviso; el perfil activo no cambia. *Tests:* ver R7.

**R2 — API pública del router** · `application/model_router.py`, `domain/models.py`, `interface/desktop_pet.py`

*Causa:* la UI llama a `self._router._usage`, `self._router._quota` y `self._router.secrets`, y fija los nombres de proveedor en un diccionario por id (repetido dos veces).

*Cambio:*

- `ModelProfile` gana el campo `provider: str = ''` (nombre para mostrar, por ejemplo «Google Gemini» o «Groq»), que se guarda en `models.json`.
- Nuevos métodos públicos del router: `usage_today(profile_id=None) -> DayUsage`, `blocked_info(profile_id=None) -> BlockInfo | None`, `has_key(profile) -> bool` y `profile_status(profile) -> str` (`activo`, `disponible`, `sin clave`, `local`, `sin cupo`).
- La UI usa solo esos métodos. Se eliminan los diccionarios de nombres y el `__import__('datetime')`.

*Listo cuando:* una búsqueda de `_router._` en `interface/` no devuelve resultados.

**R3 — Perfiles borrados que reaparecen** · `infrastructure/profile_store.py`

*Causa:* `load()` agrega en cada arranque los perfiles por defecto que falten. Si el usuario borra `openrouter-free` de `models.json`, vuelve a aparecer.

*Cambio:* agregar los perfiles por defecto faltantes **solo** cuando `schema_version` del archivo es menor al actual (migración). Después de migrar, respetar lo que haya en el archivo. *Test:* un archivo con versión 2 y un perfil borrado no lo recupera.

**R4 — Zona de reinicio por tipo de perfil** · `infrastructure/usage_tracker.py`, `model_router.py`

*Causa:* `profile_id.startswith('gemini')` decide si se usa el día del Pacífico. Un perfil Gemini con otro id usaría la fecha local.

*Cambio:* `UsageTracker` recibe una función `reset_zone(profile_id) -> 'pacific' | 'local'`; el router la arma a partir de `profile.kind`. *Test:* un perfil de tipo Gemini con id distinto usa el día del Pacífico.

**R5 — Comandos en español y argumentos intactos** · `application/commands.py`

*Causa:* los mensajes están en inglés («Voice muted.», «Closing Sophia…») en una app en español, y `handle_command` pasa todo a minúsculas, así que `/model <id>` pierde las mayúsculas del id.

*Cambio:* traducir todos los `message` y la lista de `/help` al español rioplatense (los nombres de comando y alias no cambian). Solo el comando y las palabras clave (`on`, `off`, `list`, `voice`, `sound`) se comparan en minúsculas; el argumento original se pasa tal cual a `SET_MODEL`. `/model fallback` con un valor que no sea `on` u `off` devuelve un mensaje de uso. *Tests:* mensajes en español; `/model Mi-Perfil` conserva el id; `/model fallback maybe`.

**R6 — Texto corrupto y código torpe** · `infrastructure/openai_compat_client.py`

Reemplazar el texto `payload invÃƒÂ¡lido` por `payload inválido` (guardar el archivo en UTF-8). Armar `api_messages` directamente con el mensaje `system` al principio (hoy crea un primer elemento con la clave `text` y lo pisa después).

**R7 — Tests del router** · `tests/test_model_router.py` (nuevo)

El constructor de `ModelRouter` acepta `clients`, `usage_tracker` y `quota_state`; usarlos con clientes falsos y una carpeta temporal con su propio `models.json`. Reemplazar `router.secrets` por un falso para no depender del entorno.

Casos mínimos:

1. Respuesta correcta: `model_label` y `usage` quedan en el `Reply` y se registra el pedido.
2. Uso en cero: se registra con 0 tokens (sin estimar).
3. Error de red: no bloquea; el segundo intento vuelve a llamar al cliente.
4. `quota_day` del activo sin fallback: devuelve el mensaje de límite diario con la hora.
5. Con `auto_fallback`, cadena de dos perfiles y el segundo del mismo proveedor: responde el segundo.
6. Con `auto_fallback` y un segundo perfil de otro proveedor **no reconocido**: no se usa.
7. `invalid_key` y `bad_request` no disparan fallback.
8. Excepción inesperada: devuelve `unexpected` y no bloquea.
9. `analyze_screen` con un perfil sin visión: rechaza y no llama al cliente.
10. `is_configured()` con y sin clave.

También: `test_missing_active_key_returns_no_key_not_network` debe aislar el entorno para que no dependa de que `GEMINI_API_KEY` esté definida en la PC.

## 4. Orden de ejecución

| Orden | Tareas | Qué se ve al terminar |
| --- | --- | --- |
| 1 | X1, X3 | La app sigue respondiendo tras `/screen`; estado inicial correcto |
| 2 | X2 | `/screen` funciona con Gemini |
| 3 | X4, X5, R7 | Errores honestos, sin bloqueos falsos ni tokens inventados, con tests |
| 4 | X6, X7 | Modelo y uso visibles y arriba del prompt en la terminal flotante |
| 5 | X8 | Proyecto sin restos rotos |
| 6 | R1, R2, R3 | Respaldo entre modelos de Gemini con aviso, y código más limpio |
| 7 | R4, R5, R6 | Detalles |

## 5. Checklist manual

- Sin clave de Gemini: arranca en «⚠️ Sin clave». Con clave: «🟢 Conectada».
- `/screen` y cancelar, `/screen` y aceptar, y después un mensaje normal: la app sigue respondiendo.
- `/screen` con `groq-free` activo: rechaza sin capturar.
- En modo mascota, abrir la terminal: se ven modelo y uso. Cambiar con `/model`: la línea cambia sin cerrar nada.
- La línea de uso está arriba del prompt y no se repite en la línea de estado.
- Desconectar internet, enviar, reconectar y enviar de nuevo: el segundo se responde enseguida.
- Con `auto_fallback` activo y `gemini-lite` bloqueado: responde `gemini-flash` y aparece «↪ … respondió …».
- Borrar un perfil no esencial de `models.json` y reiniciar: no reaparece.
- `uso.json`, `models.json` y los logs no contienen claves ni mensajes.

## 6. Prompt para OpenCode

> Leé este documento y `CONTEXTO_PROYECTO_SOPHIA.md`. Trabajá **solo la Fase 1**, en el orden de la sección 4, una tarea por vez y con un commit por tarea. Antes de editar cada archivo, leelo completo. Tocá únicamente los archivos que nombra la tarea. No leas `.env`, `data/memoria.json` ni `data/voice_cache/`. Nunca escribas una clave en logs, mensajes ni archivos. No agregues dependencias. Corré `python -m unittest discover -s tests -v` antes de cada commit. **No marques una tarea como hecha sin decirme el test que pasa o el paso manual que probaste y su resultado.** Si una tarea falla dos veces, detenete y contame qué probaste. Al terminar la fase, reportá qué cambió, qué archivos tocaste y cómo probarlo. No hagas `git push`.

Para la Fase 2, reemplazá «Fase 1» por «Fase 2».
