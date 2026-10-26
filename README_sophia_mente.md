# Sophia IA — asistente local en Python

Sophia IA es una aplicación de terminal pequeña para dejar abierta en una segunda
pantalla. Conversa en español con reglas sencillas, hace preguntas de seguimiento
y guarda cada intercambio en `data/memoria.json`. Reconoce algunos temas de Python
y pide datos útiles para revisar errores. No usa APIs, internet ni paquetes
externos. Requiere Python 3.10 o superior.

## Iniciar

- Windows: abrí `iniciar_sophia_ia.bat` con doble clic.
- Terminal: ejecutá `python main.py` desde la carpeta del proyecto.

Escribí qué querés resolver. Sophia IA contestará y te hará una pregunta relacionada; escribí
`salir` para cerrar. Los comandos disponibles son:

- `/ayuda`: mostrar comandos.
- `/memoria`: ver los intercambios guardados.
- `/borrar`: borrar todos los recuerdos (pide confirmación).

La entrada no distingue mayúsculas ni tildes para comandos y respuestas sencillas.
Podés saludar, agradecer, responder que no necesitás más ayuda para cerrar, o
pedir explícitamente que abra Windows Terminal.

Comandos rápidos: `sop -help` muestra esta ayuda, `clear` limpia la terminal
(sin borrar recuerdos), `sop -close` cierra Sophia, `sop -new` abre otra sesión
de Sophia y `sop -terminal` abre una terminal nueva de Windows.

También podés preguntar por un tema de tus apuntes, por ejemplo `Estoy viendo
Strings`. Sophia busca en los archivos `.md` de `companera/python context/`,
te muestra una explicación breve y pregunta si querés ver la entrada completa.
Respondé `sí` o `no`. Las consultas y respuestas de conocimiento también se
guardan en el historial.

La memoria es un archivo local de texto legible. Guarda lo que escribís y las
respuestas de Sophia IA; no se envía a ningún servicio. Si querés empezar de cero,
usá `/borrar`. También podés inspeccionar el archivo `data/memoria.json`.

## Alcance actual

Esta es una base conversacional local, **no un modelo de lenguaje**. El documento
`README_contexto_IA_Python.md` define el enfoque de tutoría para el proyecto; sin
un modelo, Sophia IA todavía no puede leer código ni aplicar por sí sola todo ese
contexto. Reconoce palabras y responde con frases preparadas. La interfaz animada
de `index.html` no está conectada y queda para una etapa futura.

## Capas

    interface ──► application ──► domain
    infrastructure ──► domain
    main.py es la raíz de composición y conecta las piezas.

Las dependencias de código apuntan hacia el núcleo. `application` define puertos
(protocolos) que los adaptadores externos cumplen; infraestructura no importa
la interfaz ni los casos de uso. Así se pueden sustituir el analizador, el
almacenamiento o la consola sin meter esos detalles en las reglas del núcleo.

| Carpeta/archivo | Responsabilidad |
|---|---|
| `companera/domain/` | estados de ánimo, temas e intercambios |
| `companera/application/` | conversación, preguntas y puertos |
| `companera/infrastructure/` | análisis por palabras, búsqueda Markdown y memoria JSON |
| `companera/interface/` | terminal y comandos interactivos |
| `main.py` | construcción e inyección de implementaciones concretas |

## Pruebas

Desde la carpeta del proyecto:

    python -m unittest discover -s tests -v

## Próximas mejoras

1. Fortalecer dominio y casos de uso con pruebas y comportamiento conversacional explícito.
2. Mejorar la memoria detrás del puerto sin acoplarla a los casos de uso.
3. Incorporar tutoría de Python guiada por el contexto del proyecto; el analizador
   actual solo detecta palabras, no interpreta código.
4. Evaluar otras interfaces más adelante. La cara animada queda fuera del alcance actual.
