# Base de conocimiento de Python: Bloque 4 (Programación orientada a objetos)

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
> 4. Programación orientada a objetos (este)
> 5. Errores y archivos (try/except, with/open, json, pathlib)
> 6. Módulos y biblioteca estándar (import, pip, datetime, random, re...)

**Índice de este bloque:** clase, objeto, init, self, metodo, atributos de clase y de instancia, herencia, polimorfismo, encapsulamiento, property, metodos especiales, classmethod y staticmethod, dataclass, enum, clase abstracta, composicion.

---

## clase
- **alias:** clase, clases, class, poo, programacion orientada a objetos, oop, molde, plano, definir clase, crear clase
- **categoria:** poo

**Qué es:** Un molde que describe cómo son y qué pueden hacer ciertos objetos: define sus datos (atributos) y sus acciones (métodos). Se crea con `class` y, por convención, su nombre va en `PascalCase` (cada palabra con mayúscula inicial, sin guiones).

**Ejemplo:**
```python
class Perro:
    def __init__(self, nombre):
        self.nombre = nombre

    def ladrar(self):
        print(f"{self.nombre} dice: guau")

mi_perro = Perro("Toby")     # crea un objeto a partir de la clase
mi_perro.ladrar()            # Toby dice: guau
```

**Ojo con:** la clase es el molde y el objeto es cada cosa fabricada con ese molde. Con una sola clase se pueden crear tantos objetos como se quiera.

---

## objeto
- **alias:** objeto, objetos, instancia, instancias, instanciar, crear objeto, object, instance
- **categoria:** poo

**Qué es:** Una **instancia** concreta de una clase: tiene sus propios valores en los atributos y puede usar los métodos que la clase define. En Python todo es un objeto: números, textos, listas y hasta las funciones.

**Ejemplo:**
```python
a = Perro("Toby")
b = Perro("Luna")
a.nombre               # "Toby"
b.nombre               # "Luna"   (cada objeto tiene sus propios datos)
a is b                 # False    (son objetos distintos)
isinstance(a, Perro)   # True
```

**Ojo con:** `c = a` no crea un objeto nuevo: `c` y `a` son dos nombres para el mismo objeto, y cambiar uno cambia el otro.

---

## init
- **alias:** init, __init__, constructor, inicializador, inicializar, crear con valores, metodo init, new
- **categoria:** poo

**Qué es:** Un método especial que Python ejecuta automáticamente al crear un objeto. Se usa para darle sus valores iniciales. Técnicamente es el "inicializador" (el objeto ya existe cuando corre), pero en la práctica casi todos lo llaman constructor.

**Ejemplo:**
```python
class Cuenta:
    def __init__(self, titular, saldo=0):
        self.titular = titular
        self.saldo = saldo

c = Cuenta("Ana", 100)    # llama a __init__ automáticamente
c.saldo                   # 100
Cuenta("Luis").saldo      # 0  (usó el valor por defecto)
```

**Ojo con:** `__init__` no debe devolver nada (devolver un valor distinto de `None` da `TypeError`). Se escribe con **dos** guiones bajos a cada lado.

---

## self
- **alias:** self, yo mismo, instancia actual, primer parametro, this, parametro self, self.atributo
- **categoria:** poo

**Qué es:** El primer parámetro de los métodos de instancia: representa al propio objeto sobre el que se llama el método. Python lo pasa solo, no se escribe al llamar. El nombre `self` es una convención que todos respetan.

**Ejemplo:**
```python
class Contador:
    def __init__(self):
        self.valor = 0

    def sumar(self):
        self.valor += 1      # self.valor es el dato de ESTE objeto

c = Contador()
c.sumar()                    # Python lo traduce a Contador.sumar(c)
c.valor                      # 1
```

**Ojo con:** olvidar `self` en la definición (`def sumar():`) da `TypeError: ... takes 0 positional arguments but 1 was given` (el principio del mensaje cambia según la versión de Python). Y dentro del método, `valor` a secas no es el atributo: hay que escribir `self.valor`.

---

## metodo
- **alias:** metodo, metodos, method, metodo de instancia, funcion de una clase, llamar metodo, objeto.metodo
- **categoria:** poo

**Qué es:** Una función definida dentro de una clase. Se llama sobre un objeto con la forma `objeto.metodo()`. Los métodos de instancia reciben `self`; también existen los de clase (`@classmethod`) y los estáticos (`@staticmethod`).

**Ejemplo:**
```python
class Rectangulo:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto

    def area(self):
        return self.ancho * self.alto

r = Rectangulo(3, 4)
r.area()          # 12
```

**Ojo con:** una función suelta no pertenece a ninguna clase; un método sí. Y `r.area` sin paréntesis es el método como objeto, no lo ejecuta.

---

## atributos de clase y de instancia
- **alias:** atributo, atributos, atributo de clase, atributo de instancia, variable de clase, variable de instancia, atributo compartido, class attribute
- **categoria:** poo

**Qué es:** Un atributo de **instancia** (`self.x`) es propio de cada objeto. Un atributo de **clase** se escribe directamente dentro de la clase y es compartido por todos los objetos.

**Ejemplo:**
```python
class Gato:
    especie = "felino"           # de clase: compartido por todos
    def __init__(self, nombre):
        self.nombre = nombre     # de instancia: propio de cada objeto

a = Gato("Misu")
b = Gato("Tom")
a.especie, b.especie             # ("felino", "felino")
a.nombre, b.nombre               # ("Misu", "Tom")
```

**Ojo con (error muy común):** un atributo de clase **mutable** (lista, diccionario) se comparte entre todos los objetos.
```python
class Mal:
    items = []                   # compartida por TODOS los objetos
    def agregar(self, x):
        self.items.append(x)

m1, m2 = Mal(), Mal()
m1.agregar(1)
m2.items                         # [1]  <- sorpresa: m2 también la ve
```
La solución es crear la lista en `__init__` con `self.items = []`. Además, asignar `a.especie = "x"` crea un atributo de instancia que oculta al de clase solo para ese objeto.

---

## herencia
- **alias:** herencia, heredar, hereda, subclase, superclase, clase hija, clase padre, super, super(), issubclass, herencia multiple, mro, sobrescribir, override
- **categoria:** poo

**Qué es:** Una clase (hija) puede heredar los atributos y métodos de otra (padre) y agregar o cambiar los suyos. Se escribe `class Hija(Padre):`. `super()` da acceso a la clase padre. Es una relación de tipo "es un": un Perro **es un** Animal.

**Ejemplo:**
```python
class Animal:
    def __init__(self, nombre):
        self.nombre = nombre
    def hablar(self):
        print("...")

class Perro(Animal):
    def __init__(self, nombre, raza):
        super().__init__(nombre)       # reutiliza el __init__ del padre
        self.raza = raza
    def hablar(self):                  # sobrescribe el método del padre
        print("Guau")

p = Perro("Toby", "labrador")
p.hablar()                             # Guau
p.nombre                               # "Toby" (heredado)
isinstance(p, Animal)                  # True
issubclass(Perro, Animal)              # True
```

**Ojo con:** si la hija define `__init__` y no llama a `super().__init__(...)`, el padre no inicializa sus atributos. Python permite herencia múltiple (`class C(A, B)`), pero complica el orden en que se buscan los métodos (`C.__mro__` lo muestra): usala con cuidado. Si la relación no es realmente "es un", conviene usar composición.

---

## polimorfismo
- **alias:** polimorfismo, polimorfico, duck typing, tipado pato, misma interfaz, distintas clases mismo metodo
- **categoria:** poo

**Qué es:** Objetos distintos responden al mismo "mensaje" (un método con el mismo nombre), cada uno a su manera, y el código que los usa no necesita saber de qué clase son. En Python vale el **duck typing**: si el objeto tiene el método que se necesita, sirve, sin importar su clase ("si camina como pato y hace cuac, es un pato").

**Ejemplo:**
```python
class Perro:
    def hablar(self):
        return "Guau"

class Gato:
    def hablar(self):
        return "Miau"

class Robot:
    def hablar(self):
        return "Bip"

for ser in [Perro(), Gato(), Robot()]:
    print(ser.hablar())          # Guau, Miau, Bip (sin herencia entre ellos)
```

**Ojo con:** si a un objeto le falta el método, el error (`AttributeError`) aparece recién al ejecutar esa línea, no antes.

---

## encapsulamiento
- **alias:** encapsulamiento, encapsular, privado, publico, protegido, atributo privado, guion bajo, _atributo, __atributo, name mangling, ocultar datos
- **categoria:** poo

**Qué es:** Ocultar los detalles internos de una clase y exponer solo lo necesario. Python no tiene atributos "privados" de verdad: usa convenciones. Un guion bajo (`_nombre`) significa "uso interno, no lo toques". Dos guiones bajos (`__nombre`) hacen que Python cambie el nombre por dentro (*name mangling*) para evitar choques entre clases que heredan.

**Ejemplo:**
```python
class Cuenta:
    def __init__(self, saldo):
        self._saldo = saldo              # "interno" por convención

    def depositar(self, monto):
        if monto <= 0:
            raise ValueError("El monto debe ser positivo")
        self._saldo += monto

    def saldo(self):
        return self._saldo

c = Cuenta(100)
c.depositar(50)
c.saldo()                                # 150
```

**Ojo con:** `_saldo` se puede leer y cambiar desde afuera (`c._saldo = -5`): es un acuerdo entre programadores, no una barrera. Tampoco `__saldo` es privado real: sigue accesible como `c._Cuenta__saldo`. Para controlar el acceso a un dato, usá `property`.

---

## property
- **alias:** property, propiedad, propiedades, getter, setter, @property, atributo calculado, solo lectura, validar atributo
- **categoria:** poo

**Qué es:** Permite que un método se use como si fuera un atributo (sin paréntesis) y agrega validaciones al leer o modificar un valor. Con `@property` se define cómo se **lee** el valor y con `@nombre.setter` cómo se **modifica**.

**Ejemplo:**
```python
class Persona:
    def __init__(self, edad):
        self.edad = edad              # pasa por el setter

    @property
    def edad(self):                   # getter: se usa como p.edad
        return self._edad

    @edad.setter
    def edad(self, valor):            # setter: se usa como p.edad = 30
        if valor < 0:
            raise ValueError("La edad no puede ser negativa")
        self._edad = valor

p = Persona(30)
p.edad = 31       # usa el setter
p.edad = -1       # ValueError
```

**Ojo con:** el dato real se guarda con otro nombre (`_edad`). Si el setter escribiera `self.edad = valor`, se llamaría a sí mismo sin fin (recursión infinita). Una propiedad sin setter es de solo lectura: asignarle un valor da `AttributeError`.

---

## metodos especiales
- **alias:** metodos especiales, metodos magicos, dunder, doble guion bajo, __str__, __repr__, __eq__, __len__, __add__, __getitem__, __iter__, __lt__, sobrecarga de operadores, str, repr
- **categoria:** poo

**Qué es:** Métodos con doble guion bajo a cada lado que Python llama automáticamente en ciertas situaciones. Hacen que tus objetos funcionen con `print`, `len`, `==`, `+`, `for`, etc.

**Ejemplo:**
```python
class Punto:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __str__(self):                 # para print(p) y str(p): texto legible
        return f"({self.x}, {self.y})"

    def __repr__(self):                # para depurar: preciso y sin ambigüedad
        return f"Punto({self.x}, {self.y})"

    def __eq__(self, otro):            # para p1 == p2
        return self.x == otro.x and self.y == otro.y

    def __add__(self, otro):           # para p1 + p2
        return Punto(self.x + otro.x, self.y + otro.y)

a, b = Punto(1, 2), Punto(3, 4)
print(a + b)       # (4, 6)
a == Punto(1, 2)   # True
a                  # Punto(1, 2)   (la consola usa __repr__)
```

**Otros frecuentes:** `__len__` (para `len(obj)`), `__getitem__` (para `obj[i]`), `__iter__` (para `for`), `__contains__` (para `in`), `__lt__` (para `<` y para `sorted`), `__call__` (para llamar al objeto como función).

**Ojo con:** si definís `__eq__` sin definir `__hash__`, el objeto deja de poder usarse dentro de un `set` o como clave de diccionario (da `TypeError: unhashable type`). Si solo definís uno entre `__str__` y `__repr__`, definí `__repr__`: `print` lo usa como respaldo.

---

## classmethod y staticmethod
- **alias:** classmethod, staticmethod, @classmethod, @staticmethod, metodo de clase, metodo estatico, cls, constructor alternativo, factory method
- **categoria:** poo

**Qué es:** `@classmethod` define un método que recibe la **clase** (`cls`) en vez del objeto (`self`): se usa mucho para crear objetos de formas alternativas. `@staticmethod` define una función común que vive dentro de la clase por orden, sin recibir ni `self` ni `cls`.

**Ejemplo:**
```python
class Fecha:
    def __init__(self, dia, mes, anio):
        self.dia, self.mes, self.anio = dia, mes, anio

    @classmethod
    def desde_texto(cls, texto):          # constructor alternativo
        dia, mes, anio = texto.split("/")
        return cls(int(dia), int(mes), int(anio))

    @staticmethod
    def es_bisiesto(anio):                # no usa self ni cls
        return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)

f = Fecha.desde_texto("25/10/2026")
f.mes                                     # 10
Fecha.es_bisiesto(2024)                   # True
```

**Ojo con:** en un `classmethod` conviene crear el objeto con `cls(...)` y no con el nombre de la clase, así también funciona para las clases hijas.

---

## dataclass
- **alias:** dataclass, dataclasses, @dataclass, clase de datos, clase para datos, frozen, default_factory, field, registro
- **categoria:** poo

**Qué es:** Un decorador (disponible desde Python 3.7) que genera automáticamente `__init__`, `__repr__` y `__eq__` a partir de los atributos anotados. Ahorra mucho código repetitivo en clases que solo guardan datos.

**Ejemplo:**
```python
from dataclasses import dataclass, field

@dataclass
class Producto:
    nombre: str
    precio: float
    etiquetas: list[str] = field(default_factory=list)   # lista por defecto, segura

p = Producto("Taza", 7.5)
print(p)                          # Producto(nombre='Taza', precio=7.5, etiquetas=[])
p == Producto("Taza", 7.5)        # True

@dataclass(frozen=True)           # inmutable: no se pueden cambiar sus atributos
class Punto:
    x: int
    y: int
```

**Opciones útiles:** `frozen=True` (inmutable), `order=True` (permite comparar con `<` y `>`).

**Ojo con:** usar una lista o diccionario directamente como valor por defecto da `ValueError`: hay que usar `field(default_factory=list)`. Los tipos anotados no se verifican al ejecutar.

---

## enum
- **alias:** enum, enumeracion, enumeraciones, enumerado, constantes con nombre, opciones fijas, auto, miembros, estados
- **categoria:** poo

**Qué es:** Una clase que define un conjunto **fijo** de valores con nombre, útil para estados, tipos u opciones (en vez de usar números o textos sueltos que pueden escribirse mal).

**Ejemplo:**
```python
from enum import Enum, auto

class Color(Enum):
    ROJO = 1
    VERDE = 2
    AZUL = 3

Color.ROJO.name         # "ROJO"
Color.ROJO.value        # 1
Color(2)                # Color.VERDE    (buscar por valor)
Color["AZUL"]           # Color.AZUL     (buscar por nombre)
for c in Color:
    print(c)            # recorre todos los miembros

class Estado(Enum):
    ACTIVO = auto()     # auto asigna 1, 2, 3...
    INACTIVO = auto()
```

**Ojo con:** `Color.ROJO == 1` da `False`: un miembro del enum no es igual a su valor. Si querés que además se comporte como texto (por ejemplo para guardarlo en un JSON), definí `class Estado(str, Enum)`.

---

## clase abstracta
- **alias:** clase abstracta, abstracta, abc, abstractmethod, metodo abstracto, interfaz, contrato, protocolo
- **categoria:** poo

**Qué es:** Una clase que **no se puede instanciar** y que obliga a sus clases hijas a implementar ciertos métodos. Funciona como un contrato: "toda clase que herede de esta debe tener estos métodos". Se crea con el módulo `abc`.

**Ejemplo:**
```python
from abc import ABC, abstractmethod

class Forma(ABC):
    @abstractmethod
    def area(self):
        """Cada forma concreta debe calcular su área."""

class Cuadrado(Forma):
    def __init__(self, lado):
        self.lado = lado
    def area(self):
        return self.lado ** 2

Cuadrado(3).area()    # 9
Forma()               # TypeError: no se puede instanciar una clase abstracta
```

**Ojo con:** si una clase hija no implementa **todos** los métodos abstractos, tampoco se puede instanciar. Es útil para separar "qué hace algo" de "cómo lo hace", y poder cambiar la implementación sin tocar el código que la usa.

---

## composicion
- **alias:** composicion, componer, composicion sobre herencia, tiene un, has-a, objeto dentro de objeto, agregacion, delegar
- **categoria:** poo

**Qué es:** Construir una clase usando **objetos de otras clases como partes**, en lugar de heredar de ellas. Expresa una relación "tiene un": un Auto **tiene un** Motor. La herencia, en cambio, expresa "es un".

**Ejemplo:**
```python
class Motor:
    def encender(self):
        return "Motor encendido"

class Auto:
    def __init__(self):
        self.motor = Motor()          # el auto TIENE un motor

    def arrancar(self):
        return self.motor.encender()  # delega el trabajo en la pieza

Auto().arrancar()                     # "Motor encendido"
```

**Ojo con:** una regla práctica muy usada es "preferí composición sobre herencia": es más flexible, porque podés cambiar una pieza sin romper el resto. Reservá la herencia para casos donde de verdad exista una relación "es un".
