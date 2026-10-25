# Luma — mente simple (Python, sin dependencias, sin internet)

Te pregunta cómo estás, entiende tu respuesta con reglas simples y la recuerda
para la próxima vez. Todo se guarda en `data/memoria.json` (podés abrirlo y editarlo).

    python main.py        # requiere Python 3.9 o superior

## Mapa de capas (las flechas son "depende de")

    interface ──► application ──► domain
    infrastructure ──► application ──► domain
    main.py conoce a todas y las enchufa entre sí.

| Capa | Qué contiene | Cambia cuando... |
|---|---|---|
| `domain/` | Mood, Topic, CheckIn | cambia el concepto de "recuerdo" |
| `application/` | casos de uso, puertos, frases | cambian las reglas o su personalidad |
| `infrastructure/` | JSON, reloj, intérprete por palabras | cambia cómo se guarda o interpreta |
| `interface/` | consola | cambia cómo se muestra (ej.: la cara) |

## Dónde tocar según lo que quieras
- **Que hable distinto:** `application/phrases.py`.
- **Que entienda más palabras o temas:** `infrastructure/keyword_text_analyzer.py`.
- **Que use un modelo de lenguaje:** nueva clase que cumpla `TextAnalyzer`; cambiar 1 línea en `main.py`.
- **Conectarla a la cara animada:** nueva interfaz que use los mismos casos de uso;
  `CompanionReply.user_mood` ya trae el ánimo detectado.
