# Base de conocimiento de Python: Bloque 3 (Funciones)

> **Formato (igual que los bloques anteriores):**
> - Cada entrada empieza con una línea `## termino` (nombre principal, en minúsculas).
> - La línea `- **alias:**` lista las otras palabras que deben llevar a esa entrada (sinónimos, plural, inglés, sin tildes).
> - Después vienen `**Qué es:**`, `**Ejemplo:**` y, si hace falta, `**Ojo con:**`.
> - Las entradas se separan con `---`.
> - Al buscar, conviene pasar lo que escribe el usuario a minúsculas y sin tildes, y compararlo con el nombre y los alias.

> **Plan de bloques:**
> 1. Fundamentos y tipos de datos (hecho)
> 2. Control de flujo (hecho)
> 3. Funciones (este)
> 4. Programación orientada a objetos (clases, herencia, dataclass)
> 5. Errores y archivos (try/except, with/open, json, pathlib)
> 6. Módulos y biblioteca estándar (import, pip, datetime, random, re...)

**Índice de este bloque:** funcion, parametros y argumentos, argumentos por defecto, argumentos con nombre, args y kwargs, return, alcance, lambda, type hints, funciones de orden superior, closure, decorador, generador, recursion, funciones integradas.

---

## funcion
- **alias:** funcion, funciones, def, definir funcion, crear funcion, llamar funcion, invocar, function, subrutina
- **categoria:** funciones

**Qué es:** Un bloque de código con nombre que se define una vez con `def` y se puede usar (llamar) todas las veces que haga falta. Sirve para no repetir código y para dividir un programa en partes entendibles.

**Ejemplo:**
```python
def saludar(nombre):
    """Muestra un saludo personalizado."""
    print(f"Hola, {nombre}")

saludar("Ana")        # Hola, Ana   <- así se llama a la función
saludar("Luis")       # Hola, Luis
```

**Convenciones:** nombres en `snake_case` y con un verbo que diga qué hace (`calcular_total`, `leer_archivo`). El texto entre triples comillas al inicio es el docstring: explica para qué sirve.

**Ojo con:** definir una función no la ejecuta: hay que llamarla con paréntesis. `saludar` sin paréntesis es solo la función como objeto, no la ejecuta. Además, la función tiene que estar definida **antes** de la línea que la llama, o da `NameError`.

---

## parametros y argumentos
- **alias:** parametro, parametros, argumento, argumentos, params, args posicionales, posicionales, orden de argumentos, typeerror argumentos
- **categoria:** funciones

**Qué es:** Los **parámetros** son los nombres que la función declara entre paréntesis al definirse. Los **argumentos** son los valores concretos que se le pasan al llamarla. Por defecto se asignan **por posición**: el primer argumento al primer parámetro, y así.

**Ejemplo:**
```python
def sumar(a, b):          # a y b son parámetros
    return a + b

sumar(3, 4)               # 3 y 4 son argumentos -> 7
```

**Ojo con:** pasar menos o más argumentos de los necesarios da `TypeError` (por ejemplo `sumar(3)` falla porque falta `b`).

---

## argumentos por defecto
- **alias:** argumentos por defecto, valor por defecto, parametro opcional, parametros opcionales, default, valores predeterminados, argumento opcional
- **categoria:** funciones

**Qué es:** Un parámetro puede tener un valor ya asignado, que se usa si al llamar a la función no se pasa ese argumento. Los parámetros con valor por defecto van **después** de los obligatorios.

**Ejemplo:**
```python
def saludar(nombre, saludo="Hola"):
    print(f"{saludo}, {nombre}")

saludar("Ana")                 # Hola, Ana
saludar("Ana", "Buen día")     # Buen día, Ana
```

**Ojo con (error muy común):** nunca uses una lista o diccionario vacío como valor por defecto. Se crea **una sola vez** y se comparte entre llamadas.
```python
def agregar(x, lista=[]):      # MAL
    lista.append(x)
    return lista
agregar(1)    # [1]
agregar(2)    # [1, 2]  <- sorpresa: recordó la llamada anterior

def agregar(x, lista=None):    # BIEN
    if lista is None:
        lista = []
    lista.append(x)
    return lista
```

---

## argumentos con nombre
- **alias:** argumentos con nombre, keyword arguments, argumentos nombrados, kwarg, pasar por nombre, solo por nombre, keyword only, posicional solamente
- **categoria:** funciones

**Qué es:** Al llamar a una función se puede indicar a qué parámetro corresponde cada valor escribiendo `nombre=valor`. Así el orden deja de importar y el código se lee mejor.

**Ejemplo:**
```python
def crear_usuario(nombre, edad, activo=True):
    return {"nombre": nombre, "edad": edad, "activo": activo}

crear_usuario(edad=30, nombre="Ana")           # el orden no importa
crear_usuario("Ana", 30, activo=False)         # se pueden mezclar

def conectar(host, *, puerto):                 # lo que va después del * ...
    ...
conectar("localhost", puerto=8080)             # ... SOLO se puede pasar por nombre
```

**Ojo con:** los argumentos posicionales deben ir antes que los de nombre: `crear_usuario(nombre="Ana", 30)` es un error de sintaxis.

---

## args y kwargs
- **alias:** args, kwargs, *args, **kwargs, argumentos variables, cantidad variable de argumentos, empaquetar, desempaquetar argumentos, asterisco, doble asterisco
- **categoria:** funciones

**Qué es:** Permiten que una función reciba una cantidad variable de argumentos. `*args` junta los posicionales extra en una **tupla** y `**kwargs` junta los de nombre extra en un **diccionario**. Los nombres `args` y `kwargs` son convención: lo importante son los asteriscos.

**Ejemplo:**
```python
def sumar_todo(*args):
    return sum(args)

sumar_todo(1, 2, 3, 4)         # 10

def mostrar(**kwargs):
    for clave, valor in kwargs.items():
        print(clave, "=", valor)

mostrar(nombre="Ana", edad=30)  # nombre = Ana / edad = 30

# Al LLAMAR, los asteriscos hacen lo contrario: desempaquetan
numeros = [1, 2, 3]
sumar_todo(*numeros)           # equivale a sumar_todo(1, 2, 3)
datos = {"nombre": "Ana", "edad": 30}
mostrar(**datos)               # equivale a mostrar(nombre="Ana", edad=30)
```

**Ojo con:** si se usan juntos, el orden es: parámetros normales, `*args`, `**kwargs`.

---

## return
- **alias:** return, retornar, devolver, valor de retorno, resultado, devolver varios valores, retorno
- **categoria:** funciones

**Qué es:** Termina la función y entrega un valor a quien la llamó. Si una función no tiene `return`, devuelve `None`. Se pueden devolver varios valores separados por coma: Python los entrega como una **tupla**.

**Ejemplo:**
```python
def dividir(a, b):
    if b == 0:
        return None            # sale de la función de inmediato
    return a / b

resultado = dividir(10, 2)     # 5.0

def minmax(lista):
    return min(lista), max(lista)   # devuelve una tupla

menor, mayor = minmax([4, 1, 9])    # desempaquetado -> 1 y 9
```

**Ojo con:** `print` y `return` no son lo mismo: `print` solo **muestra** algo en pantalla, `return` **entrega** el valor para seguir usándolo. El código que está después de un `return` no se ejecuta.

---

## alcance
- **alias:** alcance, scope, ambito, variable local, variable global, global, nonlocal, legb, unboundlocalerror, visibilidad de variables
- **categoria:** funciones

**Qué es:** El alcance define **dónde se puede usar** una variable. Una variable creada dentro de una función es **local**: existe solo mientras la función se ejecuta. Una creada fuera es **global**. Python busca los nombres en este orden: local, la función que la contiene, global, y por último los nombres integrados.

**Ejemplo:**
```python
contador = 0                   # global

def sumar_uno():
    global contador            # avisa que se quiere modificar la global
    contador += 1

sumar_uno()
print(contador)                # 1

def externa():
    x = 10
    def interna():
        nonlocal x             # modifica la x de la función externa
        x += 1
    interna()
    return x                   # 11
```

**Ojo con:** si dentro de una función asignás un valor a un nombre, Python lo trata como local en **toda** la función. Por eso `contador += 1` sin `global` da `UnboundLocalError`. En general es mejor evitar `global`: pasá los datos como argumentos y devolvelos con `return`.

---

## lambda
- **alias:** lambda, funcion lambda, funcion anonima, anonima, funcion en una linea, expresion lambda
- **categoria:** funciones

**Qué es:** Una función pequeña, sin nombre, escrita en una sola línea. Solo puede contener **una expresión**, cuyo resultado es el valor que devuelve. Sintaxis: `lambda parametros: expresion`.

**Ejemplo:**
```python
doble = lambda x: x * 2
doble(5)                                   # 10

# Su uso más común: pasarla como criterio a otra función
palabras = ["pera", "kiwi", "manzana"]
sorted(palabras, key=lambda p: len(p))     # ["pera", "kiwi", "manzana"] por largo
max(palabras, key=lambda p: len(p))        # "manzana"
```

**Ojo con:** si necesitás más de una expresión, o la querés reutilizar y explicar, usá una `def` normal. Asignar una lambda a una variable (como `doble`) funciona, pero la guía de estilo de Python recomienda `def` en ese caso.

---

## type hints
- **alias:** type hints, anotaciones de tipo, anotaciones, tipado, tipos opcionales, typing, optional, -> , sugerencias de tipo, mypy
- **categoria:** funciones

**Qué es:** Anotaciones que indican qué tipo de dato se espera en cada parámetro y qué tipo devuelve la función. Ayudan a entender el código y a que el editor detecte errores, pero **Python no las verifica al ejecutar**.

**Ejemplo:**
```python
def saludar(nombre: str, veces: int = 1) -> str:
    return (f"Hola, {nombre}. ") * veces

def promedio(numeros: list[float]) -> float:       # list[float] desde Python 3.9
    return sum(numeros) / len(numeros)

def buscar(clave: str) -> int | None:              # "int o None" desde Python 3.10
    ...
```

**Ojo con:** `saludar(5)` se ejecuta igual aunque pida un `str`: las anotaciones son documentación, no una barrera. Para verificarlas se usa una herramienta aparte, como `mypy`.

---

## funciones de orden superior
- **alias:** funciones de orden superior, orden superior, map, filter, sorted, key, funcion como argumento, pasar funcion, funciones como objetos, callback, reduce
- **categoria:** funciones

**Qué es:** En Python las funciones son valores como cualquier otro: se pueden guardar en variables y pasar a otras funciones. Las que reciben otra función se llaman de **orden superior**. Las más usadas son `map` (transforma cada elemento), `filter` (se queda con los que cumplen una condición) y `sorted` con `key` (ordena según un criterio).

**Ejemplo:**
```python
numeros = [1, 2, 3, 4, 5]

list(map(lambda n: n * 2, numeros))          # [2, 4, 6, 8, 10]
list(filter(lambda n: n % 2 == 0, numeros))  # [2, 4]
sorted(["b", "A", "c"], key=str.lower)       # ["A", "b", "c"]

def aplicar(funcion, valor):
    return funcion(valor)

aplicar(len, "hola")                         # 4  <- se pasa len, sin paréntesis
```

**Ojo con:** `map` y `filter` devuelven iteradores, no listas: hay que convertirlos con `list()` para verlos. Muchas veces una comprensión de listas es más legible: `[n * 2 for n in numeros]`.

---

## closure
- **alias:** closure, clausura, clausuras, funcion dentro de funcion, funcion interna, funciones anidadas, funcion fabrica, factory
- **categoria:** funciones

**Qué es:** Una función definida dentro de otra que **recuerda** las variables de la función externa, incluso después de que esta terminó. Sirve para crear funciones "personalizadas".

**Ejemplo:**
```python
def multiplicador(factor):
    def multiplicar(n):
        return n * factor          # "recuerda" factor
    return multiplicar

por_3 = multiplicador(3)
por_3(10)                          # 30
multiplicador(5)(10)               # 50
```

**Ojo con:** las clausuras recuerdan la **variable**, no su valor del momento. En un bucle esto sorprende:
```python
funciones = [lambda: i for i in range(3)]
[f() for f in funciones]           # [2, 2, 2], no [0, 1, 2]
funciones = [lambda i=i: i for i in range(3)]   # solución: fijar el valor
```

---

## decorador
- **alias:** decorador, decoradores, decorator, @, arroba, wraps, functools, envolver funcion
- **categoria:** funciones

**Qué es:** Una función que recibe otra función y devuelve una versión modificada de ella, para agregarle comportamiento (medir tiempo, registrar llamadas, validar...) sin tocar su código. Se aplica escribiendo `@nombre` encima de la función.

**Ejemplo:**
```python
import functools

def anunciar(funcion):
    @functools.wraps(funcion)      # conserva el nombre y docstring originales
    def envoltura(*args, **kwargs):
        print(f"Llamando a {funcion.__name__}")
        return funcion(*args, **kwargs)
    return envoltura

@anunciar
def sumar(a, b):
    return a + b

sumar(2, 3)       # imprime "Llamando a sumar" y devuelve 5
# "@anunciar" encima de la función equivale a escribir: sumar = anunciar(sumar)
```

**Ojo con:** sin `functools.wraps`, la función decorada pierde su nombre y su docstring. Y la envoltura debe devolver lo que devuelve la original, o el resultado se pierde.

---

## generador
- **alias:** generador, generadores, generator, yield, yield from, evaluacion perezosa, lazy, generar valores
- **categoria:** funciones

**Qué es:** Una función que, en lugar de `return`, usa `yield` para entregar valores **de a uno**, pausándose entre cada pedido. No guarda todo en memoria: genera cada valor cuando hace falta. Es ideal para secuencias muy largas.

**Ejemplo:**
```python
def contar_hasta(n):
    i = 1
    while i <= n:
        yield i                    # entrega i y se pausa acá
        i += 1

for numero in contar_hasta(3):
    print(numero)                  # 1, 2, 3

gen = contar_hasta(2)
next(gen)                          # 1
next(gen)                          # 2
```

**Ojo con:** un generador se **agota**: una vez recorrido, queda vacío y para repetirlo hay que crearlo de nuevo. Para verlo completo se usa `list(gen)`. No se puede acceder por posición (`gen[0]` falla).

---

## recursion
- **alias:** recursion, recursividad, recursiva, funcion recursiva, caso base, recursionerror, llamarse a si misma, factorial, fibonacci
- **categoria:** funciones

**Qué es:** Una función que se llama a sí misma para resolver un problema dividiéndolo en versiones más chicas. Siempre necesita un **caso base**, la condición que detiene las llamadas.

**Ejemplo:**
```python
def factorial(n):
    if n <= 1:                     # caso base: corta la recursión
        return 1
    return n * factorial(n - 1)    # llamada recursiva con un problema más chico

factorial(5)                       # 120  (5*4*3*2*1)
```

**Ojo con:** sin caso base, o con uno que nunca se alcanza, da `RecursionError`: Python limita la profundidad (por defecto, unas 1000 llamadas). Si el problema es muy profundo, suele ser mejor resolverlo con un bucle.

---

## funciones integradas
- **alias:** funciones integradas, funciones incorporadas, builtins, built-in, len, sum, min, max, abs, any, all, sorted, reversed, help, dir, funciones predefinidas
- **categoria:** funciones

**Qué es:** Funciones que Python trae listas para usar, sin importar nada. Las más útiles:

**Ejemplo:**
```python
len([1, 2, 3])                 # 3        cantidad de elementos
sum([1, 2, 3])                 # 6        suma
min(4, 1, 9)                   # 1        el menor
max([4, 1, 9])                 # 9        el mayor
abs(-5)                        # 5        valor absoluto
round(3.14159, 2)              # 3.14     redondea
sorted([3, 1, 2])              # [1, 2, 3]    lista nueva ordenada
list(reversed([1, 2, 3]))      # [3, 2, 1]
any([False, True, False])      # True     ¿alguno es verdadero?
all([True, True, False])       # False    ¿todos son verdaderos?
type(5)                        # <class 'int'>
isinstance(5, int)             # True

help(len)                      # muestra la documentación de una función
dir("hola")                    # lista todo lo que se le puede hacer a un texto
```

**También integradas:** `print`, `input`, `range`, `enumerate`, `zip`, `map`, `filter`, `open`, `int`, `float`, `str`, `list`, `dict`, `set`.

**Ojo con:** no uses sus nombres para tus variables: `list = [1, 2]` o `sum = 0` "tapa" la función original y después `list(...)` o `sum(...)` dejan de funcionar.
