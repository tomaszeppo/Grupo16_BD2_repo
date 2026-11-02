# Lo que planteamos para el proyecto final

Mientras armábamos este hito pensamos dos cosas para el TP final: el prode con sus tablas y una ventana para poder comentar un partido. No las metimos en el hito porque en el Hito 5 nos marcaron que habíamos agregado usuarios, grupos y predicciones cuando no correspondía, y no queríamos volver a pasarnos del alcance. Igual las dejamos escritas acá, porque ya tienen bastante pensado y nos sirve que se vea hacia dónde vamos.

## Prode

### Reglas

- Cada usuario hace **un solo pronóstico por partido**, y ese mismo pronóstico cuenta para el ranking público y para todos los grupos privados en los que esté. Un usuario puede estar en varios grupos privados.
- **3 puntos** por acertar el resultado exacto y **1 punto** por acertar solo quién gana o si es empate. Si no acierta, 0.
- **Cuándo se puede pronosticar:** la fase de grupos se habilita entera 3 días antes del primer partido del Mundial. Cada partido de eliminatorias se habilita cuando ya se conocen los dos equipos, que es poco tiempo antes porque se juega cada 4 a 6 días.

### Desempate

Con 3 millones de usuarios y como mucho 312 puntos (104 partidos × 3), empatar en puntos va a ser lo normal, así que el desempate tiene que estar bien pensado. El orden es:

1. **Puntos.**
2. **Cantidad de resultados exactos.** Entre dos con los mismos puntos, gana el que acertó más exactos. Por ejemplo, 3 exactos (9 puntos) queda arriba de 2 exactos y 3 ganadores (también 9 puntos).
3. **Tiempo acumulado.** Por cada acierto se suma cuánto antes del partido estaba cargado el pronóstico final: completo si fue exacto, la mitad si fue solo el ganador. Cada partido suma como máximo 5 días, para que no sea lo mismo cargar todo antes del Mundial que ir pronosticando partido a partido. Se guarda en segundos.
4. **Sorteo**, para los que empatan en todo lo anterior. Va a pasar seguido entre los que pronostican con mucha anticipación, porque todos llegan al tope de 5 días.

### Cómo lo guardaríamos

- **Neo4j como fuente de verdad:** usuarios, grupos, pronósticos y resultados. Es un problema de relaciones (usuario → grupo, usuario → pronóstico → partido).
- **Redis para el ranking:** un *sorted set* donde el puntaje de cada usuario es un solo número que ya trae el desempate adentro:

  ```
  puntaje = puntos × 10^11 + exactos × 10^8 + tiempo_en_segundos
  ```

  El tiempo nunca llega a 10^8 (como mucho 104 × 2 × 5 días ≈ 90 millones de segundos), así que no se mezcla con los exactos, y lo mismo pasa con los exactos y los puntos. El número máximo queda muy por debajo del límite de precisión de Redis (2^53). El sorteo va al principio del nombre de cada miembro, porque ante puntajes iguales Redis ordena alfabéticamente por nombre.
- **Por qué Redis y no ordenar al consultar:** pedir el top 100 o la posición de un usuario cuesta O(log N): con 3 millones son unos 22 pasos. En una tabla relacional, el top se resuelve con un índice, pero saber en qué puesto está alguien obliga a contar cuántos tienen más puntos que él.
- **Al terminar un partido:** se recalcula el total de cada usuario que lo pronosticó y se escribe con `ZADD`. No usamos `ZINCRBY` (sumar) porque si el proceso se corta y se reintenta, a algunos les sumaría dos veces. Escribiendo el total, repetirlo no cambia nada, y si Redis se pierde se reconstruye desde Neo4j.
- **Grupos privados:** no tendrían su propio *sorted set*. La tabla de un grupo se arma al pedirla, trayendo los puntajes de sus integrantes del ranking público (`ZMSCORE`) y ordenándolos. Así, al terminar un partido hay una escritura por usuario y no una por cada grupo de cada usuario. Para eso los grupos tendrían un tamaño máximo (por ejemplo, 100 personas).

Esto cambia algo del Hito 3, donde habíamos puesto grupos y puntajes en IRIS. Lo cambiamos porque lo que más se consulta es "top N" y "en qué puesto estoy", y eso Redis lo resuelve directo.

En Grafana mediríamos cuánto tarda la tabla en quedar actualizada después de cada partido, que es lo que más le importa al usuario del prode.

## Ventana para comentar un partido

Hoy la API acepta comentarios sobre un partido en cualquier momento, aunque falte una semana o haya terminado hace un mes. Para el TP final pensamos:

- **Abrir los comentarios 1 hora antes** del partido, que es cuando salen las formaciones y empieza la previa.
- **Cerrarlos unas horas después del final**, porque los comentarios de después del partido también son parte de lo que se analiza (como el Data Mart del Hito 12).
- **No consultar Neo4j ni IRIS en cada comentario** para saber si el partido está abierto: en un pico serían miles de consultas por segundo. Guardaríamos en Redis una marca de "partido abierto a comentarios" que vence sola al cerrar la ventana. Además, eso resuelve un problema que vimos en este hito: hoy, si Neo4j se cae, tampoco se puede comentar.
