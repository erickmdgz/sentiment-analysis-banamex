# Definición actual del programa — MVP Hackathon CX Banamex

## 1. Naturaleza del sistema

El sistema será una plataforma simple, funcional y demostrable para el hackathon.

No se busca construir desde el inicio una plataforma empresarial completa. La prioridad es demostrar valor con un MVP que permita:

1. Cargar datos crudos de encuestas NPS.
2. Procesar información de múltiples sucursales.
3. Integrar múltiples archivos de encuestas en un mismo conjunto de datos.
4. Consultar objetivos anuales de NPS por sucursal desde una fuente interna precargada en backend.
5. Mostrar métricas e insights nacionales.
6. Permitir bajar al detalle de una sucursal específica.
7. Comparar meses disponibles en la información cargada.
8. Identificar sucursales críticas.
9. Mostrar acciones sugeridas con base en los principales problemas detectados.

El sistema sí tendrá un motor de análisis para el MVP. El diseño técnico y desarrollo específico de este motor queda pendiente de desarrollo.

---

## 2. Enfoque corregido del MVP

El MVP estará centrado en una vista de alcance nacional.

Como los archivos iniciales pueden contener información de numerosas sucursales, el usuario principal no será un gerente de sucursal, sino un usuario con visibilidad nacional.

## Rol principal del MVP

### Gerente Nacional CX

Este usuario puede acceder a la información de todas las sucursales detectadas en los archivos cargados.

Su objetivo es:

- ver el estado nacional de la experiencia del cliente
- identificar problemas principales
- detectar sucursales críticas
- comparar meses disponibles
- seleccionar una sucursal para ver detalle granular
- entender qué acciones deben priorizarse
- cargar uno o varios archivos de encuestas NPS
- enriquecer el análisis con nuevas cargas posteriores

---

## 3. Rol secundario del MVP

### Administrador del sistema

Este rol existirá en el MVP como una separación visual dentro de la interfaz.

Para el MVP, el Administrador no requiere funcionalidad completa. Se usará principalmente como una representación POC de las secciones administrativas a las que este tipo de usuario tendría acceso en una versión posterior.

Su función conceptual sería:

- gestionar usuarios
- revisar cargas
- validar archivos
- configurar accesos
- monitorear errores de procesamiento
- consultar estado del sistema

Sin embargo, para el MVP de hackathon, este rol puede estar fusionado temporalmente con el Gerente Nacional CX.

La interfaz podrá mostrar una distinción visual entre:

- secciones ejecutivas / CX
- secciones administrativas

Pero no es necesario que toda la funcionalidad administrativa esté completamente implementada.

---

## 4. Flujo general del sistema

El flujo principal del MVP será:

1. El usuario inicia sesión.
2. El sistema solicita la carga de archivos de encuestas NPS.
3. El usuario carga uno o varios archivos `.txt` con información de múltiples sucursales.
4. El sistema valida los archivos cargados.
5. El sistema integra los datos válidos al conjunto de datos acumulado.
6. Si se cargan archivos adicionales después de un procesamiento previo, el sistema integra los nuevos datos a lo ya procesado.
7. El sistema evita duplicar registros usando `RecordId` como identificador único.
8. El sistema detecta las sucursales disponibles por `Id_branch`.
9. El sistema consulta los objetivos NPS anuales por sucursal desde una fuente interna precargada en backend.
10. El sistema valida la cobertura entre sucursales detectadas y objetivos disponibles.
11. El sistema procesa la información.
12. El sistema actualiza métricas, rankings, sucursales críticas e insights.
13. El sistema muestra una vista nacional Year To Date.
14. El usuario puede comparar meses disponibles.
15. El usuario puede seleccionar una sucursal específica.
16. El sistema muestra la vista Year To Date de la sucursal.
17. El usuario puede comparar meses disponibles dentro de esa sucursal.
18. El usuario puede consultar métricas granulares de la sucursal.

---

## 5. Archivos y fuentes de datos del sistema

## 5.1 Archivos de encuestas NPS

El sistema permitirá cargar uno o varios archivos `.txt` con respuestas de clientes.

Estos archivos pueden contener datos de múltiples sucursales.

Columnas esperadas:

| Campo | Descripción |
|---|---|
| `Fecha respuesta` | Fecha en la que el cliente respondió la encuesta. |
| `NPS_GROUP` | Clasificación del cliente: Promotor, Pasivo o Detractor. |
| `NPS_Rate` | Calificación numérica NPS. |
| `Verbalizacion` | Comentario abierto del cliente. |
| `RecordId` | Identificador único de la respuesta. |
| `Id_branch` | Identificador de la sucursal asociada. |

El sistema debe permitir:

- cargar un archivo
- cargar múltiples archivos a la vez
- cargar archivos adicionales posteriormente
- consolidar la información cargada
- evitar duplicados por `RecordId`
- actualizar métricas e insights con los nuevos datos
- enriquecer el aplicativo y el modelo con información incremental

---

## 5.2 Fuente interna de objetivos NPS por sucursal

El sistema no solicitará al usuario cargar manualmente un archivo de objetivos NPS desde la interfaz durante el MVP.

Para el MVP, los objetivos NPS anuales por sucursal estarán disponibles desde una fuente interna precargada en backend.

Esta fuente interna debe contener, como mínimo:

| Campo | Descripción |
|---|---|
| `Id_branch` | Identificador de la sucursal. |
| `NPS_objetivo_anual` | NPS objetivo anual asignado a esa sucursal. |

El sistema usará esta fuente para comparar el NPS actual contra la meta específica de cada sucursal.

Para el cálculo nacional, el sistema usará los objetivos de las sucursales incluidas en el análisis.

---

## 5.3 Generación previa de objetivos NPS por sucursal

Antes de operar el MVP, se debe generar una fuente interna con el NPS objetivo anual por sucursal.

Esta fuente debe construirse a partir del análisis disponible de datos y debe incluir las sucursales existentes identificadas por `Id_branch`.

El resultado de este trabajo será un archivo o estructura precargada en backend que el sistema consultará durante la ejecución.

Esta generación no forma parte del flujo de carga del usuario final en el MVP.

---

## 6. Validación inicial de datos

Después de cargar los archivos de encuestas, el sistema debe mostrar un resumen de validación.

## 6.1 Validación de archivos de encuestas NPS

Debe mostrar:

- total de archivos cargados
- total de registros cargados
- total de registros nuevos integrados
- total de registros duplicados ignorados
- total de sucursales detectadas
- rango de fechas disponible
- meses disponibles para análisis
- columnas detectadas
- registros válidos
- registros con verbalización vacía
- registros con NPS inválido
- registros sin `Id_branch`
- registros duplicados por `RecordId`
- fechas inválidas

Ejemplo:

> Archivos procesados: 3.  
> Registros cargados: 84,230.  
> Registros nuevos integrados: 82,900.  
> Duplicados ignorados: 1,330.  
> Sucursales detectadas: 1,291.  
> Periodo disponible: enero-junio 2026.

---

## 6.2 Validación de cobertura de objetivos NPS internos

Como los objetivos NPS estarán precargados en backend, el sistema no validará un archivo subido por el usuario.

En su lugar, debe validar la cobertura entre las sucursales detectadas en los archivos de encuestas y los objetivos disponibles internamente.

Debe mostrar:

- total de sucursales detectadas en las encuestas
- total de sucursales con objetivo disponible
- sucursales detectadas sin objetivo configurado
- sucursales con objetivo configurado pero sin respuestas cargadas
- objetivos inválidos en la fuente interna
- objetivos duplicados por `Id_branch`, si existieran

Ejemplo:

> Se detectaron 1,291 sucursales en las encuestas.  
> 1,250 tienen NPS objetivo configurado.  
> 41 sucursales tienen respuestas, pero no tienen objetivo disponible.

---

## 7. Vista principal nacional Year To Date

Después de la carga, integración y validación, el sistema debe mostrar por default la vista nacional Year To Date.

Esta vista condensa toda la información de las sucursales disponibles en el conjunto de datos acumulado.

## 7.1 Métricas nacionales YTD

Debe mostrar:

1. NPS nacional actual.
2. NPS objetivo anual nacional.
3. Brecha contra objetivo.
4. Total de respuestas procesadas.
5. Total de sucursales detectadas.
6. Total de sucursales con objetivo configurado.
7. Distribución de promotores, pasivos y detractores.
8. Tendencia mensual nacional.
9. Principales causas de detracción.
10. Principales fortalezas detectadas.
11. Sucursales críticas.
12. Rankings de sucursales.
13. Acciones sugeridas.

---

## 7.2 NPS nacional actual

Es el NPS calculado con todas las respuestas cargadas dentro del periodo Year To Date.

Debe mostrarse como métrica principal.

---

## 7.3 NPS objetivo anual nacional

El NPS objetivo anual nacional se deriva de los objetivos precargados por sucursal.

Para MVP puede calcularse de manera simple como:

- promedio de los objetivos de las sucursales incluidas, o
- promedio ponderado por volumen de respuestas, si se decide usar volumen

Para mantener simplicidad, el MVP puede usar promedio simple, siempre indicando que es una aproximación operativa.

---

## 7.4 Brecha contra objetivo

La brecha es la diferencia entre:

> NPS actual nacional - NPS objetivo anual nacional

Ejemplo:

| Métrica | Valor |
|---|---:|
| NPS actual nacional | 61 |
| NPS objetivo anual nacional | 70 |
| Brecha | -9 |

---

## 7.5 Distribución de promotores, pasivos y detractores

Debe mostrar:

- porcentaje de promotores
- porcentaje de pasivos
- porcentaje de detractores
- conteo de promotores
- conteo de pasivos
- conteo de detractores

---

## 7.6 Principales causas de detracción

El sistema debe mostrar los temas más frecuentes en comentarios de detractores.

Ejemplos de causas:

1. Tiempo de espera
2. Falta de resolución
3. Problemas con app / NetKey
4. Mala actitud o baja disposición del personal
5. Gestión de turnos
6. Procesos burocráticos
7. Falta de personal
8. Problemas con cajeros o ventanilla

---

## 7.7 Principales fortalezas detectadas

El sistema debe mostrar los temas positivos más frecuentes en comentarios de promotores.

Ejemplos de fortalezas:

1. Amabilidad del personal
2. Atención rápida
3. Claridad en la explicación
4. Resolución efectiva
5. Profesionalismo
6. Paciencia
7. Buena asesoría
8. Trato personalizado

---

## 7.8 Sucursales críticas

Se añadirá una métrica específica de sucursales críticas.

Una sucursal crítica es una sucursal que requiere atención prioritaria por su desempeño de NPS, brecha contra objetivo o deterioro.

## Criterios propuestos para marcar una sucursal como crítica

Una sucursal puede considerarse crítica si cumple una o más condiciones:

1. Su NPS actual está por debajo del objetivo anual.
2. Su brecha contra objetivo supera un umbral negativo definido.
3. Tiene alto porcentaje de detractores.
4. Tiene deterioro frente a un mes anterior disponible.
5. Está dentro de las sucursales con peor NPS.
6. Tiene muchas menciones negativas en causas accionables como tiempo de espera, falta de resolución o mala atención.

Para el MVP, se recomienda usar una regla simple:

> Sucursal crítica = sucursal con NPS actual por debajo de su objetivo anual y/o ubicada dentro del top de peor brecha contra objetivo.

Si una sucursal no tiene objetivo configurado, no debe evaluarse por brecha contra objetivo. En ese caso, puede marcarse como “sin objetivo disponible” y evaluarse solo por NPS, detractores o deterioro mensual.

---

## 7.9 Ranking de sucursales

La vista nacional debe incluir rankings para conectar el panorama nacional con acciones concretas.

Rankings propuestos:

1. Sucursales con peor NPS.
2. Sucursales con mayor brecha negativa contra objetivo.
3. Sucursales con más detractores.
4. Sucursales que más empeoraron frente al mes anterior disponible.
5. Sucursales que más mejoraron frente al mes anterior disponible.

Estos rankings permiten al Gerente Nacional CX decidir dónde profundizar primero.

---

## 7.10 Acciones sugeridas nacionales

El sistema debe mostrar recomendaciones simples y accionables.

Ejemplos:

1. Priorizar intervención en sucursales críticas.
2. Revisar operación de turnos en sucursales con alta detracción por espera.
3. Capacitar personal en resolución de problemas de app / NetKey.
4. Replicar prácticas de sucursales con alta mención positiva en amabilidad y resolución.
5. Revisar procesos burocráticos en sucursales con alta mención de vueltas innecesarias.
6. Auditar sucursales con mayor brecha negativa contra objetivo.
7. Revisar sucursales sin objetivo configurado en la fuente interna.

---

## 8. Comparación nacional entre meses

El sistema debe permitir comparar únicamente meses disponibles en la información cargada.

No se debe prometer comparación contra año anterior, salvo que los datos cargados contengan explícitamente meses de años anteriores.

## 8.1 Selector de comparación

El usuario podrá seleccionar:

- Mes A
- Mes B

Ambos meses deben existir en el conjunto de datos acumulado.

Ejemplos válidos:

- enero 2026 vs febrero 2026
- febrero 2026 vs marzo 2026
- marzo 2026 vs junio 2026

---

## 8.2 Métricas de comparación nacional

Al comparar dos meses, el sistema debe mostrar:

1. NPS de Mes A vs NPS de Mes B.
2. Cambio en NPS.
3. Brecha contra objetivo en Mes A vs Mes B.
4. Cambio en brecha contra objetivo.
5. Distribución NPS en ambos meses.
6. Cambio en porcentaje de promotores.
7. Cambio en porcentaje de pasivos.
8. Cambio en porcentaje de detractores.
9. Principales causas de detracción en ambos meses.
10. Causas de detracción que subieron.
11. Causas de detracción que bajaron.
12. Fortalezas principales en ambos meses.
13. Fortalezas que subieron.
14. Fortalezas que bajaron.
15. Sucursales que más mejoraron.
16. Sucursales que más empeoraron.
17. Acciones sugeridas actualizadas.

---

## 8.3 Ejemplo de comparación nacional

| Métrica | Mes A | Mes B | Cambio |
|---|---:|---:|---:|
| NPS nacional | 58 | 64 | +6 |
| Promotores | 72% | 76% | +4 pp |
| Pasivos | 13% | 11% | -2 pp |
| Detractores | 15% | 13% | -2 pp |
| Respuestas | 12,300 | 13,100 | +800 |

Ejemplo de insight:

> De enero a febrero, el NPS nacional subió 6 puntos. La mejora se relaciona con una reducción de menciones negativas sobre tiempo de espera, aunque aumentaron las quejas sobre app / NetKey.

---

## 9. Selector de sucursal

Desde la vista nacional, el usuario podrá seleccionar una sucursal específica.

El selector debe permitir:

- buscar por `Id_branch`
- listar todas las sucursales detectadas
- seleccionar una sucursal
- volver a la vista de todas las sucursales
- acceder desde rankings de sucursales críticas o destacadas

La opción default será:

> Todas las sucursales

---

## 10. Vista de sucursal Year To Date

Cuando el usuario seleccione una sucursal, el sistema debe mostrar la vista Year To Date de esa sucursal.

Esta vista debe tener las mismas métricas base que la vista nacional, pero filtradas a la sucursal seleccionada.

## 10.1 Métricas YTD de sucursal

Debe mostrar:

1. `Id_branch` seleccionado.
2. NPS actual de la sucursal.
3. NPS objetivo anual de la sucursal.
4. Brecha contra objetivo.
5. Total de respuestas de la sucursal.
6. Distribución de promotores, pasivos y detractores.
7. Tendencia mensual de la sucursal.
8. Principales causas de detracción.
9. Principales fortalezas detectadas.
10. Acciones sugeridas.
11. Palabras frecuentes.
12. Comentarios representativos.
13. Personal mencionado en comentarios.

---

## 10.2 NPS actual de sucursal

Es el NPS calculado únicamente con las respuestas de la sucursal seleccionada.

---

## 10.3 NPS objetivo anual de sucursal

Es el NPS objetivo consultado desde la fuente interna precargada en backend para el `Id_branch` seleccionado.

Si la sucursal no tiene objetivo disponible, el sistema debe indicarlo claramente.

Ejemplo:

> Esta sucursal no tiene NPS objetivo configurado en la fuente interna.

---

## 10.4 Brecha contra objetivo de sucursal

La brecha es:

> NPS actual de sucursal - NPS objetivo anual de sucursal

Ejemplo:

| Métrica | Valor |
|---|---:|
| NPS actual sucursal | 55 |
| NPS objetivo anual | 68 |
| Brecha | -13 |

Si la sucursal no tiene objetivo disponible, no se calcula brecha contra objetivo y se muestra el estado:

> Brecha no disponible por falta de objetivo anual configurado.

---

## 10.5 Principales causas de detracción por sucursal

Debe mostrar los temas negativos más frecuentes en los comentarios de detractores de esa sucursal.

Ejemplo:

1. Tiempo de espera
2. No respetan turnos
3. Falta de resolución
4. Problemas con app / NetKey
5. Mala actitud del personal

---

## 10.6 Principales fortalezas por sucursal

Debe mostrar los temas positivos más frecuentes en los comentarios de promotores de esa sucursal.

Ejemplo:

1. Amabilidad
2. Rapidez
3. Buena explicación
4. Resolución de dudas
5. Profesionalismo

---

## 10.7 Palabras frecuentes por sucursal

La vista de sucursal debe mostrar palabras frecuentes.

Debe permitir distinguir:

- palabras frecuentes generales
- palabras frecuentes en promotores
- palabras frecuentes en detractores
- palabras frecuentes por mes disponible

Ejemplos de palabras relevantes:

- atención
- amable
- rápido
- espera
- turno
- app
- NetKey
- cajero
- gerente
- sucursal
- resolver
- trámite
- fila
- sistema
- ejecutivo

---

## 10.8 Comentarios representativos

La vista de sucursal debe mostrar comentarios reales que expliquen los insights.

Debe incluir:

- comentarios representativos de detractores
- comentarios representativos de promotores
- comentario asociado al tema detectado
- NPS del comentario
- fecha
- tema o categoría

Ejemplo:

> Tema: Tiempo de espera  
> NPS: 0  
> Comentario: “Duré casi dos horas esperando para ser atendido.”

---

## 10.9 Personal mencionado en comentarios

Esta métrica se mostrará a nivel sucursal.

Debe identificar comentarios donde se mencione personal específico o referencias al personal.

Debe mostrar:

- nombre mencionado, si se puede extraer
- tipo de mención:
  - positiva
  - negativa
- número de menciones
- comentario asociado
- fecha
- NPS
- tema relacionado

Ejemplo:

| Personal mencionado | Tipo | Menciones | Comentario ejemplo |
|---|---|---:|---|
| Diana | Positiva | 8 | “Diana fue muy amable y resolvió mis dudas.” |
| Gerente | Negativa | 3 | “El gerente no me dio solución.” |

Para el MVP, si la extracción de nombres no es perfecta, basta con detectar comentarios con menciones probables a personal.

---

## 11. Comparación de sucursal entre meses

La vista de sucursal debe permitir comparar únicamente meses disponibles para esa sucursal.

## 11.1 Selector de comparación por sucursal

El usuario podrá seleccionar:

- Mes A
- Mes B

Ambos meses deben existir en las respuestas de la sucursal seleccionada dentro del conjunto de datos acumulado.

---

## 11.2 Métricas de comparación por sucursal

Al comparar meses dentro de una sucursal, el sistema debe mostrar:

1. NPS de Mes A vs Mes B.
2. Cambio en NPS.
3. Brecha contra objetivo en Mes A vs Mes B.
4. Cambio en distribución NPS.
5. Cambio en porcentaje de promotores.
6. Cambio en porcentaje de pasivos.
7. Cambio en porcentaje de detractores.
8. Principales causas de detracción en ambos meses.
9. Causas de detracción que subieron.
10. Causas de detracción que bajaron.
11. Fortalezas principales en ambos meses.
12. Fortalezas que subieron.
13. Fortalezas que bajaron.
14. Cambio en palabras frecuentes.
15. Comentarios representativos de cada mes.
16. Acciones sugeridas actualizadas.
17. Cambios en personal mencionado, si aplica.

---

## 12. Insights principales del sistema

## 12.1 Insights nacionales

El sistema debe generar insights como:

- “El NPS nacional YTD está X puntos por debajo del objetivo anual.”
- “Las principales causas de detracción son tiempo de espera, falta de resolución y problemas con app / NetKey.”
- “Las principales fortalezas son amabilidad, atención rápida y claridad en la explicación.”
- “Hay X sucursales críticas por brecha negativa contra objetivo.”
- “Las sucursales con peor NPS son A-001, A-245 y A-879.”
- “Las sucursales que más empeoraron frente al mes anterior disponible son A-123, A-456 y A-789.”
- “Las sucursales que más mejoraron frente al mes anterior disponible son A-321, A-654 y A-987.”
- “Hay X sucursales con respuestas cargadas pero sin objetivo disponible.”
- “La acción prioritaria es intervenir sucursales con alta detracción por tiempo de espera.”

---

## 12.2 Insights de sucursal

El sistema debe generar insights como:

- “La sucursal A-1234 tiene un NPS YTD de 55 contra objetivo de 68.”
- “La brecha de la sucursal es de -13 puntos.”
- “La sucursal A-1234 no tiene objetivo anual disponible en la fuente interna.”
- “El principal motivo de detracción es tiempo de espera.”
- “Los promotores destacan amabilidad y claridad en la explicación.”
- “En los detractores se repiten las palabras espera, turno y app.”
- “Se detectaron menciones positivas al personal Diana y menciones negativas al gerente.”
- “De enero a febrero, la sucursal mejoró 5 puntos de NPS.”
- “La acción prioritaria para esta sucursal es reducir tiempos de espera y revisar gestión de turnos.”

---

## 13. Acciones sugeridas

Las acciones sugeridas deben ser simples, no reportes largos.

Deben derivarse de los principales problemas detectados.

## 13.1 Ejemplos de acciones sugeridas nacionales

- Priorizar intervención en sucursales críticas.
- Revisar operación de turnos en sucursales con alta mención negativa de espera.
- Reforzar capacitación en resolución de problemas de app / NetKey.
- Replicar prácticas de sucursales con alta mención positiva de amabilidad.
- Auditar sucursales con mayor brecha negativa contra objetivo.
- Revisar procesos que generan múltiples visitas o vueltas innecesarias.
- Revisar sucursales sin objetivo configurado en la fuente interna.

---

## 13.2 Ejemplos de acciones sugeridas por sucursal

- Reducir tiempos de espera en ventanilla.
- Revisar funcionamiento del sistema de turnos.
- Aumentar claridad en explicación de trámites.
- Reforzar capacitación del personal sobre app / NetKey.
- Revisar casos donde clientes reportan falta de resolución.
- Reconocer y replicar buenas prácticas del personal con menciones positivas.
- Atender menciones negativas recurrentes hacia personal o gerencia.

---

## 14. Taxonomía base para clasificar comentarios

El sistema puede apoyarse en una taxonomía de voz del cliente para organizar los comentarios.

Categorías principales:

1. Atención al cliente
2. Tiempos y operación
3. Sucursal física
4. Cajeros automáticos
5. Canales digitales
6. Productos
7. Operaciones transaccionales
8. Costos
9. Aclaraciones, quejas y fraude
10. Procesos y requisitos
11. Programas y beneficios
12. Comunicación y notificaciones
13. Marca y confianza
14. Elogio o queja genérica sin tema específico
15. Otros / No clasificable

Para MVP, no es obligatorio mostrar toda la taxonomía completa en la interfaz. Se pueden mostrar agrupaciones simplificadas y accionables.

---

## 15. Fuera de alcance por ahora

Queda fuera de esta definición:

- arquitectura final del sistema
- modelo definitivo de base de datos
- cálculo avanzado de confianza
- validación estadística profunda
- permisos complejos por jerarquía
- funcionalidad completa del rol Administrador
- gerente de zona
- gerente regional
- directivo nacional como rol separado
- integración con sistemas reales del banco
- automatización de reportes
- seguimiento de acciones correctivas
- workflows de aprobación
- predicción de NPS futuro
- explicación avanzada del modelo de IA

No queda fuera el motor de análisis. El motor sí forma parte del MVP, pero su desarrollo específico queda pendiente.

---

## 16. Criterio de éxito del MVP

El MVP será exitoso si permite demostrar que:

1. El usuario puede cargar uno o varios archivos de encuestas NPS multisucursal.
2. El usuario puede cargar archivos adicionales después de un procesamiento inicial.
3. El sistema integra nuevos registros al conjunto de datos acumulado.
4. El sistema evita duplicados usando `RecordId`.
5. El sistema consulta objetivos NPS anuales por sucursal desde una fuente interna precargada.
6. El sistema detecta sucursales por `Id_branch`.
7. El sistema muestra una vista nacional Year To Date.
8. El sistema calcula NPS nacional actual.
9. El sistema calcula o aproxima NPS objetivo nacional a partir de objetivos internos por sucursal.
10. El sistema muestra brecha contra objetivo.
11. El sistema muestra distribución de promotores, pasivos y detractores.
12. El sistema muestra principales causas de detracción.
13. El sistema muestra principales fortalezas.
14. El sistema identifica sucursales críticas.
15. El sistema muestra rankings de sucursales.
16. El sistema permite comparar meses disponibles.
17. El sistema permite seleccionar una sucursal.
18. El sistema muestra vista Year To Date de sucursal.
19. El sistema muestra métricas granulares de sucursal.
20. El sistema muestra personal mencionado en comentarios de sucursal.
21. El sistema genera acciones sugeridas.
22. El flujo es entendible para una demo ejecutiva.
23. El sistema ayuda a decidir dónde actuar primero.
24. El rol Administrador queda representado visualmente como POC, aunque no tenga funcionalidad completa.

---

## 17. Resumen ejecutivo del diseño actual

El MVP será una plataforma de análisis CX enfocada en un Gerente Nacional CX.

El usuario podrá cargar uno o varios archivos de encuestas NPS con múltiples sucursales. Si posteriormente carga más archivos, el sistema integrará los nuevos registros al conjunto de datos acumulado, evitando duplicados mediante `RecordId`.

Los objetivos NPS anuales por sucursal no serán cargados manualmente por el usuario en el MVP. El sistema los consultará desde una fuente interna precargada en backend, generada previamente a partir de las sucursales existentes.

El sistema procesará la información, detectará las sucursales por `Id_branch` y mostrará primero una vista nacional Year To Date.

La vista nacional mostrará NPS actual, objetivo anual, brecha contra objetivo, distribución de promotores/pasivos/detractores, principales causas de detracción, principales fortalezas, sucursales críticas, rankings de sucursales y acciones sugeridas.

Después, el usuario podrá comparar meses disponibles y seleccionar una sucursal específica. Al seleccionar una sucursal, verá las mismas métricas filtradas a esa sucursal, además de información granular como palabras frecuentes, comentarios representativos y personal mencionado en comentarios.

El rol Administrador existirá como representación POC dentro de la interfaz, con distinción visual de secciones administrativas, pero sin necesidad de funcionalidad completa para el MVP.

La lógica principal del sistema será:

> Carga multisucursal incremental → validación → integración sin duplicados → consulta de objetivos internos → vista nacional YTD → comparación entre meses disponibles → ranking de sucursales → selección de sucursal → vista granular YTD → comparación mensual de sucursal → acciones sugeridas.

---

## Anexo — Árbol L1/L2/L3 (consumido por `engine.taxonomy.load_taxonomy`)

Esta sección expande las 15 categorías raíz de §14 con subcategorías L2 y hojas L3.
Es la fuente parseable por `engine.taxonomy.load_taxonomy()` (M2a). Formato fijo:

- L1 = `#### N. **Nombre**`
- L2 = `- **N.M Nombre**`
- L3 = `    - N.M.K Nombre` (cuatro espacios de indentación)

Cualquier cambio en estos códigos rompe contratos cruzados con M2a y M2b. Si una
sesión cree que la jerarquía debe cambiar, anota en `plan_implementacion/contracts_issues.md`.

#### 1. **Atención al cliente**

- **1.1 Trato del personal**
    - 1.1.1 Amabilidad y cortesía
    - 1.1.2 Trato distante o grosero
- **1.2 Calidad de la atención**
    - 1.2.1 Atención general en sucursal
    - 1.2.2 Trato al ofrecer productos o promociones
- **1.3 Disponibilidad de personal**
    - 1.3.1 Falta de personal disponible
    - 1.3.2 Personal ausente del puesto
- **1.4 Conocimiento del personal**
    - 1.4.1 Asesoría correcta
    - 1.4.2 Falta de conocimiento del producto
- **1.5 Resolución de problemas**
    - 1.5.1 Resolución efectiva
    - 1.5.2 Falta de resolución

#### 2. **Tiempos y operación**

- **2.1 Tiempo de espera**
    - 2.1.1 Espera larga reportada
    - 2.1.2 Espera razonable o rápida
- **2.2 Velocidad de atención**
    - 2.2.1 Atención ágil
    - 2.2.2 Atención lenta
    - 2.2.3 Espera operativa en sucursal o ventanilla
- **2.3 Gestión de turnos y filas**
    - 2.3.1 No respetan turnos
    - 2.3.2 Buena gestión de turnos

#### 3. **Sucursal física**

- **3.1 Limpieza e instalaciones**
    - 3.1.1 Sucursal limpia y ordenada
    - 3.1.2 Sucursal en mal estado
- **3.2 Comodidad y mobiliario**
    - 3.2.1 Mobiliario adecuado
    - 3.2.2 Mobiliario insuficiente o incómodo
- **3.3 Ubicación y accesibilidad**
    - 3.3.1 Ubicación conveniente
    - 3.3.2 Estacionamiento o accesibilidad limitada

#### 4. **Cajeros automáticos**

- **4.1 Disponibilidad de cajeros**
    - 4.1.1 Cajeros disponibles
    - 4.1.2 Cajeros fuera de servicio
- **4.2 Fallos de cajeros**
    - 4.2.1 Cajero retuvo tarjeta
    - 4.2.2 Cajero no completó la operación
- **4.3 Dispensación y servicios**
    - 4.3.1 Falta de billetes
    - 4.3.2 Diversidad de denominaciones
- **4.4 Seguridad en cajeros**
    - 4.4.1 Cajeros en zona segura
    - 4.4.2 Inseguridad en cajeros

#### 5. **Canales digitales**

- **5.1 App móvil**
    - 5.1.1 App funcional
    - 5.1.2 Fallos de la app
    - 5.1.3 Problemas con NetKey o token
- **5.2 Banca por internet**
    - 5.2.1 Portal funcional
    - 5.2.2 Fallos del portal
- **5.3 Centro de atención telefónica**
    - 5.3.1 Atención telefónica resolutiva
    - 5.3.2 Espera o desconexión en call center
- **5.4 Chat y WhatsApp**
    - 5.4.1 Chat resolutivo
    - 5.4.2 Chat sin respuesta

#### 6. **Productos**

- **6.1 Tarjetas de crédito**
    - 6.1.1 Beneficios de la tarjeta
    - 6.1.2 Problemas con la tarjeta de crédito
- **6.2 Tarjetas de débito**
    - 6.2.1 Uso correcto de tarjeta de débito
    - 6.2.2 Problemas con la tarjeta de débito
- **6.3 Créditos**
    - 6.3.1 Crédito aprobado o útil
    - 6.3.2 Negativa o demora del crédito
- **6.4 Cuentas e inversiones**
    - 6.4.1 Buen rendimiento o servicio
    - 6.4.2 Problemas con cuentas e inversiones
- **6.5 Promociones y ofertas**
    - 6.5.1 Promoción o producto con fricción
    - 6.5.2 Promoción atractiva

#### 7. **Operaciones transaccionales**

- **7.1 Depósitos y retiros**
    - 7.1.1 Depósito o retiro correcto
    - 7.1.2 Problema con depósito o retiro
- **7.2 Transferencias**
    - 7.2.1 Transferencia exitosa
    - 7.2.2 Transferencia con fallo o demora
- **7.3 Pago de servicios**
    - 7.3.1 Pago de servicios correcto
    - 7.3.2 Problema con pago de servicios

#### 8. **Costos**

- **8.1 Comisiones**
    - 8.1.1 Comisiones razonables
    - 8.1.2 Comisiones altas o injustificadas
- **8.2 Intereses**
    - 8.2.1 Intereses razonables
    - 8.2.2 Intereses altos
- **8.3 Cobros inesperados**
    - 8.3.1 Cobro no esperado
    - 8.3.2 Cargo recurrente cuestionado

#### 9. **Aclaraciones, quejas y fraude**

- **9.1 Aclaraciones de cargos**
    - 9.1.1 Aclaración resuelta
    - 9.1.2 Aclaración pendiente
- **9.2 Fraude y cargos no reconocidos**
    - 9.2.1 Reporte de fraude atendido
    - 9.2.2 Fraude no atendido
- **9.3 Manejo de quejas**
    - 9.3.1 Queja atendida
    - 9.3.2 Queja no atendida

#### 10. **Procesos y requisitos**

- **10.1 Trámites y documentación**
    - 10.1.1 Trámite ágil
    - 10.1.2 Trámite demorado
- **10.2 Apertura y cierre de productos**
    - 10.2.1 Proceso de apertura fluido
    - 10.2.2 Cierre de producto complicado
- **10.3 Requisitos y procesos internos**
    - 10.3.1 Requisitos claros
    - 10.3.2 Requisitos excesivos
    - 10.3.3 Proceso interno burocrático

#### 11. **Programas y beneficios**

- **11.1 Programa de puntos**
    - 11.1.1 Puntos acumulados o canjeados
    - 11.1.2 Problemas con puntos
- **11.2 Beneficios y recompensas**
    - 11.2.1 Beneficios bien aprovechados
    - 11.2.2 Beneficios sin valor percibido

#### 12. **Comunicación y notificaciones**

- **12.1 Notificaciones recibidas**
    - 12.1.1 Notificación útil
    - 12.1.2 Notificación excesiva o spam
- **12.2 Información proactiva**
    - 12.2.1 Información clara
    - 12.2.2 Falta de información

#### 13. **Marca y confianza**

- **13.1 Confianza institucional**
    - 13.1.1 Banco confiable
    - 13.1.2 Pérdida de confianza
- **13.2 Reputación**
    - 13.2.1 Buena reputación
    - 13.2.2 Mala reputación

#### 14. **Elogio o queja genérica sin tema específico**

- **14.1 Elogio genérico**
    - 14.1.1 Comentario positivo sin tema
- **14.2 Queja genérica**
    - 14.2.1 Comentario negativo sin tema

#### 15. **Otros / No clasificable**

- **15.1 Texto sin contenido temático**
- **15.2 Texto incomprensible**
- **15.3 Otros temas**
    - 15.3.1 Tema fuera del banco
- **15.4 No clasificable**