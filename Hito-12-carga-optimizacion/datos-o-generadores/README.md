# Datos y generadores del escenario

El benchmark genera sus propios 50.000 comentarios, con 5.000 usuarios ficticios,
semilla 2030 y 13 buckets. No se importaron los CSV de otros perfiles.

- Referencia histórica: [v2.0](../versiones/v2.0_base/carga/prueba_rendimiento.py).
- Variante ejecutada: [v2.2](../versiones/v2.2_candidata_paralelo/carga/prueba_rendimiento.py).
- Generación determinista por índice global: [perfil_paralelo.py](../versiones/v2.2_candidata_paralelo/carga/perfil_paralelo.py).
- Generador masivo H6 opcional: [generar_carga_masiva.py](../scripts/generar_carga_masiva.py).
- Preparación offline de antecedentes: [preparar_datos.py](../scripts/preparar_datos.py) y [datos](../datos/).

El contenido fijo, reparto uniforme y fechas sintéticas limitan la representatividad.
Los identificadores H12 son corridas de laboratorio. No representan partidos reales.
Se mantienen los generadores en su ubicación histórica para conservar sus imports y
manifiestos; esta carpeta proporciona la entrada pedida por la estructura de entrega.
