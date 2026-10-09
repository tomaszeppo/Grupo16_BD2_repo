El proyecto modela parte del Fixture 2030 mediante clases persistentes en IRIS. Se utilizan relaciones entre partidos y eventos, herencia entre personas del ámbito del fútbol y validaciones para mantener la integridad de los datos.

## Requisitos

- Docker Desktop o Docker Engine.
- Docker Compose.
- Terminal de macOS o Linux.

## Instalación y ejecución

Desde la carpeta del proyecto, ejecutar:

```bash
chmod +x scripts/*.sh
bash scripts/01_inicializar.sh
```

Para compilar las clases:

```bash
bash scripts/02_compilar_clases.sh
```

Para ejecutar la demostración:

```bash
bash scripts/03_demo_objetos.sh
```

El proyecto utiliza la imagen `intersystems/iris-community:latest-cd`. Los datos persistentes se almacenan en `~/docker/data/iris`.

## Modelo de datos

Las clases principales son:

- **Persona:** clase base con datos comunes.
- **Jugador, Arbitro y Tecnico:** clases que heredan de Persona.
- **Partido:** representa un partido del fixture y permite controlar su estado.
- **Evento:** representa un evento asociado a un partido.

La relación entre Partido y Evento es de tipo padre-hijo y está definida en ambos extremos. La clase Evento incluye un índice sobre la relación con Partido.

El método `CambiarEstado()` controla los cambios de estado del partido, mientras que `AgregarEvento()` valida los eventos y evita agregarlos a partidos finalizados.

## Pruebas realizadas

La demostración permite comprobar:

- La herencia entre las clases.
- El rechazo de objetos que no cumplen propiedades obligatorias.
- La validación de estados del partido.
- El guardado de un partido y sus eventos mediante una única llamada inicial a `%Save()` del padre.
- La navegación entre los objetos relacionados.
- La consulta de los mismos datos mediante SQL.

También se incluyen scripts adicionales para probar el guardado del árbol de objetos y las propiedades obligatorias.

## Persistencia

Para reiniciar el contenedor:

```bash
docker compose restart
```

Los datos se conservan en el directorio durable configurado en Docker Compose.

## Documentación y evidencia

En la carpeta `docs/` se encuentra la documentación del modelo, el diagrama de clases, la matriz de integridad y las instrucciones operativas.

En `docs/evidencia/` se guardan las capturas y los registros de las pruebas realizadas.

## Repositorio

El proyecto debe mantenerse en el repositorio GitHub del equipo, con historial de commits y acceso para el docente. No se deben subir credenciales ni archivos con los datos internos de la base de datos.