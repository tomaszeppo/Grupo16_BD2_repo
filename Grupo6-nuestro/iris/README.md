# Fixture 2030 — Entidades Complejas (Hito 9)

Módulo orientado a objetos del Fixture 2030, sobre InterSystems IRIS. Modela la parte del dominio que es una máquina de estado real (un Partido con su lista subordinada de Eventos), algo que no encaja bien como documento aislado ni como filas de una tabla ancha. El detalle de diseño está en `docs/diagrama_objetos.md` y `docs/matriz_integridad.md`.

## Qué incluye

```
fixture2030-iris/
├── docker-compose.yml         Ambiente IRIS (intersystems/iris-community:latest-cd)
├── src/
│   ├── Fixture2030.Persona.cls    Clase base de herencia
│   ├── Fixture2030.Jugador.cls    Extiende Persona
│   ├── Fixture2030.Arbitro.cls    Extiende Persona
│   ├── Fixture2030.Tecnico.cls    Extiende Persona
│   ├── Fixture2030.Partido.cls    Entidad padre (Relationship children)
│   ├── Fixture2030.Evento.cls     Entidad hija (Relationship parent) + validación
│   └── Fixture2030.Carga.cls      Carga de muestra y demostraciones
├── scripts/
│   └── consultas_sql.sql       Las mismas entidades vistas por SQL (RF8)
├── docs/
│   ├── diagrama_objetos.md     Jerarquía, relación, cardinalidades
│   ├── matriz_integridad.md    Qué garantiza la base en cada caso
│   └── evidencia/              Capturas de compilación y ejecución
└── README.md
```

## Cómo levantarlo

Necesitás Docker Desktop corriendo.

1. Crear la carpeta de persistencia en el host (misma convención que los
   hitos de Cassandra y Redis):

   ```
   mkdir -p ~/docker/data/iris
   ```

   En Windows con Docker Desktop, `~` se resuelve contra el usuario dentro
   del backend WSL2. Si da error, crear la carpeta a mano y reemplazar
   `~/docker/data/iris` en `docker-compose.yml` por una ruta absoluta.

2. Levantar el contenedor:

   ```
   docker compose up -d
   docker compose ps
   ```

   La primera vez, IRIS tarda un rato más que Mongo o Redis en estar lista
   (inicializa la Durable %SYS). Esperar antes de conectarse.

3. **Nota de seguridad:** la imagen community pide definir una contraseña
   de administrador la primera vez que se accede al Management Portal
   (`http://localhost:52773/csp/sys/UtilHome.csp`). Usar una clave de
   desarrollo, nunca una contraseña personal real (coherente con la
   convención de seguridad local de los hitos anteriores).

## Cómo compilar las clases

Entrar a la terminal de IRIS dentro del contenedor:

```
docker exec -it fixture2030-iris iris session iris
```

(Si el nombre de instancia no es `iris`, listar las disponibles con
`iris list` antes.)

Dentro de la terminal, importar y compilar todo `src/` de una vez (el
`docker-compose.yml` ya monta esa carpeta como `/opt/src` dentro del
contenedor):

```objectscript
Do $System.OBJ.ImportDir("/opt/src", "*.cls", "ck", .errors, 1)
Write errors
```

`errors` tiene que quedar vacío (0) si compiló todo sin problemas. Si hay
errores de sintaxis, el mensaje indica la clase y la línea.

## Cómo correr la demostración

Todo desde la misma terminal de IRIS, en orden:

```objectscript
Do ##class(Fixture2030.Carga).CargarMuestra()
Do ##class(Fixture2030.Carga).ConsultarPorObjetos("P-01")
Do ##class(Fixture2030.Carga).DemostrarFalloValidacion()
Do ##class(Fixture2030.Carga).DemostrarCargaFallida()
```

Y las consultas SQL de `scripts/consultas_sql.sql`, desde el Management
Portal (System Explorer → SQL) o desde cualquier cliente ODBC/JDBC
apuntando al puerto 1972.

## Lo que no pude probar yo

No tengo Docker ni una instancia de IRIS disponible en el ambiente donde
armé este proyecto, así que nada de esto se compiló ni se ejecutó de
verdad — a diferencia del módulo de Redis (Hito 7), donde sí pude simular
la lógica con una herramienta en memoria. Acá revisé la sintaxis de
ObjectScript con cuidado (nombres de clase, modificadores, la relación
`parent`/`children`, el método `%OnBeforeSave`), pero puede haber algún
detalle menor que solo aparezca al compilar contra un IRIS real — guíense
por el mensaje de error de `$System.OBJ.ImportDir` si algo no compila a la
primera.
