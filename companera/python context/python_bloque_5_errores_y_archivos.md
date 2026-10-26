# Base de conocimiento de Python: Bloque 5 (Errores y archivos)

> **Formato (igual que los bloques anteriores):**
> - Cada entrada empieza con una línea `## termino` (nombre principal, en minúsculas).
> - La línea `- **alias:**` lista las otras palabras que deben llevar a esa entrada (sinónimos, plural, inglés, sin tildes).
> - Después vienen `**Qué es:**`, `**Ejemplo:**` y, si hace falta, `**Ojo con:**`.
> - Las entradas se separan con `---`.
> - Al buscar, conviene pasar lo que escribe el usuario a minúsculas y sin tildes, y compararlo con el nombre y los alias.

> **Plan de bloques:**
> 1. Fundamentos y tipos de datos (hecho)
> 2. Control de flujo (hecho)
> 3. Funciones (hecho)
> 4. Programación orientada a objetos (hecho)
> 5. Errores y archivos (este)
> 6. Módulos y biblioteca estándar (import, pip, datetime, random, re...)

**Índice de este bloque:** try except, excepciones comunes, traceback, raise, excepciones personalizadas, assert, logging, depurar, with, open, leer archivo, escribir archivo, encoding, json, csv, pathlib.

---

## try except
- **alias:** try except, try, except, excepcion, excepciones, manejo de errores, manejar errores, capturar error, atrapar error, else, finally, error, exception handling
- **categoria:** errores

**Qué es:** Permite que el programa **siga funcionando** cuando algo falla, en vez de cortarse con un error. El código que puede fallar va en `try`; si ocurre un error del tipo indicado, se ejecuta el bloque `except` correspondiente. Opcionalmente: `else` (corre solo si **no** hubo error) y `finally` (corre **siempre**, haya o no error).

**Ejemplo:**
```python
try:
    numero = int(input("Número: "))
    resultado = 10 / numero
except ValueError:
    print("Eso no es un número")
except ZeroDivisionError:
    print("No se puede dividir por cero")
else:
    print("Resultado:", resultado)      # solo si NO hubo error
finally:
    print("Esto se ejecuta siempre")    # con o sin error

try:
    ...
except (ValueError, TypeError) as error:   # varios tipos a la vez, y el error en una variable
    print("Falló:", error)
```

**Ojo con:** un `except:` a secas o un `except Exception: pass` **esconde** los errores y hace muy difícil encontrar fallas: capturá el tipo concreto que esperás. Los `except` se revisan en orden y gana el primero que coincide, así que los más específicos van primero. Mantené el `try` corto: solo las líneas que pueden fallar.

---

## excepciones comunes
- **alias:** excepciones comunes, errores comunes, tipos de errores, valueerror, typeerror, indexerror, keyerror, nameerror, attributeerror, zerodivisionerror, filenotfounderror, modulenotfounderror, syntaxerror, indentationerror, keyboardinterrupt, que significa el error
- **categoria:** errores

**Qué es:** Los errores más frecuentes y lo que significan. Cada uno es un tipo de excepción y se puede capturar con `except`.

**Ejemplo:**
```python
int("abc")             # ValueError: el tipo es correcto pero el valor no sirve
"a" + 1                # TypeError: operación entre tipos que no se pueden combinar
[1, 2, 3][5]           # IndexError: posición fuera de la lista
{"a": 1}["b"]          # KeyError: la clave no existe en el diccionario
10 / 0                 # ZeroDivisionError: división por cero
None.upper()           # AttributeError: el objeto no tiene ese atributo o método
print(variable_x)      # NameError: el nombre no está definido (¿error de tipeo?)
open("falta.txt")      # FileNotFoundError: el archivo no existe
import modulo_falso    # ModuleNotFoundError: el módulo no está instalado o no existe
```

**Significado rápido:** `SyntaxError` e `IndentationError` aparecen **antes** de ejecutar (el código está mal escrito o mal sangrado). `KeyboardInterrupt` ocurre cuando cortás el programa con `Ctrl + C`.

**Familias:** casi todos heredan de `Exception`, y algunos tienen un padre en común: `IndexError` y `KeyError` son `LookupError`, y `FileNotFoundError` es un `OSError`. Por eso `except LookupError` captura ambos.

**Ojo con:** el texto exacto del mensaje cambia entre versiones de Python; lo que importa es el **tipo** del error (la primera palabra).

---

## traceback
- **alias:** traceback, rastro del error, leer un error, como leer un error, pila de llamadas, stack trace, mensaje de error, error en consola, most recent call last
- **categoria:** errores

**Qué es:** El mensaje que Python muestra cuando ocurre un error sin capturar. Indica **dónde** pasó y **qué cadena de llamadas** llevó hasta ahí.

**Ejemplo:**
```text
Traceback (most recent call last):
  File "programa.py", line 8, in <module>
    resultado = calcular(0)
  File "programa.py", line 4, in calcular
    return 10 / n
ZeroDivisionError: division by zero
```

**Cómo leerlo:** de **abajo hacia arriba**. La última línea dice el tipo de error y el motivo (`ZeroDivisionError: division by zero`). Justo arriba está la línea exacta donde ocurrió (`programa.py`, línea 4, dentro de `calcular`). Más arriba están las llamadas que llevaron hasta ahí (el programa llamó a `calcular` en la línea 8).

**Ojo con:** el error suele estar en **tu** código, no en el de las bibliotecas que aparecen en el medio. Buscá la última línea que pertenezca a tus archivos. Las versiones recientes (3.11 en adelante) agregan debajo de cada línea unas marcas `^^^^` que señalan la parte exacta que falló.

---

## raise
- **alias:** raise, lanzar error, lanzar excepcion, levantar excepcion, provocar error, disparar error, relanzar, raise from
- **categoria:** errores

**Qué es:** Provoca un error a propósito. Se usa para avisar que algo no es válido, en lugar de seguir con datos incorrectos.

**Ejemplo:**
```python
def dividir(a, b):
    if b == 0:
        raise ValueError("El divisor no puede ser cero")
    return a / b

try:
    dividir(1, 0)
except ValueError as error:
    print(error)                   # El divisor no puede ser cero

try:
    int("x")
except ValueError as error:
    raise RuntimeError("No pude leer la configuración") from error   # encadena el error original
```

**Ojo con:** un `raise` solo, sin nada, dentro de un `except`, **vuelve a lanzar** el mismo error (útil para registrarlo y dejarlo seguir). Elegí el tipo de error que describa mejor el problema (`ValueError` si el valor es inválido, `TypeError` si el tipo es incorrecto).

---

## excepciones personalizadas
- **alias:** excepciones personalizadas, excepcion personalizada, error personalizado, crear excepcion, custom exception, propia excepcion, heredar de exception
- **categoria:** errores

**Qué es:** Una clase de error propia, creada heredando de `Exception`. Sirve para que un programa distinga sus errores específicos de los demás y los maneje con precisión.

**Ejemplo:**
```python
class SaldoInsuficienteError(Exception):
    """Se intentó retirar más dinero del disponible."""
    def __init__(self, saldo, monto):
        super().__init__(f"Saldo {saldo} insuficiente para retirar {monto}")
        self.saldo = saldo
        self.monto = monto

def retirar(saldo, monto):
    if monto > saldo:
        raise SaldoInsuficienteError(saldo, monto)
    return saldo - monto

try:
    retirar(50, 100)
except SaldoInsuficienteError as error:
    print(error)                   # Saldo 50 insuficiente para retirar 100
    print(error.monto)             # 100
```

**Ojo con:** por convención el nombre termina en `Error`. Alcanza con `class MiError(Exception): pass` si no necesitás datos extra. Para agrupar varios errores, creá una clase base propia y hacé que los demás hereden de ella.

---

## assert
- **alias:** assert, asercion, aserciones, afirmar, comprobar condicion, verificar, validar supuesto, assertionerror
- **categoria:** errores

**Qué es:** Comprueba que algo que **debería ser siempre cierto** realmente lo sea; si no, detiene el programa con un `AssertionError`. Sirve para detectar errores del programador durante el desarrollo.

**Ejemplo:**
```python
def promedio(numeros):
    assert len(numeros) > 0, "La lista no puede estar vacía"
    return sum(numeros) / len(numeros)

promedio([4, 6])      # 5.0
promedio([])          # AssertionError: La lista no puede estar vacía
```

**Ojo con:** si Python se ejecuta con la opción de optimización (`python -O`), los `assert` **se ignoran**. Por eso nunca los uses para validar datos que vienen del usuario o de afuera: para eso usá `if` y `raise`.

---

## logging
- **alias:** logging, log, logs, registro, registrar, bitacora, logger, nivel de log, debug, info, warning, error, critical, logging.exception
- **categoria:** errores

**Qué es:** El módulo estándar para registrar lo que hace un programa, con distintos niveles de importancia. Es mejor que llenar el código de `print`, porque se puede activar, filtrar y guardar en un archivo sin tocar el código.

**Ejemplo:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,                                   # desde qué nivel se muestra
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

logger.debug("Detalle técnico")        # no se ve: está por debajo de INFO
logger.info("Programa iniciado")
logger.warning("Quedan pocos recursos")
logger.error("No se pudo guardar")

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Falló una cuenta")   # registra el error CON su traceback
```

**Niveles, de menor a mayor:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

**Ojo con:** el nivel por defecto es `WARNING`, así que sin `basicConfig` los mensajes `info` y `debug` no aparecen. Para escribir en un archivo se agrega `filename="app.log"` en `basicConfig`.

---

## depurar
- **alias:** depurar, depuracion, debug, debugging, depurador, debugger, breakpoint, pdb, punto de interrupcion, encontrar el error, buscar bug, bug, print debugging
- **categoria:** errores

**Qué es:** El proceso de encontrar por qué un programa no hace lo esperado. Las herramientas, de la más simple a la más potente:

**Ejemplo:**
```python
# 1. Mostrar valores con print (rápido, pero hay que borrarlos después)
print("DEBUG total =", total)
print(f"{total=}")                # forma corta: imprime el nombre y el valor

# 2. breakpoint(): pausa el programa y abre el depurador en la consola
def calcular(lista):
    breakpoint()                  # el programa se detiene acá
    return sum(lista) / len(lista)
```

**Comandos del depurador (pdb):** `n` (siguiente línea), `s` (entrar en una función), `c` (continuar), `p variable` (ver su valor), `l` (ver el código cercano), `q` (salir).

**Alternativa visual:** los editores como VS Code tienen un depurador con puntos de corte (breakpoints) marcados con un clic al lado del número de línea, que muestra el valor de todas las variables en cada paso.

**Ojo con:** antes de depurar, leé bien el `traceback`: casi siempre indica la línea exacta. Y reducí el problema: probá con el ejemplo más chico que reproduzca el fallo.

---

## with
- **alias:** with, with open, context manager, administrador de contexto, gestor de contexto, bloque with, __enter__, __exit__, contextmanager, cerrar automaticamente
- **categoria:** archivos

**Qué es:** Una forma de usar un recurso (un archivo, una conexión) garantizando que se **cierre o libere correctamente al terminar**, incluso si ocurre un error en el medio.

**Ejemplo:**
```python
with open("datos.txt", "w", encoding="utf-8") as archivo:
    archivo.write("hola")
# acá el archivo ya está cerrado, pase lo que pase

# Dos recursos a la vez:
with open("origen.txt", encoding="utf-8") as entrada, open("copia.txt", "w", encoding="utf-8") as salida:
    salida.write(entrada.read())
```

**Ojo con:** sin `with`, hay que acordarse de llamar a `archivo.close()`, y si ocurre un error antes de cerrarlo, queda abierto. Por eso `with` es la forma recomendada. Para crear tus propios gestores se puede usar `@contextlib.contextmanager` o definir `__enter__` y `__exit__`.

---

## open
- **alias:** open, abrir archivo, abrir, modos de apertura, modo r, modo w, modo a, modo x, modo rb, modo wb, binario, archivo, archivos, file, fileexistserror
- **categoria:** archivos

**Qué es:** La función que abre un archivo y devuelve un objeto para leerlo o escribirlo. Sintaxis: `open(ruta, modo, encoding="utf-8")`.

**Modos principales:**
- `"r"`: leer (es el modo por defecto; da `FileNotFoundError` si no existe).
- `"w"`: escribir; **borra todo el contenido anterior** y crea el archivo si no existe.
- `"a"`: agregar al final, sin borrar lo que ya había.
- `"x"`: crear un archivo nuevo; da `FileExistsError` si ya existe.
- `"b"` se suma a los anteriores para archivos binarios (`"rb"`, `"wb"`): imágenes, PDF, etc.

**Ejemplo:**
```python
with open("notas.txt", "w", encoding="utf-8") as f:    # crea o sobrescribe
    f.write("primera línea\n")

with open("notas.txt", "a", encoding="utf-8") as f:    # agrega al final
    f.write("segunda línea\n")

with open("notas.txt", "r", encoding="utf-8") as f:    # lee
    contenido = f.read()
```

**Ojo con:** el modo `"w"` **destruye** el contenido existente sin avisar: si querés conservar lo anterior, usá `"a"`. Indicá siempre `encoding="utf-8"` en archivos de texto (ver `encoding`).

---

## leer archivo
- **alias:** leer archivo, leer, read, readline, readlines, leer lineas, leer linea por linea, recorrer archivo, contenido de un archivo, leer texto
- **categoria:** archivos

**Qué es:** Las formas de obtener el contenido de un archivo de texto abierto.

**Ejemplo:**
```python
with open("notas.txt", encoding="utf-8") as f:
    todo = f.read()              # TODO el contenido en un solo texto

with open("notas.txt", encoding="utf-8") as f:
    primera = f.readline()       # una sola línea (incluye el "\n" del final)

with open("notas.txt", encoding="utf-8") as f:
    lineas = f.readlines()       # lista con todas las líneas

with open("notas.txt", encoding="utf-8") as f:
    for linea in f:              # la mejor forma para archivos grandes
        print(linea.rstrip("\n"))   # rstrip quita el salto de línea del final
```

**Ojo con:** `read()` y `readlines()` cargan todo en memoria: con archivos muy grandes, recorré el archivo con `for linea in f`, que lee de a una línea. Cada línea leída trae el `"\n"` al final. Una vez recorrido el archivo, un segundo `read()` devuelve texto vacío (el cursor ya llegó al final).

---

## escribir archivo
- **alias:** escribir archivo, escribir, write, writelines, guardar en archivo, guardar texto, agregar al archivo, crear archivo, salida a archivo
- **categoria:** archivos

**Qué es:** Las formas de guardar texto en un archivo.

**Ejemplo:**
```python
with open("salida.txt", "w", encoding="utf-8") as f:
    f.write("primera línea\n")              # write NO agrega salto de línea solo
    f.writelines(["a\n", "b\n"])            # escribe una lista de textos (tampoco agrega "\n")
    print("tercera línea", file=f)          # print sí agrega el salto de línea
```

**Ojo con:** `write` solo acepta texto: para guardar un número usá `f.write(str(5))`. Si el programa se corta antes de cerrar el archivo, puede perderse lo último que se escribió: otro motivo para usar `with`. En modo `"w"` cada ejecución reemplaza el archivo completo.

---

## encoding
- **alias:** encoding, codificacion, utf-8, utf8, tildes, enie, caracteres raros, acentos, unicodedecodeerror, unicodeencodeerror, bom, utf-8-sig, caracteres especiales
- **categoria:** archivos

**Qué es:** La "tabla" que traduce entre los caracteres (como `á`, `ñ` o `€`) y los bytes guardados en el archivo. El estándar actual es **UTF-8**. Si se lee un archivo con una codificación distinta de la que se usó al escribirlo, aparecen símbolos raros (`Ã±` en vez de `ñ`) o un error.

**Ejemplo:**
```python
with open("texto.txt", "w", encoding="utf-8") as f:
    f.write("Año nuevo, vida nueva")

with open("texto.txt", "r", encoding="utf-8") as f:
    print(f.read())                           # Año nuevo, vida nueva

with open("viejo.txt", encoding="utf-8", errors="replace") as f:   # no falla: cambia lo ilegible por el símbolo �
    texto = f.read()
```

**Ojo con:** si no indicás `encoding`, Python usa la configuración del sistema, que en Windows muchas veces **no es UTF-8**: lo que funciona en una computadora puede fallar en otra. Por eso conviene escribir siempre `encoding="utf-8"`. Un `UnicodeDecodeError` casi siempre significa que el archivo está en otra codificación: probá con `"latin-1"` o `"cp1252"`. Para CSV que se van a abrir con Excel, `encoding="utf-8-sig"` evita problemas con las tildes.

---

## json
- **alias:** json, jsondecodeerror, dumps, loads, dump, load, serializar, deserializar, guardar diccionario, guardar datos, formato json, indent, ensure_ascii
- **categoria:** archivos

**Qué es:** Un formato de texto muy usado para guardar y compartir datos estructurados. El módulo `json` convierte diccionarios y listas de Python a texto JSON y viceversa.

**Ejemplo:**
```python
import json

datos = {"nombre": "Ana", "edad": 30, "activo": True, "notas": [8, 9]}

texto = json.dumps(datos, ensure_ascii=False, indent=2)   # objeto -> texto
original = json.loads(texto)                               # texto -> objeto

with open("datos.json", "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=2)      # objeto -> archivo

with open("datos.json", encoding="utf-8") as f:
    cargado = json.load(f)                                 # archivo -> objeto
```

**Regla fácil:** las funciones con **s** al final (`dumps`, `loads`) trabajan con **textos** (string); las que no la tienen (`dump`, `load`) trabajan con **archivos**.

**Equivalencias:** `dict` ↔ objeto, `list` ↔ arreglo, `True` ↔ `true`, `None` ↔ `null`.

**Ojo con:** sin `ensure_ascii=False`, las tildes y la `ñ` se guardan como códigos (`\u00f1`). Las claves siempre se convierten a texto, las tuplas pasan a listas, y los `set` y las fechas (`datetime`) **no se pueden guardar directamente** (dan `TypeError`): hay que convertirlos antes, por ejemplo `fecha.isoformat()` o `list(conjunto)`. Un JSON mal formado da `json.JSONDecodeError`.

---

## csv
- **alias:** csv, archivo csv, excel, planilla, tabla, hoja de calculo, dictreader, dictwriter, csv.reader, csv.writer, delimitador, separador, punto y coma
- **categoria:** archivos

**Qué es:** Un formato de texto para tablas: una fila por línea y las columnas separadas por un delimitador. El módulo `csv` lo lee y lo escribe correctamente (maneja comillas y comas dentro de los datos).

**Ejemplo:**
```python
import csv

with open("personas.csv", "w", newline="", encoding="utf-8") as f:
    escritor = csv.writer(f)
    escritor.writerow(["nombre", "edad"])        # fila de encabezados
    escritor.writerow(["Ana", 30])
    escritor.writerow(["Luis", 25])

with open("personas.csv", newline="", encoding="utf-8") as f:
    for fila in csv.DictReader(f):               # cada fila llega como diccionario
        print(fila["nombre"], int(fila["edad"]))
```

**Ojo con:** al abrir el archivo hay que pasar `newline=""`; si no, en Windows aparecen líneas en blanco de más. **Todos los valores se leen como texto**: `"30"` y no `30`, hay que convertir con `int()` o `float()`. Los CSV creados con Excel en configuración regional hispana suelen usar **punto y coma** como separador: se indica con `csv.reader(f, delimiter=";")`.

---

## pathlib
- **alias:** pathlib, path, ruta, rutas, ruta de archivo, carpeta, directorio, directorios, os.path, existe archivo, crear carpeta, listar archivos, glob, nombre de archivo, extension
- **categoria:** archivos

**Qué es:** El módulo moderno para trabajar con rutas de archivos y carpetas. Un objeto `Path` representa una ruta y se combina con el operador `/`, sin preocuparse por si el sistema usa `\` (Windows) o `/` (Linux y Mac).

**Ejemplo:**
```python
from pathlib import Path

carpeta = Path("datos")
archivo = carpeta / "notas.txt"           # une las partes de la ruta con "/"

carpeta.mkdir(parents=True, exist_ok=True)   # crea la carpeta si no existe, sin error si ya está
archivo.write_text("hola", encoding="utf-8")
archivo.read_text(encoding="utf-8")       # "hola"

archivo.exists()                          # True
archivo.is_file()                         # True
archivo.name                              # "notas.txt"
archivo.stem                              # "notas"      (nombre sin extensión)
archivo.suffix                            # ".txt"
archivo.parent                            # Path("datos")

for f in carpeta.glob("*.txt"):           # lista los archivos .txt de la carpeta
    print(f)

Path.cwd()                                # carpeta de trabajo actual
Path.home()                               # carpeta personal del usuario
Path(__file__).parent                     # carpeta donde está el script que se ejecuta
archivo.unlink()                          # borra el archivo
```

**Ojo con:** una ruta relativa como `"datos/notas.txt"` se interpreta desde la carpeta **desde donde se ejecuta** el programa, no desde donde está el script: por eso `Path(__file__).parent` es muy útil para ubicar archivos junto al código. Un `Path` no es un texto: si una función antigua pide `str`, convertilo con `str(ruta)`.
