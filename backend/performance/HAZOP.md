# BP2-HAZOP-004 — evaluación candidata de protecciones

Versión 0.4. Vincula intención de diseño, parámetro, palabra guía, desviación,
causa candidata, consecuencia, responsable, actividad y barreras requeridas.
La evaluación no genera un estudio HAZOP completo ni prueba que el inventario sea exhaustivo.
Todos los registros de ejemplo son candidatos sintéticos, no reconstrucciones verificadas.

Cada barrera requiere evidencia identificada, verificación, vigencia y responsable.
Si requiere respuesta, el presupuesto temporal incluye detección, decisión,
movilización, ejecución, efecto y reserva. Cada tiempo se expresa en horas.
Disponible menos suma de tiempos debe ser estrictamente positivo para pasar
esta comprobación candidata; cero o negativo mantiene el bloqueo crítico.
Los tiempos disponibles y la reserva deben ser definidos y sustentados por el sitio.
Una alarma registrada no basta. La reducción de producción tampoco implica
eliminar instantáneamente aportes residuales. Cambios de condición exigen renovar
el balance y la vigencia de las evidencias antes de volver a evaluar.

Se evalúan barreras REQUERIDAS; todas deben cumplir. No se interpreta que toda
salvaguarda imaginable sea obligatoria ni se modelan alternativas equivalentes.
No se calcula crédito probabilístico por barreras ni se supone independencia.
Una ingeniería validada debe definir el conjunto exigible y sus dependencias.
Criticidad desconocida mantiene pendiente. Ninguna salida autoriza operación.

El esquema 0.4 exige el campo hazop; lista vacía mantiene pendiente.
El esquema 0.3 continúa aceptándose, pero sin HAZOP el resultado combinado no
puede quedar listo para revisión. Cualquier NO_GO previo se conserva.
Salida 0.4 conserva motivos por nodo/barrera y actividad para trazabilidad.

Fuentes conceptuales: Villegas Mantuano, UTN, 2012, tesis HAZOP de El Beaterio,
capítulo 3, páginas impresas 60–67, especialmente tiempo de respuesta y salvaguardas.
https://repositorio.utn.edu.ec/server/api/core/bitstreams/ee3d71ca-8c03-406c-9c47-646e136a1039/content
La fuente es un caso académico; los umbrales de su instalación no se trasladan.
El informe aportado sobre criticidad de equipos rotativos orienta la separación
AMEF/criticidad/ABC; sus escalas no se convierten en probabilidades o parada automática.

Validación: 52 pruebas locales aprobadas, 14 nuevas. Incluyen alarma sin prueba,
evidencia vencida/ausente, margen cero/negativo, demora de efecto desconocida,
barreras ausentes, criticidad desconocida, compatibilidad del contrato y bloqueo integrado.
Sigue pendiente calibración, revisión multidisciplinaria y prueba operacional.
No incluye control físico, IAM, PostgreSQL, despliegue o interfaz.
