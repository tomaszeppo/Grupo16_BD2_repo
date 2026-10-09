import sys
sys.path.insert(0, 'C:/Users/Galli/Desktop/personal/Hitos/Grupo16_BD2_repo/Grupo6-nuestro/scratch_tools')
from matriz import *

out = []
w = out.append
w("# Hito 2 — Matriz de decisión (Fixture 2030)\n")
w("Grupo 16 · Ingeniería de Datos II\n")
w("## RF1. Punto de partida\n")
w("Se recupera el inventario, las prioridades y los supuestos del Hito 1: nueve tipos de datos agrupados en datos de referencia, datos que cambian rápido durante los partidos y datos ligados a la cantidad de usuarios conectados. Los números del proyecto son 2 a 3 millones de usuarios simultáneos y picos de más de 100.000 solicitudes por segundo.\n")
w("## RF2. Criterios de comparación\n")
w("1. **Capacidad y volumen de datos.** ¿Puede manejar el volumen que necesita el módulo, tanto los registros constantes de los partidos como una gran cantidad de usuarios que entran de forma esporádica?")
w("2. **Performance.** ¿Qué tan rápido resuelve la tarea? ¿Puede mostrar el estado actual de un partido de forma casi instantánea, informar rápido a los ganadores y actualizar el seguimiento minuto a minuto?")
w("3. **Consistencia.** ¿En qué medida asegura que la información sea consistente? ¿Es verídico el estado del partido, coincide el puntaje de todas las personas de un mismo grupo, es consistente el ganador?")
w("4. **Escalabilidad y almacenamiento.** ¿Cómo almacena y cuánto crece? ¿Es efectivo en costo, es adecuado para manejar los datos a nivel global?")
w("5. **Capacidad de consulta y modelado.** ¿Permite formar las relaciones que facilitan el desarrollo y cómo se optimizan sus consultas?\n")
w("## RF3. Ponderación\n")
w("| Criterio | Peso |\n| :--- | ---: |")
for c, p in zip(CRITERIOS, PESOS):
    w("| %s | %d %% |" % (c, p))
w("| **Total** | **100 %** |\n")
w("## RF4. Modelos evaluados\n")
w("Se evalúan **los seis modelos** trabajados en clase para **cada una de las seis necesidades** de datos priorizadas:\n")
w("| Motor | Modelo |\n| :--- | :--- |\n| MongoDB | Documental |\n| Neo4j | Grafos |\n| Redis | Clave-valor |\n| Cassandra | Columnar |\n| IRIS | Multimodelo con almacenamiento transaccional |\n| InfluxDB | Series temporales |\n")
w("## RF5. Matriz de decisión\n")
w("Cada motor recibe de 1 a 5 puntos por criterio (5 es lo mejor). El total ponderado es la suma de cada valoración multiplicada por el peso del criterio, dividida por 100, por lo que el máximo posible es 5,00. Los puntajes son una valoración del grupo y no una medición; sirven para ordenar las alternativas con un criterio común y dejar a la vista dónde la diferencia es grande y dónde es corta.\n")
n = 0
for nec in NECESIDADES:
    n += 1
    t, orden = tabla(nec)
    w("### %d) %s\n" % (n, nec))
    w(t + "\n")
    primero, segundo = orden[0], orden[1]
    dif = total(NECESIDADES[nec][primero]) - total(NECESIDADES[nec][segundo])
    w("Mejor puntaje: **%s** (%.2f). Le sigue %s (%.2f), a %.2f puntos.\n" % (
        primero, total(NECESIDADES[nec][primero]), segundo, total(NECESIDADES[nec][segundo]), dif))

w("## RF6. Selección por necesidad\n")
w("| Necesidad | Primero en la matriz | Modelo seleccionado | Alternativa considerada |\n| :--- | :--- | :--- | :--- |")
ALT = {
    "Logs generados durante el partido": "InfluxDB",
    "Partidos y valores en tiempo real": "MongoDB",
    "Partidos finalizados y datos estáticos": "IRIS",
    "Grupos y puntajes": "MongoDB",
    "Predicciones de usuarios": "MongoDB",
    "Métricas y estadísticas históricas": "Cassandra",
}
for nec in NECESIDADES:
    t, orden = tabla(nec)
    w("| %s | %s (%.2f) | **%s** (%.2f) | %s |" % (nec, orden[0], total(NECESIDADES[nec][orden[0]]),
                                                 ELEGIDO[nec], total(NECESIDADES[nec][ELEGIDO[nec]]), ALT[nec]))
w("")
w("En tres necesidades el modelo seleccionado no es el primero de la matriz. Se aclara en cada caso:\n")
w("- **Partidos y valores en tiempo real.** MongoDB (4,25) y Redis (4,20) quedan prácticamente empatados. Se elige Redis porque el requisito que más pesa en este dato es responder en menos de 100 ms con picos superiores a 100.000 solicitudes por segundo, y para eso MongoDB, que guarda en disco, tiene menos margen. Es una decisión por el criterio de Performance, el de mayor peso (25 %).")
w("- **Partidos finalizados y datos estáticos.** IRIS (4,20) y MongoDB (4,15) también quedan casi empatados. Se elige MongoDB porque el dato ya no cambia y su estructura (equipos, estadio, resultado y eventos juntos) es la de un documento; la ventaja transaccional de IRIS no se aprovecharía acá y sumaría un motor más para operar.")
w("- **Predicciones de usuarios.** Con estos pesos, la matriz favorece a IRIS (4,20) y a MongoDB (4,00) por encima de Neo4j (3,70). Neo4j se mantuvo en el Hito 2 porque la relación directa entre usuario, partido y pronóstico es lo que mejor se representa como grafo, y el criterio de Consulta y modelado pesa solo 15 %. Es la decisión menos respaldada por la matriz y queda marcada para revisarla cuando se implemente ese módulo.\n")
w("## RF7. Justificación y costos aceptados\n")
J = [
 ("Logs generados durante el partido", "Cassandra", "Está orientada a escrituras intensivas, crece agregando nodos y mantiene la disponibilidad. Eso responde al flujo constante de registros que generan los partidos.", "Se acepta una consistencia que se puede configurar y un modelado pensado alrededor de las consultas, que limita las consultas improvisadas. InfluxDB conviene más para análisis puramente temporales, pero Cassandra admite registros con estructuras distintas."),
 ("Partidos y valores en tiempo real", "Redis", "Mantiene en memoria el estado vigente de los partidos, con la baja latencia que exigen los picos de más de 100.000 solicitudes por segundo y la respuesta en menos de 100 ms.", "Se acepta un mayor costo de memoria y el riesgo de perder datos si hay una falla antes de que queden guardados de forma definitiva. Cassandra ofrece más durabilidad pero no la misma velocidad para consultar el estado vigente."),
 ("Partidos finalizados y datos estáticos", "MongoDB", "Cada partido finalizado es un documento con equipos, estadio, resultado y eventos, sin consultas con múltiples uniones. El esquema flexible permite sumar atributos sin migraciones complejas.", "Se acepta cierta duplicación y desnormalización de datos. IRIS daría más control transaccional, pero ese control no es prioritario para información que cambia poco una vez validada."),
 ("Grupos y puntajes", "IRIS", "Sus garantías transaccionales aseguran que la composición de los grupos, los puntajes y las posiciones que ven los usuarios sean consistentes, y permite repartir la información entre regiones.", "Se acepta mayor complejidad operativa y sumar un motor especializado. Neo4j representaría bien las relaciones entre usuarios y grupos, pero el requisito principal es actualizar correctamente los puntajes, no recorrer relaciones complejas."),
 ("Predicciones de usuarios", "Neo4j", "Representa directamente la relación entre usuario, partido y pronóstico, y facilita consultas que recorren esas conexiones. El volumen es limitado: usuarios por partidos disponibles.", "Se acepta mantener un motor adicional y más complejidad de operación. MongoDB sería más simple si los pronósticos solo se consultaran por usuario o por partido; la conveniencia de Neo4j se valida con las consultas que se implementen."),
 ("Métricas y estadísticas históricas", "InfluxDB", "Está pensado para series temporales: guarda datos con marca de tiempo y permite agregarlos por período, como usuarios conectados, eventos por minuto o evolución de estadísticas durante los partidos.", "Se acepta que no sea adecuado para documentos generales ni para relaciones complejas. Cassandra soporta un volumen histórico parecido, pero exigiría más trabajo para las consultas y agregaciones temporales."),
]
for nec, mod, razon, costo in J:
    w("**%s → %s.** %s %s\n" % (nec, mod, razon, costo))
w("## RF8. Mapa de persistencia preliminar\n")
w("| Necesidad del Fixture 2030 | Motor |\n| :--- | :--- |")
for nec in NECESIDADES:
    w("| %s | %s |" % (nec, ELEGIDO[nec]))
w("")
w("## RF9. Preguntas, riesgos y validaciones pendientes\n")
for item in [
 "Definir cómo se consolidan y se guardan de forma definitiva los datos de un partido una vez finalizado, y qué pasa si ese paso falla.",
 "Hasta dónde escala Neo4j si la cantidad de usuarios supera cierto punto.",
 "Debatir los costos de operar seis motores distintos.",
 "Definir respaldos y alternativas en caso de ser necesarios.",
 "Decidir el límite de almacenamiento de los registros de los partidos.",
 "Definir cuestiones de seguridad: datos que necesiten cifrarse y privacidad.",
 "Revisar la elección de Neo4j para las predicciones, que la matriz no respalda por sí sola.",
]:
    w("- " + item)
w("")
open('C:/Users/Galli/Desktop/personal/Hitos/Grupo16_BD2_repo/Hito-2-matriz-decision/Hito_2_Matriz_Decision_Fixture2030.md', 'w', encoding='utf-8').write("\n".join(out))
print("ok", len("\n".join(out)))
