# Base de conocimiento de Python: Bloque 2 (Control de flujo)

> **Formato (igual que el bloque 1):**
> - Cada entrada empieza con una línea `## termino` (nombre principal, en minúsculas).
> - La línea `- **alias:**` lista las otras palabras que deben llevar a esa entrada (sinónimos, plural, inglés, sin tildes).
> - Después vienen `**Qué es:**`, `**Ejemplo:**` y, si hace falta, `**Ojo con:**`.
> - Las entradas se separan con `---`.
> - Al buscar, conviene pasar lo que escribe el usuario a minúsculas y sin tildes, y compararlo con el nombre y los alias.

> **Plan de bloques:**
> 1. Fundamentos y tipos de datos (hecho)
> 2. Control de flujo (este)
> 3. Funciones (def, argumentos, lambda, decoradores, generadores)
> 4. Programación orientada a objetos (clases, herencia, dataclass)
> 5. Errores y archivos (try/except, with/open, json, pathlib)
> 6. Módulos y biblioteca estándar (import, pip, datetime, random, re...)

**Índice de este bloque:** indentacion, if, ternario, for, range, enumerate, zip, while, break, continue, pass, else en bucles, iterable, comprension de listas, comprension de diccionarios y conjuntos, match.

---

## indentacion
- **alias:** indentacion, identacion, sangria, espacios, bloque, bloques, dos puntos, indentationerror, taberror
- **categoria:** control de flujo

**Qué es:** En Python los bloques de código (lo que va dentro de un `if`, un `for`, una función...) se marcan con **sangría**, no con llaves. La línea que abre el bloque termina en `:` y las siguientes se escriben más a la derecha, todas con la misma sangría. La convención es **4 espacios**.

**Ejemplo:**
```python
edad = 20
if edad >= 18:
    print("mayor de edad")       # dentro del if (4 espacios)
    print("puede votar")         # sigue dentro
print("esto va siempre")         # fuera del if
```

**Ojo con:** si la sangría es inconsistente da `IndentationError`. Mezclar tabuladores con espacios también da error (`TabError`): elegí uno solo, de preferencia espacios.

---

## if
- **alias:** if, elif, else, condicional, condicionales, condicion, si entonces, si no, sino, decision, bifurcacion
- **categoria:** control de flujo

**Qué es:** Ejecuta un bloque solo si una condición es verdadera. `elif` agrega más condiciones y `else` cubre el resto. Se evalúan en orden y se ejecuta **solo la primera** que se cumpla.

**Ejemplo:**
```python
nota = 7
if nota >= 9:
    print("excelente")
elif nota >= 6:
    print("aprobado")
else:
    print("desaprobado")         # imprime "aprobado"

if 0 < nota <= 10:               # comparación encadenada
    print("nota válida")

lista = []
if not lista:                    # una lista vacía cuenta como falsa
    print("no hay elementos")
```

**Ojo con:** no te olvides los dos puntos `:` ni la sangría. Para comparar se usa `==`, no `=` (que asigna).

---

## ternario
- **alias:** ternario, operador ternario, expresion condicional, if en una linea, if en linea, if inline
- **categoria:** control de flujo

**Qué es:** Una forma de escribir un `if/else` sencillo en una sola línea que produce un valor. Sintaxis: `valor_si_cierto if condicion else valor_si_falso`.

**Ejemplo:**
```python
edad = 20
estado = "mayor" if edad >= 18 else "menor"
print(estado)                    # mayor
```

**Ojo con:** úsalo solo para casos simples. Si necesitás más de una condición o varias acciones, es más claro un `if` normal.

---

## for
- **alias:** for, bucle for, ciclo for, ciclo, bucle, bucles, recorrer, iterar, iteracion, bucles anidados, for in
- **categoria:** control de flujo

**Qué es:** Recorre uno por uno los elementos de algo "iterable" (lista, texto, diccionario, `range`...) y ejecuta el bloque para cada uno.

**Ejemplo:**
```python
for fruta in ["manzana", "pera", "uva"]:
    print(fruta)

for letra in "hola":             # recorre un texto carácter por carácter
    print(letra)

persona = {"nombre": "Ana", "edad": 30}
for clave, valor in persona.items():   # recorre un diccionario
    print(clave, valor)

for i in range(3):               # bucle anidado: un for dentro de otro
    for j in range(2):
        print(i, j)
```

**Ojo con:** no agregues ni quites elementos de una lista mientras la recorrés con `for`: da resultados raros. Recorré una copia (`for x in lista.copy():`) o armá una lista nueva. Una variable de bucle sigue existiendo después de terminar el `for`.

---

## range
- **alias:** range, rango, secuencia de numeros, contar, repetir n veces, paso, step, rango de numeros
- **categoria:** control de flujo

**Qué es:** Genera una secuencia de números enteros, ideal para repetir algo una cantidad de veces. Sintaxis: `range(fin)`, `range(inicio, fin)` o `range(inicio, fin, paso)`. El número final **no se incluye**.

**Ejemplo:**
```python
list(range(5))          # [0, 1, 2, 3, 4]
list(range(2, 6))       # [2, 3, 4, 5]
list(range(0, 10, 2))   # [0, 2, 4, 6, 8]
list(range(5, 0, -1))   # [5, 4, 3, 2, 1]  (cuenta hacia atrás)

for i in range(3):
    print("vuelta", i)  # vuelta 0, vuelta 1, vuelta 2
```

**Ojo con:** `range(5)` va de 0 a 4, no de 1 a 5. No guarda todos los números en memoria (los produce a medida que se piden), por eso para verlos hay que convertirlo con `list()`.

---

## enumerate
- **alias:** enumerate, enumerar, indice, indices, posicion, contador, recorrer con indice, numerar
- **categoria:** control de flujo

**Qué es:** Permite recorrer una colección obteniendo **a la vez** la posición y el elemento.

**Ejemplo:**
```python
colores = ["rojo", "verde", "azul"]
for i, color in enumerate(colores):
    print(i, color)              # 0 rojo, 1 verde, 2 azul

for i, color in enumerate(colores, start=1):   # empezar a contar desde 1
    print(i, color)              # 1 rojo, 2 verde, 3 azul
```

**Ojo con:** es más claro y más "pythónico" que usar `range(len(lista))`.

---

## zip
- **alias:** zip, juntar, emparejar, combinar listas, recorrer dos listas, recorrer en paralelo, unir listas
- **categoria:** control de flujo

**Qué es:** Junta dos o más colecciones elemento a elemento, para recorrerlas en paralelo.

**Ejemplo:**
```python
nombres = ["Ana", "Luis"]
edades = [30, 25]
for nombre, edad in zip(nombres, edades):
    print(nombre, edad)          # Ana 30, Luis 25

dict(zip(nombres, edades))       # {"Ana": 30, "Luis": 25}
```

**Ojo con:** si las colecciones tienen distinta longitud, `zip` se detiene en la más corta y descarta el resto sin avisar. Desde Python 3.10 se puede usar `zip(a, b, strict=True)` para que dé error si no coinciden.

---

## while
- **alias:** while, bucle while, ciclo while, mientras, repetir mientras, bucle infinito, while true, loop
- **categoria:** control de flujo

**Qué es:** Repite un bloque **mientras** una condición sea verdadera. Se usa cuando no se sabe de antemano cuántas vueltas habrá.

**Ejemplo:**
```python
contador = 0
while contador < 3:
    print(contador)
    contador += 1                # sin esta línea, el bucle no terminaría

while True:                      # bucle "infinito" controlado con break
    respuesta = input("Escribí 'salir' para terminar: ")
    if respuesta == "salir":
        break
```

**Ojo con:** si la condición nunca se vuelve falsa, el programa queda en un **bucle infinito**. Asegurate de que algo dentro del bloque cambie la condición, o de tener un `break`. En la consola se corta con `Ctrl + C`.

---

## break
- **alias:** break, romper, romper bucle, salir del bucle, cortar bucle, terminar bucle, detener bucle
- **categoria:** control de flujo

**Qué es:** Sale inmediatamente del bucle (`for` o `while`) más interno en el que está.

**Ejemplo:**
```python
for numero in [3, 8, 5, 10]:
    if numero > 7:
        print("encontré uno mayor que 7:", numero)
        break                    # deja de recorrer; imprime 8
```

**Ojo con:** `break` solo corta el bucle donde está escrito. Si hay bucles anidados, el exterior sigue.

---

## continue
- **alias:** continue, continuar, saltar, saltar iteracion, siguiente vuelta, omitir elemento, saltear
- **categoria:** control de flujo

**Qué es:** Salta el resto de la vuelta actual y pasa directo a la siguiente.

**Ejemplo:**
```python
for n in range(6):
    if n % 2 == 0:
        continue                 # los pares se saltan
    print(n)                     # imprime 1, 3, 5
```

**Ojo con:** en un `while`, asegurate de actualizar la variable de control **antes** del `continue`, o te quedás en un bucle infinito.

---

## pass
- **alias:** pass, no hacer nada, marcador de posicion, placeholder, bloque vacio, dejar vacio, todo
- **categoria:** control de flujo

**Qué es:** Una instrucción que no hace nada. Sirve de relleno cuando Python exige un bloque pero todavía no sabés qué poner (un bloque vacío da error de sintaxis).

**Ejemplo:**
```python
def funcion_pendiente():
    pass                         # la completo después

if True:
    pass                         # sin pass, esto daría error
```

---

## else en bucles
- **alias:** else en bucles, for else, while else, else de for, else del bucle, for/else
- **categoria:** control de flujo

**Qué es:** Un `for` o un `while` pueden llevar un `else`. Ese bloque se ejecuta **solo si el bucle terminó normalmente**, es decir, sin que un `break` lo cortara. Es útil para búsquedas: "si no lo encontré...".

**Ejemplo:**
```python
for n in [2, 4, 6]:
    if n % 2 != 0:
        print("hay un impar")
        break
else:
    print("todos son pares")     # se ejecuta: no hubo break
```

**Ojo con:** el nombre confunde: no significa "si no entró al bucle", sino "si no se rompió con `break`".

---

## iterable
- **alias:** iterable, iterables, iterador, iteradores, iter, next, stopiteration, recorrible
- **categoria:** control de flujo

**Qué es:** Un **iterable** es cualquier objeto que se puede recorrer con `for`: listas, textos, tuplas, conjuntos, diccionarios, `range`, archivos... Un **iterador** es el objeto que va entregando los elementos uno por uno; se obtiene con `iter()` y se avanza con `next()`.

**Ejemplo:**
```python
it = iter([10, 20])
next(it)       # 10
next(it)       # 20
next(it)       # da StopIteration: ya no quedan elementos
```

**Ojo con:** algunos iteradores se **agotan**: `zip`, `enumerate`, `map` y los generadores solo se pueden recorrer una vez. Si necesitás recorrerlos de nuevo, volvé a crearlos o guardalos en una lista con `list(...)`.

---

## comprension de listas
- **alias:** comprension de listas, comprension de lista, list comprehension, comprehension, lista por comprension, filtrar lista, mapear lista, expresion generadora, generator expression
- **categoria:** control de flujo

**Qué es:** Una forma compacta de crear una lista nueva a partir de otra colección, aplicando una transformación y, opcionalmente, un filtro. Sintaxis: `[expresion for x in coleccion if condicion]`.

**Ejemplo:**
```python
cuadrados = [n * n for n in range(5)]            # [0, 1, 4, 9, 16]
pares = [n for n in range(10) if n % 2 == 0]     # [0, 2, 4, 6, 8]
mayus = [p.upper() for p in ["a", "b"]]          # ["A", "B"]

# if/else va ANTES del for (es una expresión ternaria):
etiquetas = ["par" if n % 2 == 0 else "impar" for n in range(3)]

# Con paréntesis en vez de corchetes se crea un generador (no guarda todo en memoria):
suma = sum(n * n for n in range(1000))
```

**Ojo con:** si la comprensión se vuelve larga o anidada, es más legible un `for` normal. El `if` solo (filtro) va **al final**; el `if/else` (transformación) va **al principio**.

---

## comprension de diccionarios y conjuntos
- **alias:** comprension de diccionarios, comprension de diccionario, dict comprehension, comprension de conjuntos, set comprehension, diccionario por comprension
- **categoria:** control de flujo

**Qué es:** Lo mismo que la comprensión de listas, pero con llaves: arma un diccionario (`{clave: valor ...}`) o un conjunto (`{valor ...}`).

**Ejemplo:**
```python
cuadrados = {n: n * n for n in range(4)}         # {0: 0, 1: 1, 2: 4, 3: 9}
largos = {p: len(p) for p in ["sol", "luna"]}    # {"sol": 3, "luna": 4}
letras = {c for c in "hola mundo" if c != " "}   # conjunto de letras sin repetir

invertido = {v: k for k, v in {"a": 1, "b": 2}.items()}   # {1: "a", 2: "b"}
```

**Ojo con:** en el diccionario, si dos elementos generan la misma clave, el último pisa al anterior.

---

## match
- **alias:** match, case, match case, switch, structural pattern matching, patron, patrones, coincidencia de patrones, selector
- **categoria:** control de flujo

**Qué es:** Compara un valor contra varios "patrones" y ejecuta el bloque del primero que coincida. Existe desde **Python 3.10**. Es lo más parecido que tiene Python a un `switch`, pero más potente.

**Ejemplo:**
```python
comando = "salir"
match comando:
    case "iniciar":
        print("arrancando")
    case "salir" | "cerrar":     # varias opciones con |
        print("saliendo")        # se ejecuta este
    case _:                      # comodín: cubre todo lo demás
        print("comando desconocido")

punto = (0, 5)
match punto:
    case (0, 0):
        print("origen")
    case (0, y):                 # captura el valor en la variable y
        print("sobre el eje Y en", y)
    case (x, y) if x == y:       # condición extra con "if"
        print("en la diagonal")
```

**Ojo con:** no existe en versiones anteriores a 3.10. No hay "caída" entre casos como en otros lenguajes: se ejecuta un solo `case`. Un nombre suelto dentro de un patrón (como `y`) **captura** el valor en vez de compararlo.
