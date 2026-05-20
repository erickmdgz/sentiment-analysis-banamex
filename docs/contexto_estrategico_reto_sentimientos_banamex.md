# Contexto estratégico del reto: Análisis de sentimientos y voz del cliente en sucursales Banamex

## 1. Propósito del documento

Este documento resume el contexto estratégico del reto de análisis de sentimientos presentado por Banamex para el Hackathon Banamex Tec de Monterrey.

El objetivo es alinear al equipo sobre:

- el problema de negocio;
- la relevancia del reto para Experiencia del Cliente;
- los datos disponibles;
- lo que se espera lograr;
- los KPIs y criterios de evaluación;
- las restricciones y consideraciones clave del reto.

Este documento no propone todavía una solución técnica, arquitectura, modelo, dashboard ni metodología de implementación.

---

## 2. Área responsable y contexto de Experiencia del Cliente

El reto está planteado desde el área de **Experiencia del Cliente** de Banamex.

Esta área es responsable de entender, medir y mejorar la experiencia de los clientes en los distintos segmentos, canales y productos del banco.

Sus funciones principales incluyen:

- recopilar la voz del cliente;
- entender las verdaderas necesidades de los clientes;
- acompañar y apoyar al cliente a lo largo de sus diferentes momentos con el banco;
- identificar fricciones y oportunidades de mejora.

Uno de sus principales retos es transformar grandes volúmenes de comentarios de clientes en hallazgos clave, recomendaciones de negocio y acciones concretas.

---

## 3. NPS como indicador central

Banamex mide la experiencia del cliente mediante el **NPS, Net Promoter Score**.

El NPS mide el nivel de recomendación que los clientes darían al banco. En el caso del canal sucursal, la pregunta base es:

> Con base en tu visita realizada a la Sucursal [Nombre de Sucursal] de Banamex, ¿qué tanto recomendarías Banamex a un familiar o amigo?

La escala utilizada va de **0 a 10**.

El NPS permite identificar grupos de clientes como:

- promotores;
- pasivos;
- detractores.

El uso del NPS busca apoyar decisiones relacionadas con:

- incremento de lealtad de clientes;
- incremento de rentabilidad de clientes;
- incremento de atracción de clientes.

---

## 4. Contexto del negocio

Actualmente, algunos de los principales indicadores de Banamex en canales, productos y segmentos están relacionados con la experiencia del cliente.

En este contexto, escuchar al cliente, entenderlo, resolver las fricciones percibidas y desarrollar productos y servicios considerando su voz es una actividad crítica para el negocio.

Banamex realiza múltiples esfuerzos para conocer la voz del cliente. Uno de los principales mecanismos son las encuestas.

De forma general, el banco encuesta a más de **1.2 millones de clientes al año**, con un promedio superior a **105 mil encuestas mensuales**. Cada encuesta contiene variables estructuradas y verbalizaciones abiertas del cliente.

---

## 5. Dolor o necesidad identificada

El dolor principal es dar seguimiento de manera ágil y precisa a la voz del cliente.

La necesidad consiste en identificar puntos de dolor a partir de las verbalizaciones de los clientes para apoyar el desarrollo de productos, servicios y acciones alineadas con la experiencia real del cliente.

El reto surge porque el volumen de comentarios hace difícil convertir la información abierta en hallazgos accionables de forma rápida, consistente y escalable.

---

## 6. Descripción del reto

El reto consiste en analizar una base de encuestas del canal **Sucursal** para mejorar el entendimiento del cliente y de sus puntos de dolor.

El entendimiento del cliente debe surgir del análisis conjunto de:

- verbalizaciones abiertas;
- sentimiento del cliente;
- NPS de las encuestas.

El objetivo es generar una herramienta que permita identificar y priorizar la atención de las necesidades del cliente.

---

## 7. Qué busca mejorar Banamex

Banamex busca mejorar el entendimiento de los puntos de dolor del cliente mediante una clasificación oportuna de verbalizaciones.

La clasificación debe permitir detonar acciones con impacto en corto plazo, apoyar la mejora del NPS y aumentar la agilidad del procesamiento de la voz del cliente.

---

## 8. Impacto actual del canal sucursal

El reto se enfoca en el canal sucursal, que tiene una escala operativa relevante dentro de Banamex.

De acuerdo con la presentación, el canal cuenta con:

- más de **1.2 mil sucursales** en todo el país;
- más de **4 millones de turnos al mes**;
- más de **8 millones de transacciones al mes**;
- alcance anual de más de **390 mil encuestas** en sucursal.

El objetivo declarado es diseñar soluciones que atiendan las fricciones que viven los clientes en sucursal.

---

## 9. Por qué el reto es importante

El análisis exitoso de verbalizaciones, sentimiento y NPS de clientes del canal sucursal permitiría entender mejor las fricciones del cliente y agilizar la toma de decisiones.

También es relevante porque Banamex espera que el modelo pueda escalar posteriormente a otros canales, productos y segmentos.

Esto significa que el reto no se limita a resolver un caso aislado de sucursales, sino que se plantea como una oportunidad para construir una capacidad reutilizable de análisis de voz del cliente.

---

## 10. Datos disponibles

La base de trabajo contiene **474,026 registros**.

Las encuestas incluyen verbalizaciones de clientes desde **enero de 2025 hasta abril de 2026**.

### Distribución general por año

| Año | Registros |
|---|---:|
| 2025 | 371,649 |
| 2026 | 102,377 |
| **Total** | **474,026** |

### Distribución mensual

| Periodo | Registros |
|---|---:|
| Enero 2025 | 36,399 |
| Febrero 2025 | 28,505 |
| Marzo 2025 | 33,074 |
| Abril 2025 | 33,790 |
| Mayo 2025 | 33,942 |
| Junio 2025 | 32,207 |
| Julio 2025 | 32,782 |
| Agosto 2025 | 29,133 |
| Septiembre 2025 | 28,716 |
| Octubre 2025 | 30,412 |
| Noviembre 2025 | 29,377 |
| Diciembre 2025 | 23,312 |
| Enero 2026 | 27,484 |
| Febrero 2026 | 23,976 |
| Marzo 2026 | 27,170 |
| Abril 2026 | 23,747 |

---

## 11. Diccionario de datos

| Campo | Descripción | Ejemplo |
|---|---|---|
| Fecha de respuesta | Fecha en que se respondió la encuesta | 01/01/2025 |
| NPS_GROUP | Grupo del NPS | Promotor |
| NPS_Rate | Resultado numérico del NPS | 10 |
| Verbalización | Comentario de la encuesta del cliente | Comentario abierto del cliente |
| RecordId | ID de la encuesta | R_5eCRumeaLPTDnUd |
| Id_branch | ID de la sucursal | A-864 |

---

## 12. Qué se espera lograr

Banamex espera identificar hallazgos centrados en:

- la correcta identificación de puntos de dolor;
- el sentimiento del cliente;
- el impacto en el NPS;
- recomendaciones de acciones centradas en la voz del cliente.

La expectativa no se limita a clasificar comentarios. También se espera que el análisis produzca hallazgos que puedan orientar acciones de negocio.

---

## 13. KPIs evaluados

Los KPIs planteados para el reto son:

### 13.1 Cobertura de categorización

Se evaluará la cobertura de categorización de verbalizaciones de clientes en los grupos:

- promotor;
- pasivo;
- detractor.

La categorización debe considerar tópicos concretos.

También se solicita contar con al menos **3 niveles de categorización**.

### 13.2 Precisión de clasificación

Se evaluará la precisión en la clasificación de:

- verbalizaciones;
- sentimientos.

### 13.3 Puntos de fricción

Se evaluará la cantidad de puntos de fricción identificados por categoría de verbalización.

### 13.4 Impacto en NPS

Se debe identificar el impacto de cada categoría de verbalizaciones en el NPS.

La presentación lo expresa como la necesidad de responder cuántos puntos se pierden por cada temática.

### 13.5 Motor de procesamiento y categorización

Se espera la creación de un motor de procesamiento y categorización de verbalizaciones.

Este motor debe contemplar:

- nivel de automatización del proceso de carga de nuevas verbalizaciones;
- proceso escalable para expandirse posteriormente a otros estudios de NPS con problemáticas diferentes.

---

## 14. Resultado ideal esperado

De acuerdo con la presentación, el resultado ideal considera:

- cobertura de verbalizaciones, categorías, sentimientos e impactos al NPS superior al **95%**;
- desarrollo de al menos **8 categorías de clasificación**;
- precisión en clasificación de verbalizaciones y sentimientos superior al **75%**;
- al menos **1 punto de fricción por categoría**;
- impacto en NPS de al menos las **3 categorías principales por grupo NPS**;
- confianza superior al **80%** en el impacto en NPS;
- compatibilidad del motor de procesamiento con más de **3 canales**;
- precisión del motor de análisis de verbalizaciones superior al **85%**.

---

## 15. Consideraciones importantes del reto

La presentación establece cinco consideraciones clave que deben tomarse en cuenta al desarrollar el reto.

### 15.1 Multiclase

Una verbalización puede hablar de más de un tema y contener varios puntos de fricción.

### 15.2 Grupos NPS

Las categorías pueden tener diferentes sentimientos o interpretaciones entre grupos de NPS.

Esto implica que una misma temática puede comportarse de forma distinta entre promotores, pasivos y detractores.

### 15.3 Canales

Aunque las encuestas pertenecen al canal sucursal, las verbalizaciones pueden hacer mención de otros canales o productos.

### 15.4 Impacto

Se debe identificar el impacto y la sensibilidad de cada categoría, entendida como cuántos puntos impacta en NPS cada tema.

### 15.5 Priorización

Se espera priorizar los principales puntos de dolor a atender.

---

## 16. Qué le importa más a Banamex al resolver el reto

La presentación destaca dos prioridades principales:

1. Proveer recomendaciones centradas en la voz del cliente que atiendan los puntos de dolor identificados en el análisis.
2. Considerar la escalabilidad del motor de procesamiento a diferentes estudios de NPS, incluyendo otros productos y canales.

Estas prioridades muestran que el reto tiene una orientación de negocio y escalabilidad, no únicamente de análisis descriptivo.

---

## 17. Criterios de evaluación

Los criterios de evaluación declarados son los siguientes.

### 17.1 Alcance del motor de procesamiento

Se evaluará el porcentaje de verbalizaciones categorizadas respecto al total de la base.

### 17.2 Confianza de clasificación

Se evaluará la correcta categorización de las categorías.

### 17.3 Calidad de hallazgos

Se evaluará la calidad de los hallazgos que aporten valor, considerando creatividad.

### 17.4 Escalabilidad

Se evaluará la capacidad de adaptación a más canales, productos y segmentos.

---

## 18. Implicaciones estratégicas del reto, sin definir solución

El reto debe entenderse como una necesidad de convertir voz del cliente en insumos accionables para el negocio.

Desde una perspectiva estratégica, el trabajo del equipo debe mantenerse alineado con cuatro exigencias del caso:

1. **Entendimiento del cliente**: no solo procesar texto, sino organizar lo que el cliente expresa sobre su experiencia.
2. **Relación con NPS**: conectar verbalizaciones, sentimiento y categorías con impacto en el indicador.
3. **Priorización de fricciones**: distinguir qué puntos de dolor requieren mayor atención.
4. **Escalabilidad**: considerar que la capacidad desarrollada pueda extenderse a otros estudios, canales, productos y segmentos.

Estas implicaciones no definen aún cómo debe construirse la solución. Solo delimitan lo que el reto considera valioso.

---

## 19. Límites de este documento

Este documento no incluye:

- propuesta de arquitectura;
- selección de modelos;
- diseño de pipeline;
- diseño de dashboard;
- taxonomía de categorías propuesta;
- metodología de validación;
- estrategia de presentación final;
- interpretación propia de la solución.

Su función es dejar claro el contexto, la intención del reto, los datos disponibles, las expectativas y los criterios contra los que será evaluado el trabajo.
