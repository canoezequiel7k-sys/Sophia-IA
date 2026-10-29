# Sophia — Compañera de Escritorio

Sophia es una compañera de escritorio interactiva que vive en tu segunda pantalla. Conversa con personalidad propia en español rioplatense, recuerda tus charlas y cambia de expresión mientras responde. Usa la **API gratuita de Google Gemini** como cerebro y no requiere ningún paquete externo salvo Pillow.

---

## Iniciar

Doble clic en **`iniciar_sophia_desktop.bat`** o ejecutá:

```bash
python main.py
```

---

## Configurar el cerebro (Google Gemini API — gratis)

1. Obtené tu clave en [Google AI Studio](https://aistudio.google.com/).
2. Creá un archivo `.env` en la raíz (podés copiar `.env.example`):
   ```env
   GEMINI_API_KEY=tu_clave_aqui
   ```
3. Reiniciá Sophia.

---

## Uso

- **Arrastrar:** Arrastrá la barra superior `✦ SOPHIA` para moverla a cualquier monitor.
- **Fijar:** El botón 📌 la deja siempre visible sobre otras ventanas.
- **Cerrar:** Botón ✕ o simplemente cerrá la ventana.

---

## Estructura

```
companera/
  domain/
    models.py              → CheckIn, Mood, Topic
  application/
    ports.py               → Contratos: MemoryRepository, Clock
  infrastructure/
    gemini_service.py      → Cliente de Google Gemini API
    json_memory_repository.py → Memoria persistente en data/memoria.json
    system_clock.py        → Reloj del sistema
  interface/
    desktop_pet.py         → Ventana nativa Tkinter + Pillow
  assets/sophia/           → Sprites y expresiones del personaje
main.py                    → Punto de entrada
tests/test_sophia.py       → Pruebas unitarias
```

---

## Pruebas

```bash
python -m unittest discover -s tests -v
```
