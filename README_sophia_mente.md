# Luma — mente simple (Python, sin dependencias, sin internet)

Te pregunta cómo estás, entiende tu respuesta con reglas simples y la recuerda
para la próxima vez. La conversación se guarda en `data/memoria.json` (podés
abrirlo y editarlo). La página `index.html` es la cara animada independiente.

    python main.py        # requiere Python 3.10 o superior

Escribí cómo te sentís y terminá con `salir`. La memoria se crea al guardar la
primera respuesta; no hace falta instalar paquetes ni conectarse a internet.

## Mapa de capas (las flechas son "depende de")

    interface ──► application ──► domain
    infrastructure ──► application ──► domain
    main.py conoce a todas y las enchufa entre sí.

| Capa | Qué contiene | Cambia cuando... |
|---|---|---|
| `companera/domain/` | Mood, Topic, CheckIn | cambia el concepto de "recuerdo" |
| `companera/application/` | casos de uso, puertos, frases | cambian las reglas o su personalidad |
| `companera/infrastructure/` | JSON, reloj, intérprete por palabras | cambia cómo se guarda o interpreta |
| `companera/interface/` | consola | cambia cómo se muestra (ej.: la cara) |

## Dónde tocar según lo que quieras
- **Que hable distinto:** `companera/application/phrases.py`.
- **Que entienda más palabras o temas:** `companera/infrastructure/keyword_text_analyzer.py`.
- **Que use un modelo de lenguaje:** nueva clase que cumpla `TextAnalyzer`; cambiar 1 línea en `main.py`.
- **Conectar la consola a la cara animada:** integrar una interfaz web con los mismos casos de uso;
  `CompanionReply.user_mood` ya trae el ánimo detectado.
