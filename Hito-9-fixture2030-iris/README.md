# Fixture 2030 — Entidades Complejas (Hito 9)

Módulo orientado a objetos del Fixture 2030, sobre InterSystems IRIS. Modela la parte del dominio que es una máquina de estado real (un Partido con su lista subordinada de Eventos), algo que no encaja bien como documento aislado ni como filas de una tabla ancha. El detalle de diseño está en `docs/diagrama_objetos.md` y `docs/matriz_integridad.md`.

## Contexto multi-base

Este módulo es una parte de un Fixture 2030 que usa varias bases de datos.
Los códigos de equipo, jugador y partido (`ARG`, `ARG-20`, `P-01`) son los
mismos que usan los otros módulos, y acá se guardan como texto: no hay
ninguna conexión técnica real entre las bases. Por eso `Evento` guarda un
`JugadorCodigo` y `Jugador`/`Tecnico` guardan un `EquipoCodigo`, en vez de
referencias de objeto a clases que viven en otro módulo.

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

## Estado de la validación

Las 7 clases se compilaron y se corrieron contra un IRIS real
(`intersystems/iris-community:latest-cd`): compilan sin errores, las
demostraciones se pueden repetir (`Carga.Limpiar()` borra los datos de
muestra) y las consultas SQL devuelven las mismas entidades que se cargaron
como objetos. También se comprobó que los datos sobreviven a
`docker compose down` + `up -d` con el volumen `~/docker/data/iris`, y que
borrar un partido borra sus eventos. Las salidas están en `docs/evidencia/`:

- `compilacion.txt`: las 7 clases compilan sin errores.
- `demos_objetos.txt`: carga, navegación por objetos y los dos rechazos.
- `consultas_sql.txt`: las mismas entidades vistas por SQL.
- `cascada_borrado.txt`: borrado en cascada de los eventos.
