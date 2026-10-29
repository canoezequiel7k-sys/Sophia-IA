# Contexto Integral y Análisis de Arquitectura: Sophia IA Companion

Este documento reúne todo el contexto técnico, la arquitectura, el inventario de archivos y el diagnóstico del proyecto **Sophia IA**. Está preparado para que GitHub Copilot o cualquier otro asistente/agente puedan analizar el código a fondo y saber con exactitud **qué es esencial preservar**, **qué se puede limpiar o desacoplar**, y **cómo evolucionar a Sophia a una compañera de escritorio completa**.

---

## 1. Visión del Proyecto y Transformación

* **Origen:** Prototipo de terminal en Python sin dependencias que actuaba como tutora de Python mediante reglas de palabras clave y archivos Markdown de apuntes.
* **Estado Actual:** Compañera nativa de escritorio (`desktop_pet.py`) inspirada en Capri Desktop, con ventana cyberpunk arrastrable, sprites de expresiones de Capricornio y conectada en vivo a **Google Gemini 3.1 Flash Lite API**.
* **Objetivo Futuro:** Dejar atrás el rol rígido de "bot de preguntas y respuestas de Python" y convertirse en una **compañera de escritorio interactiva, viva y personal**, que habite en la segunda pantalla, con expresiones ricas, personalidad cercana y memoria continua.

---

## 2. Inventario de Archivos: Esenciales vs. Inservibles

### 🟢 A. Núcleo Esencial (¡NO BORRAR!)
Estos componentes forman la base sólida de Clean Architecture, la persistencia, la conexión con Gemini y la interfaz nativa:

| Archivo / Carpeta | Función actual | Por qué conservarlo |
|---|---|---|
| `companera/infrastructure/gemini_service.py` | Cliente HTTP puro para Google Gemini (Gemini 3.1 Flash Lite) con fallback y extracción de expresiones faciales. | Es el cerebro conversacional de alta velocidad (menos de 1 segundo). |
| `companera/interface/desktop_pet.py` | Ventana nativa en `tkinter` + `Pillow`, diseño cyberpunk, soporte multimonitor (arrastre), *always on top*, subproceso en segundo plano para no congelar la UI. | Es el "cuerpo" de Sophia en tu segunda pantalla. |
| `companera/infrastructure/json_memory_repository.py` | Repositorio atómico que guarda y lee `data/memoria.json`. | Es la memoria a largo plazo que le permite recordar charlas pasadas. |
| `companera/domain/models.py` | Modelos de datos: `CheckIn`, `Mood`, `Topic`. | Define los contratos de datos puros sin acoplarse a librerías externas. |
| `companera/assets/sophia/` (27 archivos) | Sprites PNG y WebP (`face-calm`, `face-laugh`, `face-smug`, `face-look`, `face-aside`, `cutin-*`, `capri-cutout.png`, etc.). | Son todas las expresiones visuales del personaje. |
| `main.py` | Punto de entrada flexible (`--desktop` o terminal). | Inyector de dependencias principal. |
| `iniciar_sophia_desktop.bat` | Script de ejecución rápida para Windows. | Lanzador de un solo clic. |
| `.env` / `.env.example` | Clave de API `GEMINI_API_KEY`. | Configuración segura ignorada por git. |
| `tests/` (`test_companion.py`, `test_gemini.py`) | 19 pruebas unitarias automatizadas. | Garantizan que ningún cambio rompa la estabilidad del software. |

---

### 🔴 B. Contexto Antiguo de Python (Candidatos a Limpiar o Desacoplar)
Eran el "esqueleto" inicial para que respondiera sobre sintaxis de Python, pero para una compañera general de escritorio resultan innecesarios o limitantes:

1. **`companera/python context/` (5 archivos Markdown, ~86 KB):**
   - `python_bloque_1_fundamentos.md`
   - `python_bloque_2_control_de_flujo.md`
   - `python_bloque_3_funciones.md`
   - `python_bloque_4_poo.md`
   - `python_bloque_5_errores_y_archivos.md`
   - *Diagnóstico:* Son manuales estáticos de texto. Como ahora Sophia tiene acceso a Gemini 3.1, Gemini **ya sabe Python de forma nativa mucho mejor que estos archivos**. Inyectar estos textos en cada mensaje consume tokens y limita las respuestas de Sophia a definiciones escolares.
2. **`README_contexto_IA_Python.md` (526 líneas):**
   - Reglas didácticas rígidas de cómo enseñar Python a principiantes.
   - *Diagnóstico:* Fuerza a la IA a actuar como profesora estricta en vez de una compañera viva en el escritorio.
3. **`index.html`:**
   - Prototipo inicial de canvas en navegador web.
   - *Diagnóstico:* Confirmado por el usuario como 100% descartado. Se puede eliminar sin afectar nada del programa.

---

### 🟡 C. Componentes de Transición (A Generalizar)

| Archivo | Situación actual | Mejora necesaria |
|---|---|---|
| `companera/infrastructure/markdown_knowledge_base.py` | Lee únicamente los apuntes de Python. | Si se eliminan los apuntes de Python, este buscador se puede simplificar o reconvertir en una base para guardar notas personales que vos le pidas que recuerde. |
| `companera/infrastructure/keyword_text_analyzer.py` | Reglas duras de palabras ("jefe", "python", "mamá"). | Era el analizador local cuando no había LLM. Ahora Gemini clasifica el ánimo y tema de forma infinitamente más inteligente. |
| `companera/application/phrases.py` | Frases fijas como *"¿Qué esperabas que hiciera el código?"*. | Innecesarias con Gemini activo; solo sirven de fallback si no hay internet. |

---

## 3. Diagnóstico: ¿Por qué solo usó dos imágenes durante la charla?

En tu prueba notaste que solo alternó entre dos imágenes (`calm` y `look`). Esto tiene una **causa técnica concreta en dos puntos del código**:

1. **La animación de espera:** En `companera/interface/desktop_pet.py` (línea 204), cada vez que mandás un mensaje, la UI cambia la cara automáticamente a **`look`** para simular que está pensando.
2. **El sesgo del prompt:** En `gemini_service.py`, la instrucción le dice:
   `[EXPR: calm] -> para respuestas normales, reflexivas, tranquilas.`
   Como el 90% de las respuestas son normales, Gemini casi siempre devolvía `[EXPR: calm]`.
3. **Resultado:** Tu pantalla solo vio: `calm` ➔ `look` (pensando) ➔ `calm` (respuesta) ➔ `look` ➔ `calm`.
4. **Assets sin aprovechar:** Existen en `companera/assets/sophia/` archivos como:
   - `face-smug.png` (pícara / confiada)
   - `face-laugh.png` (riendo / súper contenta)
   - `face-aside.png` (mirando de reojo / curiosa / analítica)
   - `face-wide.png` (sorprendida / ojos abiertos)
   - `face-many.png` (descolocada / cómica)
   - `cutin-*.png` (gráficos dinámicos con zoom a los ojos/boca)
   - `intro-*.webp` (animaciones con movimiento)

---

## 4. Plan de Acción Recomendado para la Nueva Etapa

1. **Limpieza Segura:**
   - Eliminar `index.html` obsoleto.
   - Retirar los 5 archivos de `companera/python context/`.
   - Aligerar referencias rígidas de tutoría en el prompt del sistema.
2. **Personalidad de Compañera:**
   - Definir a Sophia como compañera de escritorio: ingeniosa, atenta, presente.
   - Charla libre de cualquier tema personal o cotidiano + ayuda técnica natural cuando haga falta.
3. **Motor de Expresiones Dinámico:**
   - Reglas de emoción más expresivas en Gemini para que use con frecuencia `smug`, `laugh`, `aside`, `wide` y `many`.
   - Incorporar animaciones o transiciones más vivas.
4. **Comportamientos Vivos:**
   - Reacciones autónomas si pasa tiempo sin interacción.
   - Síntesis de voz opcional con Edge-TTS.
