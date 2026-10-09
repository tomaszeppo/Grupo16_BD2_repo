# Operativa desde Terminal

1. Levantar IRIS con `bash scripts/01_inicializar.sh`.
2. Compilar definiciones persistentes con `bash scripts/02_compilar_clases.sh`.
3. Ejecutar las pruebas con `bash scripts/03_demo_objetos.sh`.
4. Entrar manualmente al terminal cuando se necesite inspeccionar: `bash scripts/04_terminal_iris.sh`.
5. Para visualizar las proyecciones SQL, la demo ejecuta consultas a través de `%SQL.Statement`; las consultas equivalentes están en `sql/consultas_demo.sql`.

## Carga y compilación manual

La carpeta `clases/` contiene fuentes `.cls`. El script las carga sin compilarlas una por una y compila luego el paquete `Fixture.*` como conjunto para que el compilador conozca los dos extremos de la relación padre-hijo antes de generar storage.

El terminal de IRIS está dentro del contenedor; el proyecto no utiliza un ORM externo ni otra base para simular el modelo de objetos.
