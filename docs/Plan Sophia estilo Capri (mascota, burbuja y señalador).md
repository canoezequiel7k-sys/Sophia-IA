# Plan: Sophia estilo Capri (mascota, burbuja y señalador)

*Preparado el 30/10/2026 a partir de la lectura del código real de `Sophia IA` y de la captura de referencia de Capri Desktop.*

## 0. Objetivo

Que Sophia viva en el escritorio como en tu referencia:

1. **Personaje flotante** sin ventana ni marco, arrastrable, que usa `capri-cutout.png`.
2. **Burbuja cyberpunk** con esquinas cortadas, retrato (`face-*`) con marco, nombre más etiqueta de estado, título, cuerpo con barra de acento y botón de confirmar.
3. **Señalador**: flecha punteada desde el personaje hasta un punto de la pantalla, con una etiqueta (por ejemplo "MI ÍCONO").
4. **Cerebro**: Gemini devuelve título, cuerpo y, si hace falta, a qué señalar.

Todos los sprites ya están en `companera/assets/sophia/`. Lo que falta es código de interfaz.

## 1. Reglas de trabajo

- Ir **por fases, en orden**. Al terminar cada fase, probarla a mano antes de seguir.
- Un commit por tarea (`feat:`, `fix:`, `refactor:`, `test:`). Sin `git push` hasta que vos lo decidas.
- No leer ni imprimir `.env`, `data/memoria.json` ni `data/voice_cache/`.
- Sin dependencias nuevas: todo se resuelve con Tkinter, Pillow y `ctypes`.
- Código específico de Windows detrás de funciones chicas con respaldo (`if sys.platform == "win32"`).
- Ningún hilo secundario toca widgets de Tk: todo pasa por la cola de eventos que ya existe.
- Correr `python -m unittest discover -s tests -v` antes de cada commit.

## 2. Fase 0 — Base: arreglar lo que estorba

Estos errores afectan directamente al modo mascota. Conviene resolverlos antes.

**T0.1 — Clic en el avatar muerto** · `desktop_pet.py` `_build_ui` bindea `<Button-1>` y `_setup_drag` bindea `<ButtonPress-1>` en el mismo widget. En Tk son el mismo evento, así que el segundo pisa al primero. Unificar en un solo manejador: si el mouse se movió menos de 4 px entre presionar y soltar es un clic (saludo), si se movió más es un arrastre. *Listo cuando:* clic = saludo, arrastrar = mueve la ventana.

**T0.2 — Orden de empaquetado al volver a modo chat** · `desktop_pet.py` Al hacer `pack_forget()` y luego `pack()`, la barra de título pasa al final y queda debajo del avatar. Volver a empaquetar con `before=` apuntando al frame del avatar. *Listo cuando:* alternar modo mascota y chat varias veces deja la barra arriba.

**T0.3 — Usar `ChatService`** · `desktop_pet.py` `_process` duplica la lógica de `ChatService`. Reemplazarlo por una llamada a `ChatService.send()` para que las fases siguientes (título, objetivo) se agreguen en un solo lugar.

**T0.4 — Eventos de la bandeja** · `desktop_pet.py` `_poll_events` solo maneja `"reply"`. Agregar `tray_toggle`, `tray_mute` y `tray_exit`, y arrancar `SophiaTray` si `minimize_to_tray` está activo. Cuando el personaje flote sin ventana, la bandeja es la forma de recuperarla.

**T0.5 — `read_text_file`** · `tools.py` El parámetro se llama `path` en el registro pero `path_text` en el método. Unificar el nombre y agregar un test del camino feliz.

## 3. Fase 1 — Personaje flotante limpio

**Archivo nuevo:** `companera/interface/pet_window.py`.

**T1.1 — Ventana del personaje**

- `overrideredirect(True)`, `-topmost` y `-transparentcolor` con un color clave raro (por ejemplo `#010203`) y **no** el `#0f111a` del tema, para que ningún píxel del sprite coincida por accidente.
- Si el sistema no es Windows, caer a una ventana normal sin transparencia.

**T1.2 — Sprite sin halo** Tk no soporta alpha por píxel. Los bordes suavizados del PNG se mezclan con el color de fondo y dejan un contorno feo. Solución: con Pillow, componer el sprite sobre el color clave con un umbral (alfa menor a 128 pasa a color clave, el resto se mezcla contra el color clave). Cachear el resultado por tamaño.

**T1.3 — Tamaño y posición**

- El alto sale de `Settings.avatar_size` (120, 160 o 220 de ancho base). Hoy el sprite se carga fijo a 200 px.
- Posición inicial: esquina inferior derecha del **área de trabajo** (sin pisar la barra de tareas). Obtenerla con `SystemParametersInfoW(SPI_GETWORKAREA)`.
- Guardar la posición al soltar el arrastre (`pet_x`, `pet_y` en `Settings`) y restaurarla al iniciar, verificando que siga dentro de alguna pantalla.

**T1.4 — Interacción**

- Arrastre desde el propio sprite (con el umbral de T0.1).
- Clic derecho: menú con mute, siempre encima, mostrar/ocultar chat, modo chat y salir.
- Los píxeles del color clave dejan pasar los clics a lo que haya detrás: es el comportamiento que querés.

**T1.5 — Vida en reposo** · `avatar_animator.py` Conectar `AvatarAnimator`: flotación suave de 2 px cada 4 a 9 segundos, desactivable con `rest_animation`.

**Cierre de fase:** Sophia flota sin marco, sin halo, se arrastra, recuerda dónde la dejaste y se puede salir desde el menú o la bandeja.

## 4. Fase 2 — Burbuja cyberpunk

**Archivo nuevo:** `companera/interface/speech_bubble.py`. Ampliar `theme.py`.

**T2.1 — Paleta** (aproximada, sacada de la captura; ajustá con el cuentagotas)

| Elemento | Color |
| --- | --- |
| Fondo de la burbuja | `#140f22` |
| Borde y barra de acento | `#7c3aed` |
| Pill de estado ("SYNC") | `#6d28d9` |
| Etiqueta del señalador | `#ff2d6f` |
| Texto principal | `#f5f3ff` |
| Texto secundario | `#c4b5fd` |

Agregarlos como campos del dataclass `Theme` (hoy el tema no los tiene) y mantener el tema `claro` coherente.

**T2.2 — Anatomía** (de arriba hacia abajo)

1. Fila superior: retrato de 56 px con marco, nombre "SOPHIA" en mayúsculas con fuente monoespaciada (Consolas) y la pill de estado a la derecha.
2. Título en negrita, hasta dos líneas.
3. Cuerpo con una barra vertical de acento a la izquierda.
4. Botón "ENTENDIDO" que cierra la burbuja.
5. Cola (triángulo) que apunta al personaje.

**T2.3 — Dibujo**

- `Toplevel` sin borde con el mismo color clave de la Fase 1.
- Contorno: polígono de esquinas cortadas (chaflán de 12 px). Para bordes nítidos, renderizar el contorno con Pillow a doble resolución y reducir; los textos van como items de `Canvas` encima.
- Medir el texto con `tkinter.font.Font.measure` para calcular el alto antes de dibujar.

**T2.4 — Estados**

- Retrato: `face-{expresión}` de la respuesta (ya existe el catálogo en `domain`). Mientras piensa, alternar `cutin-*`.
- Pill: "PENSANDO", "HABLANDO", "LISTA" según el estado real de la app.
- Efecto máquina de escribir opcional (un carácter cada 15 a 20 ms con `after`), cancelable al llegar otra respuesta.

**T2.5 — Posición y ciclo de vida**

- Aparece arriba o al costado del sprite. Si no entra en pantalla, se da vuelta. Sigue al personaje mientras se arrastra.
- Se cierra con el botón, con un clic o a los N segundos según el largo del texto. **Guardar el id del `after`** y cancelarlo cuando llegue una burbuja nueva (hoy un timer viejo cierra la burbuja nueva).

**T2.6 — Título y cuerpo provisorios** Hasta la Fase 4, el título es la primera oración (máximo 60 caracteres) y el cuerpo es el resto.

**Cierre de fase:** la respuesta de Gemini aparece como en tu referencia, con retrato que cambia según la expresión.

## 5. Fase 3 — Señalador (flecha y etiqueta)

**Archivo nuevo:** `companera/interface/pointer_overlay.py`.

**T3.1 — Overlay a pantalla completa**

- `Toplevel` sin borde que cubre el **escritorio virtual** completo (todas las pantallas: `GetSystemMetrics` con `SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`, `SM_CXVIRTUALSCREEN`, `SM_CYVIRTUALSCREEN`), `-topmost` y color clave.
- Con `ctypes`, agregarle `WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW` (`GetWindowLongW` y `SetWindowLongW`) para que sea totalmente transparente a los clics y no aparezca en la barra de tareas.
- Crearlo **solo cuando se necesita** y destruirlo al terminar.

**T3.2 — Dibujo**

- Línea punteada (`dash=(6, 4)`) del personaje al objetivo, con punta de flecha en el extremo.
- Etiqueta rosa con texto en mayúsculas junto al objetivo, más un pequeño triángulo apuntando.
- Animación: la línea "crece" en unos 300 ms con `after` cada 16 ms.

**T3.3 — API**

```python
overlay.point_at(x, y, label, origin=(ox, oy))
overlay.clear()
```

Se limpia sola al cerrar la burbuja, al pasar un tiempo o al presionar Escape.

**T3.4 — Objetivos conocidos** · `infrastructure/screen_targets.py` (nuevo) Funciones que devuelven un punto sin ver la pantalla del usuario:

- `clock_area()`: rectángulo de la bandeja y el reloj (ventana `Shell_TrayWnd` con `GetWindowRect`).
- `active_window()`: rectángulo de la ventana en primer plano (`GetForegroundWindow`).
- `screen_corner(nombre)` y `mouse_position()`.

**T3.5 — Comando de prueba** `/señalar reloj` y `/señalar ventana` en `commands.py`, para probar el señalador sin depender de Gemini.

**Cuidados:** DPI (ya hay `SetProcessDpiAwareness(1)` en `main.py`: verificar que las coordenadas coincidan), varias pantallas con coordenadas negativas, y apps a pantalla completa que pueden tapar un `topmost`.

**Cierre de fase:** `/señalar reloj` dibuja una flecha desde Sophia hasta el reloj, con etiqueta, sin bloquear ningún clic.

## 6. Fase 4 — Cerebro: título y objetivo en la respuesta

**T4.1 — Modelo** · `domain/models.py` Agregar a `Reply`: `title: str = ""` y `target: str = "none"` y `target_label: str = ""`. Tipar `mood` y `topic` correctamente (hoy son `object`; mover `Mood` y `Topic` arriba de `Reply`).

**T4.2 — Schema de Gemini** · `gemini_service.py` Agregar al `responseSchema`: `title` (string corto), `target` (enum cerrado: `none`, `clock`, `tray`, `active_window`) y `target_label` (string corto). El modelo **no** devuelve coordenadas en esta etapa: elige un objetivo de una lista que vos controlás.

**T4.3 — Persona** · `persona/sophia.md` Completar con: cuándo usar cada expresión, cómo armar título y cuerpo (título de menos de 60 caracteres), cuándo señalar (solo si ayuda de verdad, nunca decorativo), y corregir "Hablas" por "Hablás".

**T4.4 — Orquestación** Si `target` es distinto de `none`, la UI pide el punto a `screen_targets`, y el señalador y la burbuja aparecen juntos. Si el objetivo no se puede resolver, solo se muestra la burbuja.

**T4.5 — Tests** JSON con y sin objetivo, valor fuera del enum, JSON roto (debe caer a texto crudo con `calm`), y objetivo no resoluble.

**Mejora pendiente:** si la respuesta se trunca con salida estructurada, hoy se muestra el JSON roto como texto. Subir `maxOutputTokens` y detectar `finishReason` de truncado.

## 7. Fase 5 — "Mirá mi pantalla" (opcional, opt-in)

Solo si querés que Sophia señale elementos arbitrarios y no una lista fija.

- Comando o botón `/pantalla`, con confirmación visible: *"Esta imagen sale hacia Google"*.
- Captura con `PIL.ImageGrab`, enviada como dato en línea. **Nunca se guarda en disco.**
- Pedirle a Gemini la ubicación del elemento. **Verificar en la documentación oficial** el formato exacto de coordenadas (las cajas de detección suelen venir normalizadas), y convertir a píxeles teniendo en cuenta DPI y escritorio virtual.
- Indicador visible mientras se captura.

## 8. Orden y resultado visible

| Fase | Qué vas a ver al terminar | Esfuerzo |
| --- | --- | --- |
| 0 | Clic y modo chat andan bien | Bajo |
| 1 | Sophia flotando sin marco | Medio |
| 2 | Burbuja como en la referencia | Medio-alto |
| 3 | Flecha y etiqueta al reloj | Medio |
| 4 | Gemini decide título y objetivo | Medio |
| 5 | Señalar cualquier cosa de la pantalla | Alto |

Si querés ver algo vistoso rápido, hacé la Fase 0, saltá a la 2 con un `Toplevel` fijo de prueba, y volvé a la 1.

## 9. Checklist manual por fase

- Arrastrar a la segunda pantalla y volver a abrir la app: ¿recuerda la posición?
- Cambiar a escala de pantalla 125 % o 150 % en Windows: ¿siguen alineados sprite, burbuja y flecha?
- Abrir un juego o video a pantalla completa: ¿molesta el personaje o el overlay?
- Cerrar con el menú, con la bandeja y con ✕: ¿no quedan procesos ni ventanas fantasma?
- Probar sin clave, sin internet y sin `pygame`: ¿degrada con mensajes claros?

## 10. Riesgos

- **Sin alpha por píxel en Tk:** el halo y las esquinas dentadas son el principal problema visual. Por eso el compuesto con umbral (T1.2) y el dibujo con Pillow (T2.3).
- **Solo Windows:** transparencia, click-through y áreas de trabajo usan `ctypes`. Mantener el respaldo para otras plataformas.
- **Privacidad:** cada mensaje sale a Google. Las capturas (Fase 5) son datos sensibles: siempre opt-in, visibles y sin guardarse.
- **Complejidad de `desktop_pet.py`:** ya tiene unas 500 líneas. Mover mascota, burbuja y señalador a sus módulos y dejar la app como orquestadora.

## 11. Prompt inicial para tu agente de código (Copilot)

> Leé `docs/` y `CONTEXTO_PROYECTO_SOPHIA.md`. Trabajá **solo la Fase 0** de este plan, tarea por tarea, con un commit por tarea. No leas `.env`, `data/memoria.json` ni `data/voice_cache/`. No agregues dependencias. Corré `python -m unittest discover -s tests -v` antes de cada commit. Al terminar la fase, detenete y reportá qué cambió, qué archivos tocaste y cómo probarlo. No hagas `git push`.
