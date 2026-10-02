# ¿Por qué MongoDB?
Se seleccionó MongoDB como sistema de gestión de base de datos debido a que el módulo requiere almacenar información documental de equipos y jugadores, con una estructura flexible y orientada a documentos.
La utilización de MongoDB permite representar cada equipo y cada jugador como un documento independiente, manteniendo una estructura sencilla y fácilmente consultable. Además, permite realizar operaciones de búsqueda, filtrado, ordenamiento, actualización y agregación mediante sus operadores nativos.
La elección de una base de datos documental resulta adecuada para este módulo debido a que la información de los jugadores comparte una estructura común, pero puede evolucionar en futuras iteraciones sin requerir necesariamente cambios estructurales equivalentes a los de un modelo relacional tradicional.



# Justificación de la relación entre equipos y jugadores
Se decidió utilizar una relación mediante referencia entre las colecciones equipos y jugadores.
Cada equipo posee un campo codigo de tres letras que funciona como identificador lógico único. Los documentos de la colección jugadores poseen un campo equipo, cuyo valor corresponde al codigo del equipo al que pertenece el jugador.
De esta manera, por ejemplo, un jugador cuyo campo equipo posee el valor "ARG" pertenece al documento de equipos cuyo campo codigo es "ARG".
Se optó por esta estrategia en lugar de incrustar los jugadores dentro de cada documento de equipo porque permite mantener a los jugadores como documentos independientes y facilita realizar consultas específicas sobre ellos, como búsquedas por apellido, posición, dorsal o equipo.
Además, esta estrategia evita duplicar la información del equipo en cada documento de jugador. Si el nombre de un equipo cambia, la información del equipo se modifica únicamente en la colección equipos, manteniendo una única fuente de información.
## Alternativa descartada
Como alternativa se consideró almacenar los jugadores directamente dentro de cada documento de equipo mediante un arreglo embebido. Si bien este enfoque permitiría obtener un equipo y sus jugadores en una única consulta, se descartó debido a que dificultaría las consultas globales sobre jugadores y produciría documentos de equipo de mayor tamaño.
Por este motivo, se considera más conveniente mantener ambas entidades en colecciones separadas y relacionarlas mediante el código del equipo.


# Validaciones
## Validación de datos
Se implementaron validaciones mediante el mecanismo de validación de esquemas de MongoDB ($jsonSchema), con el objetivo de evitar que se incorporen documentos que no respeten la estructura definida para el módulo.
En la colección equipos se valida la existencia de los campos nombre y código, verificando que ambos sean cadenas de texto y que el código respete el formato establecido de tres letras mayúsculas.
En la colección jugadores se validan los campos nombre, apellido, dorsal, equipo y posición. El dorsal debe ser un número entero dentro del rango definido y la posición debe corresponder a uno de los valores permitidos.
La validación se configuró con validationLevel: "strict" y validationAction: "error", por lo que MongoDB rechaza las operaciones que intenten insertar o modificar documentos que no cumplan con las reglas establecidas.
La validación mediante $jsonSchema controla la estructura y los tipos de los documentos, pero no permite establecer directamente una clave foránea entre dos colecciones. Por este motivo, la integridad de la relación jugador-equipo se verifica adicionalmente mediante consultas de agregación con $lookup, comprobando que todos los códigos utilizados por los jugadores correspondan a un equipo existente.

# Justificación de los índices
Se implementaron índices sobre los campos que participan con mayor frecuencia en las consultas del módulo.

En la colección equipos se creó un índice único sobre codigo, debido a que este campo funciona como identificador lógico del equipo y no debe repetirse.

En la colección jugadores se creó un índice sobre equipo, ya que este campo es utilizado para recuperar los jugadores pertenecientes a un equipo determinado.

También se creó un índice sobre apellido, debido a que el módulo requiere ordenar jugadores alfabéticamente, y un índice sobre posicion, utilizado para realizar búsquedas filtradas por posición.

La decisión de indexar estos campos busca reducir la cantidad de documentos que MongoDB debe recorrer durante las consultas y mejorar el acceso a los datos cuando el volumen de información aumente.

# Justificación del unique
## Identificación de equipos
El campo código fue definido como identificador lógico único para los equipos. Por este motivo se creó el índice { código: 1 } con la opción unique: true.
Esto permite que MongoDB rechace automáticamente la inserción de dos equipos que posean el mismo código, evitando una inconsistencia que podría afectar posteriormente la relación con los jugadores.
De esta forma, el índice no solamente cumple una función de rendimiento, sino también una función de integridad de los datos.

# Agregaciones
Se utilizaron pipelines de agregación para obtener información derivada de los datos almacenados.

Una de las agregaciones implementadas utiliza $lookup para relacionar las colecciones equipos y jugadores mediante los campos codigo y equipo, respectivamente. A partir de esta relación se obtiene la cantidad de jugadores asociados a cada equipo y posteriormente se ordenan los resultados.

Esta operación demuestra la capacidad de MongoDB para realizar consultas sobre múltiples colecciones y generar información estadística sin necesidad de modificar los documentos originales.

También se implementó una agregación mediante $group para obtener la cantidad de jugadores según su posición.
