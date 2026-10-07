# Cardinalidad y escalabilidad

## Cardinalidad de `estadisticas_partido`

El modelo potencial tiene:

`127 partidos × 64 equipos × 20 sedes × 8 fuentes × 6 fases`

como un límite bruto de combinaciones. No todas se materializan porque cada partido solo utiliza dos equipos y una sede/fase; por eso el límite real de series es mucho menor.

Con el generador se materializan como máximo:

`127 × 2 × 20 × 8 = 40.640 series`

antes de considerar que no todas las sedes se combinan con todos los partidos. La cifra es intencionalmente acotada y evita tags de variación explosiva.

## Qué no es tag

- timestamp: es el orden temporal, no una dimensión de identidad.
- valor de una medida: cambia constantemente y no es una categoría estable.
- identificador único de observación: crearía una serie casi por punto.
- usuario individual: para esta métrica se necesitan conteos por región, no la identidad de cada usuario.

## Objetivo 10M+

La carga de diseño es:

`127 × 2 × 8 × 5.000 = 10.160.000 puntos deportivos`.

Se utiliza una frecuencia sintética determinista con múltiples fuentes para representar telemetría de alta frecuencia. No es una afirmación de tasa real del Mundial: es un escenario de carga reproducible para el Hito.

## Escalabilidad

Para acercarse al escenario real de producción se deberían medir lote, workers, presión de disco, CPU, memoria, consultas concurrentes y crecimiento de series. El laboratorio local utiliza un nodo único y no pretende probar una topología distribuida.
