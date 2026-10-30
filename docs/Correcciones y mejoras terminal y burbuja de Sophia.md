# Correcciones y mejoras: terminal y burbuja de Sophia

*Documento para el agente de código (OpenCode). Basado en el código real al 30/10/2026 y en las dos capturas del usuario.*

## 0. Resumen: qué falla y por qué

| # | Qué se ve | Causa en el código | Archivo |
| --- | --- | --- | --- |
| 1 | Al abrir la terminal no se ve el prompt, el modelo ni el pie; hay que agrandarla | En `TerminalView.__init__` el `Text` del log se empaqueta **antes** que el prompt y el pie, y pide 24 líneas por defecto. En una ventana de 640×440 se queda con todo el alto y lo demás queda en cero | `terminal_view.py` |
| 2 | El texto de la burbuja queda tapado por ENTENDIDO | `show_thinking()` crea una burbuja chica y `update_content()` solo cambia el texto: no recalcula alto, polígono, barra de acento, botón ni cola. Además `show()` usa alturas de línea fijas (16 y 18 px) que fallan con escala de pantalla alta | `speech_bubble.py` |
| 3 | La terminal aparece vacía al abrirla y pierde todo al cerrarla | Cada `open()` crea un `TerminalView` nuevo con historial vacío. El mensaje de bienvenida se escribe cuando la vista todavía no existe | `terminal_window.py`, `terminal_view.py` |
| 4 | Líneas partidas de forma irregular | El ancho se calcula como `winfo_width() / 7.0` (ancho de carácter inventado) y encima el `Text` tiene `wrap=WORD`: el texto se ajusta dos veces | `terminal_view.py` |
| 5 | La hora de todos los mensajes de Sophia cambia a la actual | `datetime.now()` se calcula al **dibujar**, no al recibir el mensaje | `terminal_view.py` |
| 6 | La intro borra el texto de bienvenida | `play_stage()` hace `canvas.delete('all')` y dibuja solo cabecera e imagen | `speech_bubble.py` |
| 7 | Detalles | Scrollbar blanca, pie encima del prompt, `ctrl+p comandos` no alineado a la derecha, `Ctrl+C` bloqueado en el prompt, el log salta al final en cada redibujado | `terminal_view.py` |

**Evidencia en las capturas:** en la primera, la burbuja tiene \~200 px de alto y 7 líneas de texto: es el tamaño de la burbuja de «pensando» (causa 2). En la segunda, la terminal en su tamaño inicial muestra solo el log (causa 1).

## 1. Reglas de trabajo

- Una tarea por vez, un commit por tarea (`fix:`, `feat:`, `refactor:`, `test:`). Sin `git push`.
- **Leer el archivo completo antes de editarlo.** Tocar solo los archivos que nombra la tarea.
- No leer `.env`, `data/memoria.json` ni `data/voice_cache/`. Sin dependencias nuevas.
- La lógica de medidas va en **funciones puras** (sin Tk) para poder testearlas. Los tests que necesiten Tk se saltean si no hay pantalla (`unittest.skipUnless` y `try/except tk.TclError`).
- Correr `python -m unittest discover -s tests -v` antes de cada commit.
- Si una tarea falla dos veces, parar y reportar qué se probó.
- Los `PhotoImage` se guardan en atributos de instancia.

## 2. Fase 1: terminal usable desde el primer segundo

**T1 — Que prompt, estado y pie siempre se vean** · `terminal_view.py`, `terminal_window.py`

El packer reparte el espacio en el orden en que se hace `pack()`. Reordenar las llamadas (no los constructores) de abajo hacia arriba:

```python
footer.pack(side=tk.BOTTOM, fill=tk.X)         # 1.º: borde inferior
prompt_wrap.pack(side=tk.BOTTOM, fill=tk.X)    # 2.º: arriba del pie
self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # 3.º
self.log.pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # último: toma lo que sobra
self.log.configure(height=1)                   # que no pida 24 líneas
```

En `TerminalWindow.open()`:

- Calcular el **alto mínimo real**: franja de título + `prompt_wrap.winfo_reqheight()` + alto del pie + 4 líneas de log + márgenes (hacer `update_idletasks()` antes). Usarlo en `window.minsize(...)`.
- Al restaurar `terminal_w` y `terminal_h`, **limitarlos** a `[mínimo, tamaño del monitor − margen]`. Un valor guardado chico no debe dejar la ventana inutilizable.
- Si `terminal_x` y `terminal_y` guardados no caen dentro de ningún monitor (`monitor_at`), ignorarlos y usar `place_terminal`.
- Tamaño inicial por defecto: 680×460 multiplicado por `ui_scale` (ver B7).

*Listo cuando:* con ventanas de 640×440, 560×360 y el tamaño mínimo, y con escala de Windows al 100, 125 y 150 %, el prompt, la línea `Sophia · modelo · Gemini` y el pie se ven completos. Para reproducirlo: poner `terminal_w: 560` y `terminal_h: 360` en `data/settings.json`. *Test:* con un `Tk` oculto, crear un `TerminalView` de 560×360 y verificar que `prompt_wrap.winfo_y() + prompt_wrap.winfo_height()` no supera el alto del frame.

**T2 — Historial compartido** · nuevo `interface/terminal_model.py`, `terminal_view.py`, `terminal_window.py`, `desktop_pet.py`

- Crear `TerminalMessage(role, text, error, stamp)` (dataclass inmutable) y `TerminalHistory` con `add_user(text)`, `add_sophia(text, error=False)`, `clear()`, `messages` (máximo 300) y `subscribe(callback)` / `unsubscribe(callback)`.
- **`stamp` se fija al crear el mensaje** (`HH:MM`), nunca al dibujar. Esto arregla la causa 5.
- `SophiaDesktopApp` crea **un solo** `TerminalHistory` y lo pasa a cada `TerminalView`: la ventana flotante y la principal.
- `TerminalView(master, history, on_submit, model, on_palette)` dibuja desde `history`, se suscribe al crearse y se desuscribe al destruirse (`<Destroy>`).
- `_append_user` y `_append_sophia` en `desktop_pet.py` escriben en el historial **una vez** (hoy escriben dos, una por vista). Eliminar `TerminalWindow.append_user` y `append_sophia`.
- `_welcome` agrega el saludo al historial: así aparece al abrir la terminal por primera vez.

*Listo cuando:* enviar 3 mensajes, cerrar con × y reabrir muestra los 3, con sus horas originales, y redimensionar no cambia ninguna hora. *Tests (sin Tk):* límite de 300, suscripción y desuscripción, `clear()`, `stamp` estable.

**T3 — Ajuste de líneas sin doble wrap** · `terminal_view.py`

- `self.log.configure(wrap=tk.NONE)`: el texto ya llega ajustado, Tk no debe volver a ajustarlo.
- Calcular las columnas con medidas reales del log, no del frame:

```python
fnt = tkfont.Font(font=self.log.cget('font'))
char_w = fnt.measure('0')
usable = self.log.winfo_width() - 2 * int(self.log.cget('padx')) - 4
columns = max(30, usable // char_w - 1)   # -1 de margen de seguridad
```

- Redibujar con el evento `<Configure>` **del log** (con la espera de 150 ms que ya existe). Si `winfo_width()` devuelve 1 (aún no mapeado), reintentar con `after_idle`.

*Listo cuando:* ninguna línea se ve partida en dos ni cortada; en una respuesta larga, las líneas llenan el ancho de forma pareja a cualquier tamaño de ventana. *Test:* en `terminal_render.wrap`, ninguna línea supera `columns` (con y sin prefijo `▎`).

**T4 — Autoscroll inteligente** · `terminal_view.py`

`_render_all` llama siempre a `scroll_to_end`. Cambiarlo: antes de redibujar guardar `at_bottom = self.log.yview()[1] >= 0.999` y la posición `yview()[0]`; después, si `at_bottom` o el mensaje nuevo es del usuario, ir al final; si no, `yview_moveto(posición)`. Así aparece el aviso «Ir al final ↓» cuando corresponde.

## 3. Fase 2: burbuja que se adapta al texto

Objetivo: la ventana tiene **el tamaño justo del contenido**. El botón ENTENDIDO siempre va debajo del último renglón.

**B1 — Calcular el layout con métricas reales** · `speech_bubble.py`

Función pura, sin Tk:

```python
@dataclass(frozen=True)
class BubbleLayout:
    width: int
    height: int
    title_lines: list[str]
    body_lines: list[str]
    stage_y: int | None
    title_y: int
    body_y: int
    body_h: int
    button: tuple[int, int, int, int]   # x1, y1, x2, y2
    truncated: bool

def compute_layout(title, body, measure_title, measure_body,
                   line_h_title, line_h_body, scale, max_height, stage_h=0) -> BubbleLayout: ...
```

Las alturas de línea salen de `font.metrics('linespace')` de cada fuente. **Eliminar las constantes 16 y 18 px.**

Posiciones (todas multiplicadas por `scale`), acumulando hacia abajo:

1. `y = margen(12) + 12`.
2. Cabecera (retrato 54 + 2 de borde): ocupa `header_h = 56`. Luego `y += header_h + gap(10)`.
3. Si hay escenario de intro: `stage_y = y`, `y += stage_h + gap`.
4. Si hay título: `title_y = y`, `y += len(title_lines) * line_h_title + gap`.
5. `body_y = y`, `y += len(body_lines) * line_h_body + gap`.
6. **`button_y = y`**, alto 34, `y += 34 + 12`. El botón nunca se ubica con `height - X`.
7. `height = y + margen(12) + cola(18)`.

Ancho adaptativo:

- Hacer el ajuste de líneas con el ancho máximo (460), medir la línea más ancha y fijar `width = clamp(línea_más_ancha + 128, 320, 460)`. Un texto corto da una burbuja angosta.

Alto máximo y recorte:

- `max_height = 60 % del alto del monitor` (usar `monitor_at`). Si el cuerpo no entra, mostrar las líneas que caben y terminar la última con `…`; `truncated = True`. El texto completo siempre está en la terminal.
- Quitar el tope silencioso de 18 líneas de `_wrapped`.
- `_wrapped` hoy usa `text.split()` y **pierde los saltos de línea** de la respuesta. Respetar los párrafos: separar por saltos de línea, ajustar cada párrafo y permitir como máximo una línea en blanco seguida.

**B2 — Un solo método que dibuja** · `speech_bubble.py`

- Mover todo el dibujo de `show()` a `_draw(layout, portrait, status)`: polígono, cola, retrato, «SOPHIA», pill, título, barra de acento, texto del cuerpo y botón, **todo con coordenadas de `layout`**.
- `show()` = crear la ventana oculta + `compute_layout` + `_draw` + `geometry`.
- **`update_content()` = `compute_layout` + `canvas.delete('all')` + `_draw` + `window.geometry(WxH)` + reposicionar.** Aquí está el bug de la captura.
- Guardar el último estado de la pill en `self._status` para repintarlo.
- Guardar los argumentos de la última `position_near` en `self._anchor` para que `update_content` pueda reposicionarse sola. Como la burbuja está arriba de la mascota, al crecer debe **crecer hacia arriba** (la cola sigue tocando a la mascota).
- El `item` del texto del cuerpo debe tener `width` **mayor** al ancho de ajuste (+ 4 × scale) o ninguno, para que el canvas no vuelva a ajustar.

**B3 — Retrato y expresión al responder** · `speech_bubble.py`

`update_content` recibe `expression` y `portrait` pero no los usa: el retrato queda en `face-look` de la fase de «pensando». Con `_draw` se redibuja con el retrato de la respuesta.

**B4 — Temporizador de cierre** · `speech_bubble.py`

`show_thinking` crea la burbuja con un cierre a los 18 s y `update_content` no lo reinicia: si el modelo tardó, la burbuja se cierra pocos segundos después de responder. Al actualizar el contenido, cancelar `_close_id` y reprogramarlo con `seconds * 1000 + len(body) * 22` (máximo 18 s), contado desde ese momento. Poner `_thinking_dot_id = None` luego de cancelarlo.

**B5 — Máquina de escribir sin saltos** · `speech_bubble.py`

El layout se calcula con el **texto completo** desde el principio; el efecto solo revela caracteres. La ventana no cambia de tamaño mientras escribe.

**B6 — Intro que no borra el texto** · `speech_bubble.py`, `desktop_pet.py`, `intro_sequence.py`

Hoy `_welcome` muestra una burbuja con el saludo y después `play_stage` la pisa (`canvas.delete('all')`, 400×250 fijo, sin título, cuerpo ni botón).

- `show(..., stage_frames=None)`: si recibe frames, `compute_layout(..., stage_h=126 * scale)` y `_draw` dibuja el escenario entre la cabecera y el título. El texto y el botón siguen visibles todo el tiempo.
- `play_stage` **solo cambia la imagen** del `item` del escenario con `itemconfigure`. Los tiempos salen de `INTRO_SEQUENCE` (borrar la lista `durations` duplicada).
- En `_welcome`: agregar el saludo al historial (T2) y no mostrar burbuja todavía. Con `show_intro` activo, esperar los frames del hilo (evento `intro_frames`) y recién ahí hacer `show(..., stage_frames=frames)`. Si en 2 s no llegaron o `show_intro` es `false`, mostrar la burbuja normal.
- Mientras corre la secuencia, el temporizador de cierre debe sumar la duración total de la animación.
- Ignorar el evento `intro_frames` si el usuario ya envió un mensaje (hay una burbuja de «pensando» activa).

**B7 — Escala de pantalla** · `screen_metrics.py`, `speech_bubble.py`, `terminal_window.py`

Agregar `ui_scale(root) = root.winfo_fpixels('1i') / 96`. Multiplicar por ese factor **todas las constantes en píxeles** de la burbuja y de la ventana de la terminal (márgenes, retrato, pill, botón, franja de título de 34 px, agarre de 8 px, tamaños mínimos). Las fuentes en puntos ya escalan solas.

**B8 — Tests** · `tests/test_bubble_layout.py` (sin Tk)

Con `measure = len(text) * 8` y alturas de línea 18, 22 y 26, escala 1.0, 1.5 y 2.0, y textos de 20, 110, 400 y 1500 caracteres:

- `button[1] >= body_y + body_h` (el botón nunca pisa el texto).
- `height <= max_height`.
- `320 * scale <= width <= 460 * scale`.
- `truncated` es `True` solo cuando hizo falta y la última línea termina en `…`.
- Un texto con saltos de línea conserva los párrafos.
- Con `stage_h > 0`, `stage_y < title_y < body_y`.

*Listo cuando:* una respuesta de 1 línea y una de 25 muestran burbujas de tamaños distintos, sin solaparse, con el botón debajo de todo, y la burbuja de «pensando» crece sin parpadear al llegar la respuesta.

## 4. Fase 3: detalles de la terminal

**D1 — Scrollbar oscura** · `terminal_view.py`

`tk.Scrollbar` en Windows ignora los colores. Usar `ttk.Scrollbar` con el tema `clam` (la app no usa otros widgets ttk):

```python
style = ttk.Style(self)
style.theme_use('clam')
style.configure('Sophia.Vertical.TScrollbar',
                troughcolor=TERMINAL_THEME.background, background=TERMINAL_THEME.border,
                bordercolor=TERMINAL_THEME.background, lightcolor=TERMINAL_THEME.border,
                darkcolor=TERMINAL_THEME.border, arrowcolor=TERMINAL_THEME.accent_light)
style.map('Sophia.Vertical.TScrollbar', background=[('active', TERMINAL_THEME.accent)])
```

**D2 — Pie** · `terminal_view.py`

Reemplazar el `Label` con espacios por un `Frame` con dos `Label`: izquierda, la ruta del proyecto (reemplazar el home por `~`, con `/`); derecha, `ctrl+p comandos`. Va **debajo** de la línea de estado (orden de T1). Ya no se usa la ruta fija `~/Documents/Sophia IA`.

**D3 — Copiar** · `terminal_view.py`

- En el prompt, `<Control-c>` hoy devuelve `'break'` y bloquea la copia. Si hay selección, copiarla; si no, no hacer nada.
- En el log, bindear `<Control-c>` para copiar la selección y llamar a `self.log.focus_set()` en `<Button-1>` (un `Text` deshabilitado no toma el foco con el clic).

**D4 — Historial con ↑ y ↓** · `terminal_view.py`

Hoy `↑` siempre reemplaza el texto. Solo debe recorrer el historial cuando el cursor está en la primera línea del prompt (y `↓` en la última); si no, comportamiento normal.

**D5 — Menú de `/`** · `terminal_view.py`

Verificar primero: escribir `/` y seguir tecleando. `Menu.tk_popup` en Windows captura el teclado hasta cerrarse, así que probablemente no se pueda seguir escribiendo. Si pasa, reemplazarlo por un `Listbox` colocado con `place` encima del prompt, sin tomar el foco: `↑`/`↓` navegan, `Tab` o `Enter` completan, `Esc` cierra.

**D6 — Guardado de posición y tamaño** · `terminal_window.py`

`<Configure>` del `Toplevel` también se dispara por los widgets hijos. Filtrar con `if event.widget is not self.window: return`. Guardar `terminal_x/y/w/h` con `Settings.save` al soltar el agarre de tamaño y al cerrar, no en cada evento.

## 5. Fase 4: limpieza (riesgo bajo)

**L1 — Restos del chat viejo** · `desktop_pet.py`

Buscar el uso de cada uno antes de borrarlo: el `tk.Entry` oculto `_entry` con `place_forget()`, `_chat`, `_send()`, `_refresh_audio_buttons` (apunta a botones que ya no existen), `_show_pet_bubble`, `_position_pet_bubble`, `_close_pet_bubble`, `_start_anim`, `_play_frame`, `_stop_anim` y `_anim_*` si ya no se usan, y los sprites `cutin-*` de 200 px. En modo ventana no hay burbuja: solo la terminal.

**L2 — Settings** · `settings.py`

Verificar que `terminal_x`, `terminal_y`, `terminal_w` y `terminal_h` sean campos del dataclass (con `None`, `None`, 680 y 460 por defecto). `Settings.load` descarta todo lo que no sea campo. Validar en `__post_init__` que `terminal_w` y `terminal_h` sean enteros positivos.

**L3 — Documentación**

Agregar una entrada v0.4 al `CHANGELOG.md` con los arreglos de esta lista.

## 6. Orden de ejecución

| Orden | Tareas | Qué se ve al terminar |
| --- | --- | --- |
| 1 | T1 | Prompt visible desde el primer segundo |
| 2 | B1, B2, B3, B4 | Burbuja del tamaño del texto |
| 3 | T2, T3 | Historial que no se pierde y líneas parejas |
| 4 | B5, B6, B7, B8 | Intro con texto visible y todo escalado |
| 5 | T4, D1–D6 | Detalles de la terminal |
| 6 | L1–L3 | Código más limpio |

## 7. Checklist manual

- Editar `data/settings.json` con `terminal_w: 560` y `terminal_h: 360`, abrir la terminal: se ven prompt, estado y pie.
- Probar con la escala de Windows al 100, 125 y 150 %.
- Respuestas de 20, 150, 500 y 1500 caracteres: la burbuja crece sin tapar el botón; la de 1500 se recorta con `…`.
- Enviar un mensaje y esperar: la burbuja de «pensando» se transforma en la respuesta sin cerrarse ni saltar.
- Cerrar y reabrir la terminal: el historial sigue y las horas no cambiaron.
- Redimensionar la terminal a ancho y a angosto: sin líneas partidas ni cortadas.
- Subir con la rueda y recibir un mensaje: no salta, aparece «Ir al final ↓».
- Arrancar con `show_intro` activo: el saludo queda visible durante y después de la animación.
- Arrancar con `show_intro` en `false`: burbuja normal.

## 8. Prompt para OpenCode

> Leé este documento y `CONTEXTO_PROYECTO_SOPHIA.md`. Trabajá **solo la Fase 1**, una tarea por vez y con un commit por tarea. Antes de editar cada archivo, leelo completo. Tocá únicamente los archivos que nombra la tarea. No leas `.env`, `data/memoria.json` ni `data/voice_cache/`. No agregues dependencias. Corré `python -m unittest discover -s tests -v` antes de cada commit. Si una tarea falla dos veces, detenete y contame qué probaste. Al terminar la fase, reportá qué cambió, qué archivos tocaste y cómo probarlo. No hagas `git push`.

Para las otras fases, reemplazá «Fase 1» por la que corresponda.
