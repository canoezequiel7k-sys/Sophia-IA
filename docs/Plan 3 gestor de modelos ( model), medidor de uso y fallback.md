# Plan 3: gestor de modelos (`/model`), medidor de uso y fallback

*Preparado el 30/10/2026 a partir del código actual de `Sophia IA` y de la documentación de límites de la API de Gemini.*

## 0. Qué se construye

1. **`/model`**: elegir con qué IA habla Sophia (Gemini u otros modelos gratuitos).
2. **Línea de uso** sobre el campo de texto: pedidos y tokens de hoy y estado del cupo.
3. **Fallback**: si un modelo se queda sin cupo, pasar al siguiente (opcional, apagado por defecto).

**Decisiones asumidas** (se pueden cambiar):

- Un **único adaptador compatible con OpenAI** cubre a casi todos los proveedores con capa gratuita (Groq, OpenRouter, Mistral, Ollama local, etc.). Los modelos concretos de cada capa gratuita cambian seguido: **no se escriben en el código**, viven en `data/models.json`. Antes de usar un proveedor, confirmar en su documentación la URL base, los límites y si soporta salida JSON.
- **Tokens usados: reales**, tal como los informa la API. **Tokens restantes: no se muestran como número** salvo que el proveedor los informe. La API de Gemini no expone lo que queda; sus límites se miden en pedidos por minuto, tokens por minuto y pedidos por día, por proyecto y por modelo, y solo se ven en AI Studio. En su lugar: pedidos y tokens de hoy, aviso de cupo agotado con hora de regreso y un tope blando opcional que carga el usuario.
- La cuota diaria de Gemini se reinicia a medianoche, hora del Pacífico. Hoy eso es a las 04:00 en Argentina; desde el 1/11/2026, a las 05:00.
- Las claves van **solo en `.env`**. `models.json` guarda el nombre de la variable, nunca la clave.
- El fallback viene **apagado** y solo usa proveedores que el usuario aceptó explícitamente, porque cada proveedor recibe la conversación.

## 1. Hallazgos en el código que condicionan el plan

- `GeminiService` mezcla todo: lectura de `.env`, HTTP, persona, perfil, historial, schema, reintentos y parseo. Hay que separarlo para poder tener más de un proveedor.
- `ChatService` y la app quedan atados a **un** modelo desde `main.py`. Hace falta un enrutador que se pueda cambiar en caliente.
- `generate_screen_reply` no está en el puerto `LanguageModel`; la app lo llama directo sobre `self._gemini`.
- `Reply` no lleva información de uso ni del modelo que respondió.
- Un 429 no se distingue: se reintenta una vez, se pasa al siguiente modelo de Gemini y termina como `quota`, sin saber si fue por minuto o por día. No se lee `usageMetadata`.
- Un HTTP 400 se informa siempre como «clave inválida», aunque sea un error de schema o payload.
- `main.py` siempre pasa `settings.model`, así que `GEMINI_MODEL` del entorno nunca se usa.
- **Los comandos devuelven cadenas técnicas que la UI muestra como si las dijera Sophia** (`MUTE_VOICE`, `EXIT_SOPHIA`, `PROFILE_CLEAR`). Además `/mute voice` no silencia (la app compara contra `/mute`, `/callate` y `/silenciar`), `/exit` no sale y `/forget all` no borra. Agregar `/model` encima de eso empeoraría el problema, por eso es la Fase 0.

## 2. Arquitectura objetivo

```
UI ──► ChatService ──► ModelRouter ──► GeminiClient
                           │          └──► OpenAICompatClient
                           ├─ PromptBuilder (persona + perfil + historial)
                           ├─ ReplyParser (JSON tolerante)
                           ├─ UsageTracker (data/uso.json)
                           └─ QuotaState (cupos agotados)
```

| Archivo (nuevo) | Capa | Rol |
| --- | --- | --- |
| `domain/models.py` (ampliar) | domain | `TokenUsage`, `ModelProfile`, `Reply` ampliado |
| `application/prompt_builder.py` | application | persona, perfil e historial |
| `application/reply_parser.py` | application | JSON tolerante |
| `application/model_router.py` | application | perfil activo, fallback, registro de uso |
| `application/quota.py` | application | clasificar 429 y bloqueos |
| `infrastructure/http_json.py` | infrastructure | único lugar con `urllib` |
| `infrastructure/gemini_client.py` | infrastructure | HTTP de Gemini |
| `infrastructure/openai_compat_client.py` | infrastructure | HTTP compatible con OpenAI |
| `infrastructure/profile_store.py` | infrastructure | `data/models.json` |
| `infrastructure/secrets.py` | infrastructure | claves desde entorno y `.env` |
| `infrastructure/usage_tracker.py` | infrastructure | `data/uso.json` |
| `infrastructure/pacific_time.py` | infrastructure | día y reinicio del cupo |

## 3. Reglas de trabajo

- Una tarea por vez, un commit por tarea (`feat:`, `fix:`, `refactor:`, `test:`). Sin `git push`.
- Leer cada archivo completo antes de editarlo. Tocar solo lo que nombra la tarea.
- **No leer ni imprimir `.env`, `data/memoria.json` ni `data/voice_cache/`.** Nunca poner una clave en logs, mensajes de error, `models.json`, `uso.json` ni tests.
- Sin dependencias nuevas. Todo lo que no sea Tk va con funciones puras y clientes inyectables para testear sin red.
- `python -m unittest discover -s tests -v` antes de cada commit.
- Si una tarea falla dos veces, parar y reportar.
- La app debe seguir funcionando **igual que hoy** con Gemini al terminar cada fase.

## 4. Fase 0: comandos ordenados

**C1 — Resultado tipado** · `application/commands.py`, `interface/desktop_pet.py`

- Crear `CommandAction` (enum): `NONE`, `MUTE_VOICE`, `UNMUTE_VOICE`, `MUTE_SOUND`, `UNMUTE_SOUND`, `CLEAR_HISTORY`, `FORGET_PROFILE`, `POINT`, `SCREEN`, `EXIT`, `OPEN_MODEL_PICKER`, `SET_MODEL`, `TOGGLE_FALLBACK`.
- Crear `CommandResult(message: str, action: CommandAction = NONE, arg: str = '')`.
- `handle_command` devuelve `CommandResult | None`. La UI tiene **un solo** método `_run_command(result)` que ejecuta la acción y muestra `message` solo si no está vacío. Se elimina la comparación de `lowered in (...)` de `_submit_text`.
- `/clear` ejecuta `CLEAR_HISTORY`: la app borra la memoria **y** el historial de la terminal. `handle_command` deja de recibir `memory_clear`.
- Conservar los alias en español (`/limpiar`, `/silenciar`, `/señalar`, `/pantalla`, `/salir`, `/modelo`).
- *Tests:* cada comando produce la acción esperada; alias; comando desconocido. *Listo cuando:* `/mute voice` silencia, `/exit` cierra, `/clear` limpia, y ninguna cadena técnica aparece en el chat.

## 5. Fase 1: núcleo de proveedores (sin cambios visibles)

**P1 — Dominio** · `domain/models.py`

- `TokenUsage(prompt: int = 0, completion: int = 0, total: int = 0)`, inmutable.
- Agregar al final de `Reply`, con valores por defecto: `usage: TokenUsage | None = None` y `model_label: str = ''`.
- `ModelProfile(id, label, kind, model, base_url='', key_env='', supports_json=True, supports_vision=False, timeout=15.0)`. `kind` es `gemini` u `openai_compat`.

**P2 — HTTP único** · `infrastructure/http_json.py` `post_json(url, headers, payload, timeout) -> HttpResponse(status, headers, body)`. Lanza `HttpStatusError(status, body_text, headers)` y `ConnectionFailed`. Es el único lugar con `urllib`. Los clientes reciben la función por parámetro para poder usar una falsa en tests. Los headers nunca se incluyen en mensajes de error ni en logs.

**P3 — Prompt y parser compartidos** · `application/prompt_builder.py`, `application/reply_parser.py` Extraer de `GeminiService.generate_reply`:

- `build_system_prompt(project_root, include_json_instructions)`: persona (`persona/sophia.md`, con `SOPHIA_SYSTEM_PROMPT` de reserva) más los `facts` de `data/perfil.json`. Si `include_json_instructions`, agrega un bloque con las claves y valores permitidos (`VALID_EXPRESSIONS`, `Mood`, `Topic`, targets), generado desde las constantes del dominio para que no se desactualice.
- `build_messages(history, user_message, limit=8) -> list[ChatMessage]` con `ChatMessage(role, text)`; `role` es `user` o `assistant`.
- `parse_reply(raw) -> Reply`: quita cercos de código, toma desde la primera `{` hasta la última `}`, normaliza enums con la lógica actual (`expression` inválida → `calm`, etc.). Si no hay JSON, usa el texto entero con `calm`; conserva el rescate `[EXPR:x]`.
- *Tests:* cercos de código, ruido antes y después, enum inválido, sin JSON, JSON truncado, más de 50 `facts`.

**P4 — Cliente de Gemini** · `infrastructure/gemini_client.py`

- `GeminiClient(profile, secrets, post)` con `complete(system_prompt, messages, image_b64=None) -> RawCompletion(text, usage, finish_reason)`. Lanza `ProviderError(code, retry_after=None, detail='')`, con códigos: `no_key`, `invalid_key`, `bad_request`, `quota_minute`, `quota_day`, `quota`, `server`, `network`, `parse`.
- Mismo payload de hoy (incluido `responseSchema`). La captura de pantalla pasa a ser `complete(..., image_b64=...)`.
- Uso: leer `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`); si falta el total, sumar.
- HTTP 401 y 403 → `invalid_key`. HTTP 400 → `invalid_key` **solo** si el cuerpo habla de clave inválida; si no, `bad_request` y se registra el cuerpo (sin la clave). 429 → ver U3.

**P5 — Cliente compatible con OpenAI** · `infrastructure/openai_compat_client.py`

- POST a `{base_url}/chat/completions` con `Authorization: Bearer <clave>` (sin header si `key_env` está vacío, caso local).
- Cuerpo: `model`, `messages` (system + historial), `temperature`, `max_tokens` y `response_format` con `json_object` **solo** si `supports_json`.
- Texto en `choices[0].message.content`; uso en `usage.prompt_tokens`, `completion_tokens` y `total_tokens`. Mismos códigos de error que P4.
- **Rechazar `base_url` con `http://`** salvo `localhost` y `127.0.0.1`: la clave no debe viajar en claro.

**P6 — Perfiles** · `infrastructure/profile_store.py`, `data/models.json`

```json
{
  "profiles": [
    {"id": "gemini-lite", "label": "Gemini Flash-Lite", "kind": "gemini",
     "model": "gemini-3.1-flash-lite-preview", "key_env": "GEMINI_API_KEY"},
    {"id": "otro", "label": "Mi proveedor", "kind": "openai_compat",
     "base_url": "https://example.com/v1", "model": "<modelo>", "key_env": "MI_CLAVE",
     "supports_json": true, "supports_vision": false}
  ],
  "fallback_chain": ["gemini-lite"]
}
```

- Si el archivo no existe, **generarlo** con los perfiles de hoy: `settings.model` y `FALLBACK_MODELS` como perfiles `gemini`. Así nada cambia para el usuario.
- Validar ids únicos, `kind` válido y `base_url` seguro. Escritura atómica; archivo dañado → perfiles por defecto y log. Nunca guarda claves.

**P7 — Claves** · `infrastructure/secrets.py` `SecretStore.get(name)`: variable de entorno primero, después `.env` (reusar `load_env_file`). `is_set(name)`. El valor `tu_clave_aqui` cuenta como no configurada.

**P8 — Enrutador** · `application/model_router.py`, `main.py`, `desktop_pet.py`

- `ModelRouter` implementa `LanguageModel`: arma prompt y mensajes (P3), llama al cliente del perfil activo, aplica `parse_reply` y devuelve el `Reply` con `usage` y `model_label`. Ante un `ProviderError`, devuelve `Reply(ok=False, error_code=...)` con los mismos textos de hoy.
- Métodos: `active`, `set_active(id)`, `profiles()` y `analyze_screen(...)`.
- `main.py` crea el enrutador y se lo pasa a `ChatService` y a la app. La app lo usa para la captura de pantalla en lugar de `self._gemini`. Respetar `GEMINI_MODEL` si está definido.
- *Tests con clientes falsos:* perfil activo, respuesta con uso, mapeo de errores, captura de pantalla. *Listo cuando:* la app responde igual que antes con Gemini y los tests de P3 a P8 pasan sin red.

## 6. Fase 2: uso y cupos

**U1 — Hora del Pacífico** · `infrastructure/pacific_time.py` Funciones puras: `pacific_offset_hours(utc)`, `pacific_day_key(utc)` (`YYYY-MM-DD`) y `next_pacific_midnight(utc)`. Regla de EE. UU.: horario de verano (UTC−7) desde el segundo domingo de marzo a las 10:00 UTC hasta el primer domingo de noviembre a las 09:00 UTC; el resto del año UTC−8. **No usar `zoneinfo`**: en Windows necesita el paquete `tzdata`. *Tests:* 2026-03-08 09:59 UTC → −8 y 10:00 UTC → −7; 2026-11-01 08:59 UTC → −7 y 09:00 UTC → −8; la clave del día para 2026-10-30 12:00 UTC es `2026-10-30`; `next_pacific_midnight` de ese instante es 2026-10-31 07:00 UTC.

**U2 — Registro de uso** · `infrastructure/usage_tracker.py`, `data/uso.json`

- `record(profile_id, usage, now_utc)` y `today(profile_id, now_utc) -> DayUsage(requests, prompt, completion, total, last_total)`.
- Agrupa por día y por perfil: día del Pacífico para perfiles `gemini` (coincide con el reinicio) y fecha local para el resto. Conserva 30 días. Escritura atómica; archivo dañado → vacío y log.
- Se registra solo cuando la respuesta fue `ok`. Se usa el total que informa el proveedor; **nunca estimar por cantidad de caracteres**. Si el proveedor no informa uso, el pedido cuenta con 0 tokens.
- No guarda texto de mensajes.

**U3 — Cupos** · `application/quota.py`

- `classify_quota(body_text) -> QuotaInfo(kind, retry_after)`: en el texto del error (en minúsculas), `perday`, `per day` o `daily` → `day`; `perminute` o `per minute` → `minute`; `token` → `tokens`; si no, `unknown`. Leer `retryDelay` (por ejemplo `32s`) como segundos.
- `QuotaState.mark(profile_id, info, now_utc)`: `day` bloquea hasta `next_pacific_midnight`; el resto, hasta `now + retry_after` (por defecto 60 s, máximo 120 s). `blocked_until(profile_id, now)`.
- *Tests* con cuerpos de ejemplo escritos a mano. **Tarea de ajuste:** registrar en el log (sin clave) el cuerpo del primer 429 real para afinar el clasificador, porque el formato exacto no está garantizado.

**U4 — Línea de uso** · `interface/terminal_view.py`, `interface/desktop_pet.py`

- Nuevo `Label` entre el log y el prompt, en color tenue, con `set_usage(text, state)` y `state` en `ok`, `warn` o `blocked`. Respetar el orden de `pack` del documento de correcciones (T1).
- Texto normal: `hoy: 38 pedidos · 41,2k tokens · último 1,3k`. Con tope blando: `38/250 pedidos`.
- Bloqueado por día: `Gemini sin cupo (diario) · vuelve ~04:00`, con la hora **local de la PC** (`astimezone()`). Por minuto: `límite por minuto · 18 s`, con cuenta regresiva cada segundo mientras dure.
- Se actualiza después de cada respuesta y al cambiar de modelo.
- `format_tokens` (función pura): `999`, `1,3k`, `41,2k`, `1,2M`. Con tests.

**U5 — Tope blando opcional** · `settings.py` `Settings.usage_soft_limit: int | None = None` (pedidos por día), que el usuario carga mirando AI Studio. Pasa a `warn` desde el 80 %.

## 7. Fase 3: `/model`

**M1 — Selector** · `commands.py`, `desktop_pet.py`, `command_palette.py`, `terminal_view.py`

- `/model` sin argumentos abre el selector, reutilizando `CommandPalette` con una acción por perfil. Cada fila indica su estado: `● Gemini Flash-Lite · activo`, `○ Mi proveedor · sin clave`, `○ … · sin cupo hasta 04:00`, `○ … · local`. `Enter` activa.
- `/model <id>` activa directo. `/model list` imprime la lista en el log. Alias `/modelo`. Agregar `Cambiar modelo` a la paleta `Ctrl+P`.
- Activar guarda `Settings.active_model` (id del perfil) y actualiza la línea `Sophia · {etiqueta} · {proveedor}`, que hoy se arma una sola vez en `TerminalView.__init__`: agregar `set_model_label`. El enrutador cambia de perfil sin reiniciar y sin reconstruir `ChatService`.
- No permitir activar un perfil sin clave: mostrar la variable que falta (por ejemplo `Falta MI_CLAVE en .env`).

**M2 — Aviso de privacidad** · `settings.py`, `terminal_model.py` `Settings.acknowledged_providers: list[str]`. Al activar un proveedor que no está en la lista, pedir confirmación (como hace `/screen`) con un texto como: «Este proveedor recibirá tus mensajes y lo que Sophia sabe de vos. Revisá sus términos: algunos planes gratuitos usan lo que enviás para mejorar sus productos.» Si cancela, no cambia nada. Agregar el rol `system` al historial de la terminal (texto tenue con prefijo `↪`) para estos avisos.

**M3 — `/screen` según capacidades** · `desktop_pet.py` Si el perfil activo no tiene `supports_vision`, responder que no puede ver imágenes y **no capturar**. El diálogo de confirmación deja de decir «Google Gemini» y usa el proveedor que recibirá la imagen. Una captura **nunca** se redirige a otro proveedor por fallback.

**M4 — Alta de modelos** Por ahora, a mano en `data/models.json`; documentarlo con un ejemplo en el README. `/model add` queda para después.

## 8. Fase 4: fallback automático

**F1 — Cadena de respaldo** · `application/model_router.py`

- Si el perfil activo devuelve `quota*`, `server` o `network`, probar el siguiente de `fallback_chain` que (a) tenga clave, (b) no esté bloqueado en `QuotaState` y (c) esté reconocido por el usuario (M2).
- Un solo recorrido, máximo 3 perfiles y 40 s de tiempo total. `invalid_key` y `bad_request` **no** disparan fallback.
- Si responde otro perfil: `Reply.model_label` indica cuál y se agrega el mensaje `system` `↪ Gemini sin cupo · respondió Mi proveedor`.
- El perfil activo **no cambia** solo: cuando se renueva el cupo, vuelve a responder el elegido. Si sigue bloqueado, se saltea sin gastar un pedido.

**F2 — Interruptor** · `settings.py`, `commands.py` `Settings.auto_fallback: bool = False`. `/model fallback on` y `/model fallback off`, más una acción en la paleta.

**F3 — Cupo restante real (opcional)** `RateInfo(remaining_requests, remaining_tokens, reset_seconds)` leído de los headers de límite que mande el proveedor (confirmar en su documentación; suelen llamarse `x-ratelimit-*`). Si existe, la línea de uso agrega `restan 12.300 tokens`. Si no, no se inventa ningún número.

## 9. Orden de ejecución

| Orden | Tareas | Qué se ve al terminar |
| --- | --- | --- |
| 1 | C1 | Comandos que funcionan |
| 2 | P1–P3 | Nada nuevo; base lista y testeada |
| 3 | P4–P8 | Todo igual, ahora sobre el enrutador |
| 4 | U1–U3 | Nada visible; uso y cupos calculados |
| 5 | U4, U5 | Línea de uso sobre el prompt |
| 6 | M1–M4 | `/model` con selector |
| 7 | F1–F3 | Fallback automático |

## 10. Checklist manual

- Borrar `data/models.json` y abrir la app: se genera y responde igual.
- Quitar `GEMINI_API_KEY` del entorno de prueba: mensaje claro y `/model` marca «sin clave».
- Simular un 429 (cliente falso o modelo agotado): línea en rojo con la hora de regreso; con fallback activado, responde el otro modelo y aparece `↪`.
- Cambiar con `/model` sin reiniciar: cambia la línea `Sophia · modelo · proveedor`.
- `/screen` con un modelo sin visión: rechaza sin capturar.
- Cerrar y abrir: los números de hoy siguen.
- `data/uso.json`, `data/models.json` y los logs no contienen claves ni mensajes.

## 11. Riesgos

- **Modelos gratuitos chicos:** JSON flojo y voseo irregular. El parser tolerante y el texto plano de rescate lo cubren, pero la calidad será distinta a Gemini.
- **Los límites y modelos gratuitos cambian:** no hardcodear nombres ni números.
- **El cuerpo de un 429 no tiene formato garantizado:** por eso existe `unknown` con espera de 60 s.
- **Privacidad:** cada proveedor recibe la conversación y los datos del perfil. Por eso el aviso de M2 y el fallback apagado por defecto.
- **Tamaño del cambio:** P1 a P8 en ese orden, cada una con tests; no mezclar tareas.

## 12. Prompt para OpenCode

> Leé este documento y `CONTEXTO_PROYECTO_SOPHIA.md`. Trabajá **solo la Fase 0**, una tarea por vez y con un commit por tarea. Antes de editar cada archivo, leelo completo. Tocá únicamente los archivos que nombra la tarea. No leas `.env`, `data/memoria.json` ni `data/voice_cache/`. Nunca escribas una clave en logs, mensajes ni archivos. No agregues dependencias. Corré `python -m unittest discover -s tests -v` antes de cada commit. Si una tarea falla dos veces, detenete y contame qué probaste. Al terminar la fase, reportá qué cambió, qué archivos tocaste y cómo probarlo. No hagas `git push`.

Para las otras fases, reemplazá «Fase 0» por la que corresponda.
