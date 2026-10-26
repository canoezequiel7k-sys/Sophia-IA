# Base de conocimiento de Python: Bloque 1 (Fundamentos y tipos de datos)

> **Formato (importante para que tu IA lo pueda leer):**
> - Cada entrada empieza con una línea `## termino` (el nombre principal, en minúsculas).
> - La línea `- **alias:**` lista las otras palabras que deben llevar a esa entrada (sinónimos, plural, inglés, sin tildes).
> - Después vienen `**Qué es:**`, `**Ejemplo:**` y, si hace falta, `**Ojo con:**`.
> - Las entradas se separan con `---`.
> - Al buscar, conviene pasar lo que escribe el usuario a minúsculas y sin tildes, y compararlo con el nombre y los alias.

> **Plan de bloques:**
> 1. Fundamentos y tipos de datos (este)
> 2. Control de flujo (if, for, while, comprensiones)
> 3. Funciones (def, argumentos, lambda, decoradores, generadores)
> 4. Programación orientada a objetos (clases, herencia, dataclass)
> 5. Errores y archivos (try/except, with/open, json, pathlib)
> 6. Módulos y biblioteca estándar (import, pip, datetime, random, re...)

**Índice de este bloque:** variable, tipos de datos, string, int, float, bool, none, list, tuple, dict, set, conversion de tipos, print, input, operadores, comentarios.

---

## variable
- **alias:** variable, variables, asignacion, asignar, nombre de variable, tipado dinamico
- **categoria:** fundamentos

**Qué es:** Un nombre que apunta a un valor guardado en memoria. Se crea al asignar con `=`. No se declara el tipo: Python lo deduce (tipado dinámico), y el mismo nombre puede apuntar después a un valor de otro tipo.

**Ejemplo:**
```python
edad = 30            # int
nombre = "Ana"       # str
a, b = 1, 2          # asignación múltiple
a, b = b, a          # intercambiar valores sin variable auxiliar
```

**Reglas de nombres:** pueden tener letras, números y guion bajo; no pueden empezar con número ni ser palabras reservadas (`if`, `for`, `class`...); distinguen mayúsculas (`edad` y `Edad` son distintas). Convención: `snake_case` para variables (`mi_variable`) y MAYÚSCULAS para constantes (`PI`).

**Ojo con:** dos nombres pueden apuntar al mismo objeto mutable (ver `list`), y modificarlo por uno lo cambia para el otro.

---

## tipos de datos
- **alias:** tipo, tipos, tipo de dato, tipos de datos, type, isinstance, tipado, mutable, inmutable
- **categoria:** fundamentos

**Qué es:** Todo valor tiene un tipo que define qué se puede hacer con él. Básicos: `int`, `float`, `bool`, `str`, `NoneType`. Colecciones: `list`, `tuple`, `dict`, `set`. `type(x)` devuelve el tipo y `isinstance(x, tipo)` pregunta si el valor es de ese tipo (es lo preferido).

**Ejemplo:**
```python
type(5)                  # <class 'int'>
type("hola")             # <class 'str'>
isinstance(3.5, float)   # True
```

**Mutables e inmutables:** los mutables (`list`, `dict`, `set`) se pueden modificar en el lugar. Los inmutables (`int`, `float`, `bool`, `str`, `tuple`) no: "modificarlos" crea un valor nuevo.

**Ojo con:** `isinstance(True, int)` da `True`, porque `bool` es un tipo de `int`.

---

## string
- **alias:** string, strings, str, cadena, cadenas, cadena de texto, texto, f-string, fstring, comillas
- **categoria:** tipos de datos

**Qué es:** Una secuencia de caracteres, es decir, texto. Se escribe entre comillas simples `'...'`, dobles `"..."` o triples `"""..."""` (para varias líneas). Es **inmutable**: sus métodos no la modifican, devuelven una nueva.

**Ejemplo:**
```python
nombre = "Ana"
saludo = f"Hola, {nombre}"      # f-string: inserta variables dentro del texto
print(saludo)                    # Hola, Ana

texto = "  Python es genial  "
texto.strip()                    # "Python es genial"  (quita espacios de los bordes)
texto.upper()                    # "  PYTHON ES GENIAL  "
texto.replace("genial", "útil")  # reemplaza una parte
"a,b,c".split(",")               # ["a", "b", "c"]
"-".join(["a", "b", "c"])        # "a-b-c"
```

**Índices y cortes (slicing):** el primer carácter es el 0 y el último es el -1.
```python
palabra = "python"
palabra[0]       # "p"
palabra[-1]      # "n"
palabra[1:4]     # "yth"   (desde el 1 hasta antes del 4)
palabra[::-1]    # "nohtyp" (al revés)
len(palabra)     # 6
"th" in palabra  # True
```

**Métodos frecuentes:** `upper`, `lower`, `title`, `capitalize`, `strip`, `split`, `join`, `replace`, `find`, `count`, `startswith`, `endswith`, `isdigit`.

**Otras cosas útiles:** concatenar con `+` (`"a" + "b"`), repetir con `*` (`"ab" * 3`), caracteres especiales con `\n` (salto de línea) y `\t` (tabulación), y texto "crudo" con `r"C:\carpeta"`.

**Ojo con:** `palabra[0] = "X"` da `TypeError`, porque no se puede modificar un carácter. Tampoco se puede sumar texto con número (`"edad: " + 30` falla): usá `f"edad: {30}"` o `str(30)`.

---

## int
- **alias:** int, entero, enteros, numero entero, integer, division entera, modulo, potencia
- **categoria:** tipos de datos

**Qué es:** Un número entero, sin decimales y sin límite de tamaño (puede ser tan grande como la memoria permita).

**Ejemplo:**
```python
a = 7
a + 2        # 9
a - 2        # 5
a * 2        # 14
a / 2        # 3.5   (la división "/" siempre da float)
a // 2       # 3     (división entera)
a % 2        # 1     (resto o módulo)
a ** 2       # 49    (potencia)
divmod(a, 2) # (3, 1) cociente y resto juntos
1_000_000    # los guiones bajos ayudan a leer números grandes
```

**Ojo con:** `int("3.5")` da error: primero hay que pasar por `float`, es decir `int(float("3.5"))`, y el resultado es 3 (corta, no redondea).

---

## float
- **alias:** float, flotante, flotantes, decimal, decimales, numero decimal, coma flotante, redondear, round
- **categoria:** tipos de datos

**Qué es:** Un número con parte decimal. Se escribe con punto: `3.14`.

**Ejemplo:**
```python
precio = 19.99
round(precio, 1)     # 20.0
round(2.675, 2)      # 2.67 (ver "Ojo con")
10 / 4               # 2.5
import math
math.isclose(0.1 + 0.2, 0.3)   # True: forma correcta de comparar floats
```

**Ojo con:** los floats son aproximados por cómo se guardan en binario: `0.1 + 0.2` da `0.30000000000000004`, y por eso `0.1 + 0.2 == 0.3` es `False`. Para dinero o cálculos exactos se usa el módulo `decimal`.

---

## bool
- **alias:** bool, booleano, booleanos, boolean, verdadero, falso, true, false, truthy, falsy
- **categoria:** tipos de datos

**Qué es:** Un valor lógico: `True` o `False` (con mayúscula inicial). Resulta de comparaciones y se usa en condiciones.

**Ejemplo:**
```python
5 > 3                # True
"a" == "b"           # False
x = 5
x > 0 and x < 10     # True
not x > 0            # False
```

**Valores "falsos" (falsy):** se consideran `False` en una condición el `0`, `0.0`, `""` (texto vacío), `[]`, `{}`, `set()` y `None`. Todo lo demás se considera `True`.
```python
if lista:            # equivale a "si la lista no está vacía"
    print("tiene elementos")
```

**Ojo con:** `True == 1` y `False == 0` dan `True`, porque `bool` es un tipo de `int`.

---

## none
- **alias:** none, nulo, null, nada, sin valor, nonetype, vacio
- **categoria:** tipos de datos

**Qué es:** El valor que representa "ausencia de valor". Su tipo es `NoneType` y existe un único `None`. Una función que no devuelve nada con `return` devuelve `None`.

**Ejemplo:**
```python
resultado = None
if resultado is None:        # se compara con "is", no con "=="
    print("todavía no hay resultado")

def saludar():
    print("hola")

x = saludar()                # imprime "hola"
print(x)                     # None
```

**Ojo con:** `None` no es lo mismo que `0` ni que `""`. Para comprobarlo se usa `is None` o `is not None`.

---

## list
- **alias:** list, lista, listas, arreglo, array, append, sort, sorted, slice de lista
- **categoria:** colecciones

**Qué es:** Una colección **ordenada** y **mutable** de elementos, que pueden ser de distintos tipos. Se escribe con corchetes.

**Ejemplo:**
```python
frutas = ["manzana", "pera"]
frutas.append("uva")             # agrega al final
frutas.insert(0, "kiwi")         # agrega en una posición
frutas.remove("pera")            # quita por valor
ultimo = frutas.pop()            # quita y devuelve el último
frutas[0]                        # "kiwi"
frutas[0:2]                      # corte, igual que en string
len(frutas)                      # cantidad de elementos
"kiwi" in frutas                 # True

numeros = [3, 1, 2]
numeros.sort()                   # ordena en el lugar -> [1, 2, 3]
sorted([3, 1, 2], reverse=True)  # devuelve una lista nueva -> [3, 2, 1]
```

**Métodos frecuentes:** `append`, `extend`, `insert`, `remove`, `pop`, `index`, `count`, `sort`, `reverse`, `copy`, `clear`.

**Ojo con:** `b = a` NO copia la lista, hace que ambos nombres apunten a la misma. Para copiar usá `b = a.copy()` o `b = a[:]`. Además, `.sort()` devuelve `None` (modifica la lista, no devuelve una nueva).

---

## tuple
- **alias:** tuple, tupla, tuplas, desempaquetado, unpacking
- **categoria:** colecciones

**Qué es:** Como una lista pero **inmutable**: una vez creada no se pueden agregar ni cambiar elementos. Se escribe con paréntesis y se usa para datos fijos, como coordenadas.

**Ejemplo:**
```python
punto = (3, 4)
punto[0]                 # 3
x, y = punto             # desempaquetado: x=3, y=4
unico = (5,)             # tupla de un solo elemento (la coma es obligatoria)
```

**Ojo con:** `(5)` es solo el número 5 entre paréntesis, no una tupla. Como son inmutables y "hashables", pueden usarse como claves de un diccionario, cosa que las listas no pueden.

---

## dict
- **alias:** dict, diccionario, diccionarios, dictionary, clave valor, key value, llave, json de python, get, items
- **categoria:** colecciones

**Qué es:** Una colección de pares **clave: valor**. Se accede a cada valor por su clave, no por posición. Desde Python 3.7 mantiene el orden en que se insertan los elementos.

**Ejemplo:**
```python
persona = {"nombre": "Ana", "edad": 30}
persona["nombre"]                 # "Ana"
persona["ciudad"] = "Lima"        # agrega o modifica
persona.get("pais", "sin dato")   # "sin dato" (valor por defecto si no existe)
"edad" in persona                 # True (pregunta por claves)
del persona["edad"]               # elimina una clave

for clave, valor in persona.items():
    print(clave, valor)
```

**Métodos frecuentes:** `get`, `keys`, `values`, `items`, `update`, `pop`, `setdefault`, `copy`.

**Ojo con:** `persona["pais"]` da `KeyError` si la clave no existe: usá `.get()` si no estás seguro. Las claves deben ser inmutables (texto, números, tuplas), no listas.

---

## set
- **alias:** set, conjunto, conjuntos, sets, union, interseccion, diferencia, sin repetidos, unicos
- **categoria:** colecciones

**Qué es:** Una colección **sin orden** y **sin elementos repetidos**. Sirve para eliminar duplicados y para operaciones de conjuntos.

**Ejemplo:**
```python
a = {1, 2, 3}
b = {3, 4}
a | b              # unión: {1, 2, 3, 4}
a & b              # intersección: {3}
a - b              # diferencia: {1, 2}
a.add(5)           # agrega un elemento
a.discard(99)      # quita sin dar error si no está
set([1, 1, 2, 2])  # {1, 2}  (quitar repetidos de una lista)
vacio = set()
```

**Ojo con:** `{}` crea un **diccionario** vacío, no un conjunto: para un conjunto vacío usá `set()`. Como no tiene orden, no se accede por índice (`a[0]` falla).

---

## conversion de tipos
- **alias:** conversion de tipos, convertir, casting, cast, int(), float(), str(), bool(), pasar a numero, pasar a texto, valueerror
- **categoria:** fundamentos

**Qué es:** Cambiar un valor de un tipo a otro usando el nombre del tipo como función.

**Ejemplo:**
```python
int("42")          # 42
float("3.5")       # 3.5
str(100)           # "100"
bool(0)            # False
list("hola")       # ["h", "o", "l", "a"]
tuple([1, 2])      # (1, 2)
set([1, 1, 2])     # {1, 2}
dict([("a", 1)])   # {"a": 1}
```

**Ojo con:** si el valor no se puede convertir, da `ValueError` (por ejemplo `int("hola")`). Si viene del usuario, conviene validarlo con `try/except` (ver bloque de errores).

---

## print
- **alias:** print, imprimir, mostrar, mostrar en pantalla, salida, sep, end
- **categoria:** entrada y salida

**Qué es:** La función que muestra texto o valores en la consola.

**Ejemplo:**
```python
print("Hola")                    # Hola
print("a", "b", "c")             # a b c
print("a", "b", sep="-")         # a-b
print("sin salto", end="")       # no agrega salto de línea al final
nombre = "Ana"
print(f"Hola, {nombre}")         # forma más cómoda de mezclar texto y variables
```

**Ojo con:** `print` solo muestra, no devuelve el valor (devuelve `None`).

---

## input
- **alias:** input, entrada, leer, pedir dato, teclado, preguntar al usuario, entrada de usuario
- **categoria:** entrada y salida

**Qué es:** La función que espera a que el usuario escriba algo y lo devuelve **siempre como texto** (`str`).

**Ejemplo:**
```python
nombre = input("¿Cómo te llamás? ")
edad = int(input("¿Cuántos años tenés? "))   # hay que convertir a mano
print(f"{nombre}, el año que viene tendrás {edad + 1}")
```

**Ojo con:** aunque el usuario escriba `25`, `input` devuelve `"25"` (texto). Si no lo convertís con `int()` o `float()`, no podés hacer cuentas. Y si escribe algo que no es número, `int()` da `ValueError`.

---

## operadores
- **alias:** operador, operadores, aritmeticos, comparacion, logicos, and, or, not, in, is, igual, distinto, mayor, menor
- **categoria:** fundamentos

**Qué es:** Símbolos o palabras que combinan valores.

**Ejemplo:**
```python
# Aritméticos:   +  -  *  /  //  %  **
# Comparación:   ==  !=  <  >  <=  >=       -> dan True o False
# Lógicos:       and  or  not
# Pertenencia:   in  not in                 -> "a" in "casa" es True
# Identidad:     is  is not                 -> mismo objeto en memoria
# Asignación:    =  +=  -=  *=  /=

x = 10
x += 5            # equivale a x = x + 5
1 < x < 20        # True: las comparaciones se pueden encadenar
```

**Ojo con:** `==` compara **valores** (¿son iguales?) y `is` compara **identidad** (¿son el mismo objeto?). Para valores se usa `==`; `is` se reserva para `None`. Confundir `=` (asignar) con `==` (comparar) es un error muy común.

---

## comentarios
- **alias:** comentario, comentarios, docstring, documentacion, almohadilla, numeral, hashtag
- **categoria:** fundamentos

**Qué es:** Texto que Python ignora y que sirve para explicar el código. Una línea que empieza con `#` es un comentario. El texto entre triples comillas al comienzo de una función, clase o archivo se llama **docstring** y documenta para qué sirve.

**Ejemplo:**
```python
# Esto es un comentario de una línea
edad = 30   # también se puede poner al final de una línea

def duplicar(n):
    """Devuelve el doble del número recibido."""
    return n * 2
```

**Buena práctica:** el comentario debería explicar el **por qué** de algo, no repetir lo que el código ya dice.
