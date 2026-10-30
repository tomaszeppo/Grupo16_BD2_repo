# M02 / H2 - Paralelismo controlado del generador, antes de implementar

Fecha: 30/10/2026. La hipótesis se registra antes de crear la nueva variante.
No se ejecutarán cargas durante su preparación. Las versiones 2.0 y 2.1 quedan históricas.

## Evidencia y posible limitación (RF7)

La primera línea base de 50.000 escrituras, concurrencia 100 y un proceso registró
6.261,365 escrituras/s, p99 172,385 ms, cero errores y persistencia correcta.
La CPU del cliente superó el 90% de un núcleo en tres de cuatro muestras útiles.
El benchmark H6 original ya advertía sobre el límite del generador de un proceso.
Esto justifica investigar su capacidad de envío/callbacks; no prueba saturación causal
del cliente ni descarta límites del servidor, red, instrumentación o almacenamiento.

## Hipótesis H2

Repartir las escrituras entre dos procesos independientes, con su propia sesión preparada,
podría aprovechar más de un núcleo para el trabajo Python y reducir presión sobre un único
proceso. Conservar 100 operaciones concurrentes totales (1x100 frente a 2x50) permitirá
evaluar esa arquitectura sin aumentar deliberadamente el máximo de solicitudes en vuelo.
Se espera mejorar throughput y/o cola de latencias sin perder integridad.

El original ya tiene multiprocessing: no se presenta como inventado aquí. La mejora será
su uso controlado y las correcciones necesarias para comparar: datos independientes del
número de procesos, sesiones propias, inicio sincronizado y presupuesto global fijo.

## Comparación propuesta

| Condición | A, control nuevo | B, candidata paralela |
|---|---|---|
| Filas | 50.000 | 50.000 |
| Procesos | 1 | 2 |
| Concurrencia por proceso | 100 | 50 |
| Concurrencia total máxima configurada | 100 | 100 |
| Generación | Misma secuencia global con semilla 2030 | Mismos datos por índice global, divididos en tramos disjuntos |
| Instrumentación | Misma que B | Misma que A |
| Consulta, esquema, timeout, retry policy e imagen | Iguales | Iguales |

Se repetirá A y B con el mismo código nuevo: la corrida histórica es antecedente, no
una demostración suficiente por sí sola. El número de procesos afecta también el número
de sesiones/pools; una mejora no aislará exclusivamente CPU frente a conexiones.

## Correcciones previstas (RF8)

1. Dos trabajadores creados con spawn y conexiones propias; no compartir sesiones entre procesos.
2. Barrera después de preparar conexión, sentencia y datos, antes de empezar la fase medida.
3. Mantener los mismos valores de datos que el caso original de un proceso; el original
   usa semilla 2030+índice de proceso y no garantiza esa igualdad al cambiar procesos.
4. Perfiles A y B validados, ambos con presupuesto global 100, y trazabilidad de configuración.
5. Mantener el cálculo de latencias y percentiles individuales, sin promediar percentiles de procesos.

## Costos, prueba y decisión

Puede crecer CPU/RAM del cliente y el número de conexiones; la creación de procesos,
generación/hash de datos y sincronización agregan preparación. Se registrarán tiempo de
carga y tiempo total por separado. Podría trasladarse el límite a Cassandra o no haber mejora.

Después se medirán repeticiones intercaladas de A/B, errores, throughput, p95/p99, recursos
y persistencia con IDs nuevos. No modificar esquema, timeout ni caché en la misma prueba.
No borrar filas para repetir. La tabla crecerá y deben registrarse sus efectos de fondo.

La implementación podrá verificarse con pruebas aisladas de datos, perfiles y barrera,
sin base. El rendimiento real y la decisión final se registrarán después de las pruebas
conjuntas. No se prometerá multiplicar la tasa por dos ni se dará por probado un cuello.
