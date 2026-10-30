# Sophia — Contexto del Proyecto

**Sophia** es una compañera de escritorio nativa en Python, inspirada en Capri Desktop.
Vive en la segunda pantalla del usuario, conversa con personalidad propia en español rioplatense y cambia de expresión facial mientras responde o piensa.

---

## Estado Actual (v0.3)

- **Cerebro:** Google Gemini API con salida JSON estructurada, fallback y autenticación por `x-goog-api-key`.
- **Interfaz:** Ventana nativa Tkinter + Pillow, arrastrable, con soporte "siempre encima" y cola de eventos.
- **Voz/sonido:** `edge-tts` + `pygame-ce`, caché y degradación segura sin dependencias.
- **Configuración:** `Settings` persistido en `data/settings.json`.
- **Memoria/perfil:** Escritura atómica, cuarentena de memoria dañada y perfil local borrable.
- **Arquitectura:** Puertos de aplicación, `ChatService`, comandos locales y herramientas con permisos.
- **Tests:** Pruebas unitarias locales con fakes, sin ventanas, audio ni red.

---

## Archivos Clave

| Archivo | Rol |
|---|---|
| `main.py` | Punto de entrada. Lanza `start_desktop()`. |
| `companera/interface/desktop_pet.py` | Ventana, animaciones, lógica de UI. |
| `companera/infrastructure/gemini_service.py` | Cliente HTTP para Gemini API. Prompt del sistema y extracción de expresiones. |
| `companera/infrastructure/json_memory_repository.py` | Memoria persistente. |
| `companera/domain/models.py` | `CheckIn`, `Mood`, `Topic`. |
| `companera/application/ports.py` | Protocolos `MemoryRepository` y `Clock`. |
| `companera/assets/sophia/` | Sprites PNG del personaje (face-*, cutin-*, intro-*). |
| `.env` | `GEMINI_API_KEY=tu_clave` (ignorado por git). |

---

## Expresiones del Personaje

El modelo Gemini devuelve JSON estructurado con el campo `expression`.
Por compatibilidad, el cliente acepta también una etiqueta legado `[EXPR: nombre]` al final.
El sistema valida el catálogo único en `domain.models` y muestra el sprite correspondiente:

| Etiqueta | Sprite | Cuando se usa |
|---|---|---|
| `calm` | `face-calm.png` | Respuesta cotidiana o tranquila |
| `laugh` | `face-laugh.png` | Alegría, broma o entusiasmo |
| `smug` | `face-smug.png` | Confianza, logro o picardía |
| `look` | `face-look.png` | Curiosidad o pregunta |
| `aside` | `face-aside.png` | Análisis o algo delicado |
| `wide` | `face-wide.png` | Sorpresa o descubrimiento |
| `many` | `face-many.png` | Confusión cómica |

Mientras piensa → cicla: `cutin-eyes → cutin-look → cutin-many → face-look → face-aside`
Mientras habla → cicla: `cutin-eyes → cutin-grin → cutin-laugh → cutin-look → cutin-many → face-{expr}`

---

## Próximas Ideas

- Voz de salida con `edge-tts` (voces en español argentino).
- Comportamientos autónomos: saludar al iniciar sesión, entrar en modo "sleepy" si no la hablás.
- Burbuja de diálogo flotante sin borde de ventana (mascota de escritorio pura).
