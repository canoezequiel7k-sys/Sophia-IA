# Plan 2: Terminal estilo OpenCode, «pensando» sin parpadeos e intro animada

*Preparado el 30/10/2026 leyendo el código actual de `Sophia IA`, tus tres capturas y los frames de `assets/sophia/`.*

## 0. Qué querés y qué encontré

**Se queda igual:** la mascota flotante, la burbuja que sale al costado (`SpeechBubble`) y el señalador.

**Cambia:**

1. La terminal de chat pasa a verse y comportarse como la de OpenCode.
2. Mientras Sophia piensa, no se mueve ninguna imagen.
3. En la intro, el retrato de la burbuja reproduce los 9 frames `intro-*.webp` como un saludo.

**Causas reales que encontré en el código:**

- **El parpadeo y la mascota «cuadrada» tienen la misma causa.** `_show_sprite` también escribe en `PetWindow.show_sprite`, así que la mascota deja de ser el recorte `capri-cutout.png` y pasa a ser un cuadrado de 200×200 con fondo (es lo que se ve arriba a la derecha en tus capturas). Encima, `_thinking_anim` cicla 5 imágenes cada 250 ms y `_talking_anim` alterna 2 cada 180 ms.
- **La burbuja tapa la terminal** (captura 1): `SpeechBubble` y `PetChatWindow` llaman a `position_near` con los mismos datos y caen en el mismo lugar.
- **La burbuja nace en una posición por defecto y recién después se mueve**: otro parpadeo.
- **La intro corre sobre `self._avatar`**, que está oculto en modo mascota, en un orden distinto al que pediste, y termina con `_show_sprite("face-calm")`, que vuelve a pisar el recorte.
- **Los frames de intro son 16:9 (\~1456×819)** y la mano que saluda está a la derecha: no entran en el retrato cuadrado de 54 px de la burbuja.
- **`PetChatWindow` duplica el chat principal**, y `_send_pet_text` escribe en un `Entry` oculto para disparar `_send`.
- **`_rest_return` puede devolver la mascota a su lugar anterior** si la arrastrás durante la animación de respiración.
- **`pet_window.py` usa `ctypes.wintypes.RECT` sin importar `ctypes.wintypes`.** Si nadie más lo importó, el error se traga en el `except Exception` y la posición inicial siempre cae al valor de reserva.

## 1. Cómo trabajar con OpenCode (modelo gratuito)

Un modelo gratuito rinde mejor con pasos chicos y verificables. Por eso cada tarea tiene archivo, qué hacer y cuándo está lista.

- **Una tarea por vez** y un commit por tarea (`fix:`, `feat:`, `refactor:`, `test:`). Sin `git push`.
- Tocar **solo los archivos que nombra la tarea**. No leer `.env`, `data/memoria.json` ni `data/voice_cache/`. Sin dependencias nuevas.
- Lo que se pueda, como **funciones puras sin Tk** (así se testean sin abrir ventanas).
- Correr `python -m unittest discover -s tests -v` antes de cada commit.
- Si una tarea falla dos veces, **parar y reportar** qué intentó y qué error vio.
- Ningún hilo secundario toca widgets de Tk: todo pasa por `self._events`.
- Las imágenes de Tk (`PhotoImage`) se guardan siempre en atributos de instancia; si no, desaparecen.

## 2. Fase A — Mascota estable (base de todo)

**A1 — Separar mascota y retrato** · `desktop_pet.py`, `pet_window.py` `_show_sprite` deja de llamar a `PetWindow.show_sprite`. Solo actualiza `self._avatar` (la ventana principal). La mascota en modo flotante muestra **siempre** `capri-cutout.png`. *Listo cuando:* con la app en modo mascota, enviar mensajes y abrir/cerrar la terminal nunca cambia la imagen de la mascota.

**A2 — Estado de la mascota sin cambiar imágenes** · `pet_window.py` Agregar `set_state(state)` con `idle`, `thinking` y `talking`. Solo modifica el movimiento: en `thinking` flotación lenta de ±2 px cada \~1,2 s; en `talking`, igual que `idle`. Ninguna imagen cambia.

**A3 — Corregir la respiración** · `desktop_pet.py` `_rest_breathe` y `_rest_return` mueven la ventana con coordenadas absolutas guardadas. Cambiarlo a un desplazamiento relativo y no ejecutarlo mientras hay un arrastre en curso. *Listo cuando:* arrastrar la mascota justo al respirar no la devuelve al lugar anterior.

**A4 — Métricas de pantalla** · nuevo `interface/screen_metrics.py` Hoy `GetSystemMetrics(76..79)` está copiado en `pet_window.py`, `speech_bubble.py` y `pet_chat.py`. Centralizar en `virtual_screen()` y agregar `monitor_at(x, y)` (con `MonitorFromPoint` y `GetMonitorInfoW`) que devuelve el rectángulo del **monitor donde está esa coordenada**. Agregar `import ctypes.wintypes` en `pet_window.py`. *Por qué:* tu `pet_x` guardado es 3658, o sea segundo monitor; las ventanas deben limitarse a ese monitor y no cruzar al otro.

**A5 — Tests** · `tests/` Test de `monitor_at` con funciones falsas (sin ctypes real) y de que `_show_sprite` no toca la mascota.

## 3. Fase B — «Pensando» sin parpadeos

**B1 — Burbuja de pensando** · `speech_bubble.py` Nuevo `show_thinking(portrait)`: se abre al enviar el mensaje con el retrato fijo `face-look`, «SOPHIA», la pill `PENSANDO` y tres puntos que rotan `●○○ → ○●○ → ○○●` cada 350 ms. Lo único que se mueve son los puntos.

**B2 — Crear oculta, posicionar y recién mostrar** · `speech_bubble.py` En `show()` y `show_thinking()`: `withdraw()` al crear, dibujar, calcular posición y recién ahí `deiconify()`. Esto elimina el salto de posición.

**B3 — Reutilizar la ventana al responder** · `speech_bubble.py` Nuevo `update_content(title, body, expression, portrait)`: cuando llega la respuesta, la burbuja de pensando se transforma en la definitiva (cambia texto y alto) sin destruir y crear otra.

**B4 — Borrar la animación vieja** · `desktop_pet.py` Eliminar `_thinking_anim`, `_talking_anim`, `_THINKING_FRAMES`, `_TALKING_BASE_FRAMES` y `_start_anim` si queda sin uso. `HABLANDO` solo cambia el texto de la pill.

*Listo cuando:* durante 5 segundos de espera no cambia ninguna imagen; solo se mueven los puntos, y al responder la burbuja no desaparece ni salta.

## 4. Fase C — Intro animada en la burbuja

Los 9 frames existen en `assets/sophia/`. En este orden: **grab, happy, mouth1, mouth2, mouth3, smear, wave1, wave2, wave3**.

**C1 — Secuencia y tiempos** · nuevo `interface/intro_sequence.py`

```python
INTRO_SEQUENCE = (
    ("intro-grab", 140), ("intro-happy", 200),
    ("intro-mouth1", 110), ("intro-mouth2", 110), ("intro-mouth3", 110),
    ("intro-smear", 90),
    ("intro-wave1", 160), ("intro-wave2", 160), ("intro-wave3", 260),
)
```

Suma \~1,3 s. Los milisegundos son un punto de partida: `smear` es un cuadro de transición, por eso dura poco. El último frame se queda fijo hasta que la burbuja se cierra.

**C2 — Carga de frames** · `intro_sequence.py` `load_intro_frames(assets_dir, width=224)` abre cada `.webp`, toma el frame 0 y lo reduce a 224×126 (16:9). **Compone cada frame sobre el color del panel de la burbuja** (`theme.bubble`) con Pillow, así no depende del alpha de Tk y no queda halo. Si falta un archivo, lo saltea y lo registra en el log. La decodificación (imágenes de \~1456×819) va en un hilo de fondo al iniciar; los `PhotoImage` se crean en el hilo de Tk.

**C3 — Modo intro de la burbuja** · `speech_bubble.py` `show(..., stage_frames=None)`: si recibe frames, reemplaza el retrato de 54 px por un escenario de 224×126 debajo de la cabecera (nombre y pill), y la burbuja pasa a 400 px de ancho. Nuevo `play_stage(frames, on_done=None)` con `after` cancelables; `close()` los cancela todos.

**C4 — Conectar la intro** · `desktop_pet.py` Reemplazar `_play_intro`: ya no toca `self._avatar`. `_welcome` abre la burbuja en modo intro, arranca la secuencia y dispara el sonido `hello` al mismo tiempo. Respetar `show_intro`: si es `false`, burbuja normal con retrato.

**C5 — Tests** · `tests/` El orden exacto de `INTRO_SEQUENCE`, que `load_intro_frames` no falla con un archivo ausente (carpeta temporal) y que todos los frames salen del mismo tamaño.

*Listo cuando:* al abrir la app, la burbuja de bienvenida reproduce el saludo completo en orden y queda en `wave3`.

## 5. Fase D — Terminal estilo OpenCode

**Equivalencias con tu referencia:**

| OpenCode | Sophia |
| --- | --- |
| Mensaje del usuario en bloque con barra lateral | Bloque con fondo `#15151d` y barra `▎` violeta en cada línea |
| Respuesta en texto plano, con código y tablas coloreados | Cabecera tenue `◆ Sophia · 21:07` y texto con markdown mínimo (negrita, `código`, viñetas, bloques) |
| Caja de entrada con barra azul a la izquierda | Prompt multilínea con barra violeta y placeholder |
| `Build · modelo · proveedor` bajo el prompt | `Sophia · gemini-3.1-flash-lite-preview · Gemini` y, a la derecha, `● ONLINE` / `PENSANDO` / `HABLANDO` |
| Pie `~/ruta:rama` … `ctrl+p commands` | `~/Documents/Sophia IA` … `ctrl+p comandos` |
| «Jump to latest ↓» | «Ir al final ↓» |
| Paleta con ctrl+p | Paleta de comandos |

**Decisión asumida:** la terminal guarda cada respuesta completa (historial y copiado) y además aparece la burbuja al lado de la mascota. Si preferís burbuja sola, se puede ocultar el texto de Sophia del log.

**D1 — Tema y fuente** · `theme.py` Agregar `TerminalTheme` (solo oscuro por ahora) y `terminal_font(root)`, que usa «Cascadia Mono» si está en `font.families()` y si no «Consolas».

| Elemento | Color |
| --- | --- |
| Fondo | `#0b0b10` |
| Superficie (bloque usuario, prompt) | `#15151d` |
| Borde | `#2a2440` |
| Texto | `#e6e6ef` |
| Texto tenue | `#7a7a8c` |
| Acento / barra | `#7c3aed` |
| Acento claro | `#a78bfa` |
| Sophia | `#00f0ff` |
| Error | `#ff6b81` |
| Código en línea | `#f6ad55` |

**D2 — Render de texto puro** · nuevo `interface/terminal_render.py` Sin Tk. `parse_inline(text)` devuelve tramos `plain`, `bold` o `code`. `wrap(text, columns, prefix)` usa `textwrap` y respeta bloques \`\`\` y viñetas ` -  `. Con fuente monoespaciada, el ancho en caracteres se calcula fácil. *Tests:* negrita, código, bloque, ancho exacto, línea más larga que el ancho.

**D3 — `TerminalView`** · nuevo `interface/terminal_view.py` `tk.Frame` con un `Text` de solo lectura. API: `append_user(text)`, `append_sophia(text, error=False)`, `set_thinking(on)`, `set_status(text, color)`, `clear_view()`.

- Como `Text` no dibuja bordes por línea, el bloque de usuario se arma con prefijo ` ▎  ` en cada línea ya ajustada.
- Al cambiar el tamaño, se vuelve a ajustar todo el historial (con 150 ms de espera para no recalcular en cada píxel).
- Máximo 300 mensajes en pantalla.
- Autoscroll solo si ya estabas al final; si no, aparece «Ir al final ↓» (clic o tecla `End`).
- Mientras piensa, una línea al final con spinner `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` cada 90 ms y segundos transcurridos; desaparece al llegar la respuesta.
- `Ctrl+C` copia la selección; clic derecho también.

**D4 — Prompt y línea de estado** · `terminal_view.py` `Text` de 1 a 5 líneas con crecimiento automático, barra izquierda de 3 px, placeholder «Preguntale algo a Sophia…». `Enter` envía, `Shift+Enter` agrega línea, `↑`/`↓` recorren el historial de lo enviado (solo cuando el cursor está en la primera o última línea), `Ctrl+L` limpia la vista (no borra la memoria). Debajo, la línea `Sophia · {settings.model} · Gemini`.

**D5 — Pie** · `terminal_view.py` Izquierda: ruta del proyecto con `~`. Derecha: `ctrl+p comandos`. Ambos en color tenue.

**D6 — Autocompletado de `/`** · `terminal_view.py`, `commands.py` Al escribir `/`, lista flotante sobre el prompt con `commands.COMMANDS` filtrado. `Tab` completa, `Esc` cierra. De paso, limpiar el formato de esa tupla (tiene espacios de más).

**D7 — Paleta `Ctrl+P`** · nuevo `interface/command_palette.py` Lista filtrable por texto con `↑`/`↓`, `Enter` y `Esc`. Acciones iniciales: activar/silenciar voz, efectos on/off, detener voz, limpiar historial (con confirmación), señalar reloj, mirar pantalla (opt-in), mostrar/ocultar terminal, cambiar a modo ventana, salir. Cada acción es un `PaletteAction(label, hint, callback)`. Estas acciones reemplazan los botones de voz y efectos de la ventana vieja.

**D8 — `TerminalWindow`** · nuevo `interface/terminal_window.py` `Toplevel` sin borde con línea de 1 px (`#2a2440`), franja de título propia («sophia — terminal», botones – y ×, arrastre), agarre de tamaño abajo a la derecha, tamaño inicial 640×440 y mínimo 440×300. Guarda posición y tamaño en `Settings` (`terminal_x`, `terminal_y`, `terminal_w`, `terminal_h`). Reemplaza a `PetChatWindow`.

**D9 — Integración y limpieza** · `desktop_pet.py`

- `_append_user` y `_append_sophia` escriben en el `TerminalView` (único log).
- `_send_pet_text` pasa a `submit(text)`, sin `Entry` oculto.
- El modo ventana embebe el mismo `TerminalView`; se eliminan `_chat`, `_entry` y `_controls`.
- Borrar `pet_chat.py` y `chat_view.py`.
- `_send` llama `set_thinking(True)`; `_render` lo apaga.

**D10 — Que nada se tape** · nuevo `interface/layout.py` Función pura `place_bubble(pet, terminal, size, monitor) -> Placement(x, y, tail_x)` y `place_terminal(pet, size, monitor)`, con `Rect(x, y, w, h)` simples y tests sin Tk. Reglas:

1. Terminal a la izquierda de la mascota, base alineada con la de ella, 16 px de separación.
2. Burbuja arriba de la cabeza de la mascota, con la cola apuntando a su centro (`tail_x`). `SpeechBubble` hoy solo tiene dos posiciones fijas de cola; pasar a una cola con posición libre.
3. Si arriba no entra, va del lado opuesto al terminal; si tampoco, la posición más cercana que entre.
4. La burbuja **nunca** intersecta el rectángulo de la terminal.
5. Todo se limita al monitor de `monitor_at` (Fase A4).

**D11 — Opcional** Rama de git leyendo `.git/HEAD` (sin subprocess), zoom de fuente con `Ctrl+rueda`, tablas markdown con `│ ─ ┼`.

*Listo cuando:* la terminal se ve como la de OpenCode, no hay texto superpuesto con la burbuja y se puede usar el chat entero sin tocar el mouse.

## 6. Orden recomendado

| Orden | Fase | Qué ves al terminar | Esfuerzo |
| --- | --- | --- | --- |
| 1 | A | La mascota deja de ser cuadrada y no salta | Bajo |
| 2 | B | Pensando con tres puntos, sin parpadeos | Bajo-medio |
| 3 | C | Saludo animado en la burbuja de bienvenida | Medio |
| 4 | D1–D5 | Terminal con aspecto OpenCode | Alto |
| 5 | D6–D9 | Autocompletado, paleta e integración | Alto |
| 6 | D10 | Burbuja y terminal sin pisarse | Medio |

Hacé A, B y C primero: son rápidos, se ven enseguida y D los necesita.

## 7. Checklist manual

- Enviar 5 mensajes seguidos: la mascota no cambia de imagen en ningún momento.
- Arrastrar la mascota al otro monitor con la terminal abierta: terminal y burbuja la siguen y no cruzan de pantalla.
- Reiniciar la app: ¿recuerda posición y tamaño de la mascota y de la terminal?
- Achicar la terminal al mínimo: ¿se vuelve a ajustar el texto sin cortarse?
- Respuesta larga: la burbuja no se sale de pantalla ni tapa la terminal.
- Con `show_intro` en `false`: burbuja de bienvenida normal.
- Cerrar con `×` de la terminal, con la paleta y con la bandeja: no quedan ventanas fantasma ni timers vivos.

## 8. Riesgos

- **`Text` de Tk no tiene bordes por línea.** La barra `▎` se logra con prefijos y reajuste manual del texto; requiere fuente monoespaciada.
- **Rendimiento del reajuste:** limitar a 300 mensajes y espera de 150 ms al redimensionar.
- **`PhotoImage` y recolector de basura:** guardar siempre las referencias (frames de intro, retratos, spinner).
- **Varios monitores:** nunca usar el escritorio virtual entero para limitar ventanas; usar el monitor de la mascota.
- **Modelo gratuito:** si inventa nombres o toca archivos de más, pedirle que relea la tarea y revisar el diff antes de aceptar.

## 9. Prompt para OpenCode (plantilla por fase)

> Leé `docs/Plan 2` y `CONTEXTO_PROYECTO_SOPHIA.md`. Trabajá **solo la Fase A**, una tarea por vez y con un commit por tarea. Tocá únicamente los archivos que nombra cada tarea. No leas `.env`, `data/memoria.json` ni `data/voice_cache/`. No agregues dependencias. Corré `python -m unittest discover -s tests -v` antes de cada commit. Si una tarea falla dos veces, detenete y contame qué probaste. Al terminar la fase, reportá qué cambió, qué archivos tocaste y cómo probarlo. No hagas `git push`.

Para las otras fases, reemplazá «Fase A» por la que corresponda.
