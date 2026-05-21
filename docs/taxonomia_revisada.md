# Taxonomía revisada — Voz del cliente Banamex

## Resumen de cambios vs versión anterior

**Movidos a metadatos transversales** (no son temas, son atributos que aplican sobre cualquier verbalización):
- *Identificación del personal* (antes 1.3) → flag `personal_nominado`. Se puede tener elogio nominado con mala actitud, así que es un eje ortogonal, no una categoría.
- *NPS verbal explícito* (antes 13.3) → flag `recomendacion_explicita`. Es señal sobre la verbalización, no un tema del que se hable.
- Añadidos también `mencion_otro_banco` y `canal_mencionado` para enriquecer el análisis sin inflar la taxonomía.

**Renombrado a neutral**:
- 1.1.2 *Mala actitud / grosería* → *Actitud / disposición*. El sentimiento lo asigna ABSA; la taxonomía no debe llevar polaridad incorporada o el modelo se confunde entre "amabilidad-negativa" y "mala actitud" para la misma frase.

**Aperturas de L3 donde la sección estaba sub-desarrollada**:
- 5.3 (canales no-app) ahora distingue banca telefónica humana, IVR y chat/WhatsApp — son experiencias operativamente distintas.
- 7.2 / 7.3 / 7.4 (operaciones transaccionales) ahora tienen L3, porque suele ser donde hay más volumen de queja específica.
- 4.2 (errores ATM) abre sub-tipos accionables (sin comprobante, pantalla, software genérico) porque cada uno apunta a un equipo distinto dentro del banco.

**Coberturas nuevas que faltaban**:
- 1.3 *Atención diferenciada* (cajas para adultos mayores, discapacidad). Tema sensible y recurrente.
- 3.4 *Horarios de sucursal*. Reclamo previsible que no tenía nodo.
- 10.4 *Diferenciación cliente / no-cliente*. Aparece seguro en encuestas de sucursal.
- 13.3 *Transición post-Citi*. Banamex tiene un evento institucional reciente que el cliente verbaliza.

**Notas de desambiguación** en tres clusters problemáticos:
- 1.2.2 vs 6.5.1 (engaño general vs engaño para vender).
- 2.2.3 vs 10.3 (síntoma "muchas vueltas" vs causa "procesos burocráticos").
- 8.3 vs 9.1 vs 9.2 (cargo no reconocido vs proceso de aclaración vs fraude). Este es el solapamiento más peligroso porque una misma queja puede legítimamente caer en los tres.

**Resultado volumétrico**: 15 L1, 48 L2, ~90 L3 — dentro del rango defendible para arrancar, con regla automática de colapsar hojas que no acumulen >100 menciones/mes hacia su L2 padre.

---

## Metadatos transversales

No son categorías. Son atributos extraídos en paralelo a la clasificación, aplicables a cualquier verbalización.

- `personal_nominado` → bool + nombre extraído + polaridad (elogio / queja).
- `recomendacion_explicita` → positiva / negativa / null. Captura frases tipo "lo recomiendo" o "no se lo recomiendo a nadie".
- `mencion_otro_banco` → bool + entidad mencionada (BBVA, Banorte, Santander, HSBC, etc.). Útil para benchmarks competitivos.
- `canal_mencionado` → lista de canales referidos (sucursal, app, ATM, telefónica, web, WhatsApp). Permite triangular incluso cuando la encuesta es de sucursal.

---

## Taxonomía

#### 1. **Atención al cliente**
- **1.1 Trato del personal**
  - 1.1.1 Amabilidad / cordialidad
  - 1.1.2 Actitud / disposición
  - 1.1.3 Empatía y paciencia
  - 1.1.4 Profesionalismo / capacitación percibida
  - 1.1.5 Favoritismo / discriminación entre clientes
- **1.2 Calidad de la asesoría**
  - 1.2.1 Claridad en la explicación
  - 1.2.2 Información incorrecta o engañosa
  - 1.2.3 Falta de conocimiento del producto
  - 1.2.4 Resolución efectiva del problema
- **1.3 Atención diferenciada**
  - 1.3.1 Cajas / filas especiales (adultos mayores, embarazadas)
  - 1.3.2 Respeto a la prioridad declarada
  - 1.3.3 Atención a personas con discapacidad

> Nota: 1.2.2 "Información incorrecta o engañosa" se usa cuando el cliente percibe engaño general. Si el engaño es específicamente para colocar un producto, va a **6.5.1 Venta cruzada no solicitada**.

#### 2. **Tiempos y operación**
- **2.1 Tiempo de espera**
  - 2.1.1 Espera en sucursal / fila
  - 2.1.2 Espera para ser atendido tras tomar turno
  - 2.1.3 Espera en línea telefónica / call center
- **2.2 Duración del trámite**
  - 2.2.1 Trámite ágil
  - 2.2.2 Trámite excesivamente largo
  - 2.2.3 Requerir múltiples visitas / vueltas
- **2.3 Gestión de turnos**
  - 2.3.1 Sistema de fichas / pantallas
  - 2.3.2 No respetan turno

> Nota: 2.2.3 ("múltiples vueltas") se usa cuando el cliente describe el *síntoma* (tuvo que volver). 10.3 ("procesos burocráticos") se usa cuando describe la *causa estructural* (el banco le pidió cosas innecesarias). Si menciona ambas, etiquetar ambas.

#### 3. **Sucursal física**
- **3.1 Instalaciones**
  - 3.1.1 Limpieza
  - 3.1.2 Confort (aire acondicionado, asientos)
  - 3.1.3 Accesibilidad / señalización
  - 3.1.4 Privacidad en el área de atención
- **3.2 Ubicación**
  - 3.2.1 Estacionamiento
  - 3.2.2 Cercanía / disponibilidad de sucursales
- **3.3 Seguridad física**
  - 3.3.1 Personal de seguridad / vigilancia
- **3.4 Horarios**
  - 3.4.1 Horario de apertura / cierre
  - 3.4.2 Horario reducido / cierres no anunciados
  - 3.4.3 Disponibilidad fines de semana

#### 4. **Cajeros automáticos (ATM)**
- **4.1 Disponibilidad**
  - 4.1.1 Cajero fuera de servicio
  - 4.1.2 Sin efectivo
- **4.2 Funcionalidad**
  - 4.2.1 Retiro fallido / dinero retenido
  - 4.2.2 Tarjeta retenida
  - 4.2.3 No entrega comprobante
  - 4.2.4 Pantalla / interfaz con fallas
  - 4.2.5 Otros errores de software

#### 5. **Canales digitales**
- **5.1 App móvil**
  - 5.1.1 Fallas de acceso / login
  - 5.1.2 Lentitud o caídas
  - 5.1.3 Errores en transferencias / pagos desde app
  - 5.1.4 Compatibilidad con dispositivo (Android, iOS, Huawei, etc.)
  - 5.1.5 Diseño / usabilidad
- **5.2 Banca por internet (web)**
  - 5.2.1 Acceso al portal
  - 5.2.2 Token / Netkey
  - 5.2.3 Errores de operación web
- **5.3 Banca telefónica y mensajería**
  - 5.3.1 Banca telefónica con agente humano
  - 5.3.2 IVR / menú automatizado telefónico
  - 5.3.3 Chat / WhatsApp / asistente conversacional

#### 6. **Productos**
- **6.1 Tarjetas**
  - 6.1.1 Crédito (límite, intereses, beneficios)
  - 6.1.2 Débito
  - 6.1.3 Reposición / extravío / robo
  - 6.1.4 Entrega de plástico
- **6.2 Crédito y préstamos**
  - 6.2.1 Préstamo personal / de nómina
  - 6.2.2 Hipotecario
  - 6.2.3 Automotriz
  - 6.2.4 Liquidación / cancelación anticipada
- **6.3 Cuentas y ahorro**
  - 6.3.1 Apertura de cuenta
  - 6.3.2 Cancelación de cuenta
  - 6.3.3 Nómina
- **6.4 Inversiones**
  - 6.4.1 CETES / pagaré / fondos
- **6.5 Seguros**
  - 6.5.1 Venta cruzada no solicitada
  - 6.5.2 Cobertura / reclamación

#### 7. **Operaciones transaccionales**
- **7.1 Depósitos y retiros en ventanilla**
  - 7.1.1 Depósito no acreditado
  - 7.1.2 Límites de monto en ventanilla
- **7.2 Transferencias (SPEI / mismo banco)**
  - 7.2.1 Transferencia rechazada / no llega
  - 7.2.2 SPEI duplicado o cargo doble
  - 7.2.3 Demora en acreditación
- **7.3 Pagos de servicios / domiciliaciones**
  - 7.3.1 Pago de servicio no aplicado
  - 7.3.2 Domiciliación incorrecta o no autorizada
- **7.4 Cambio de divisas**
  - 7.4.1 Tipo de cambio percibido como injusto
  - 7.4.2 Disponibilidad de USD u otras divisas

#### 8. **Costos**
- **8.1 Comisiones**
  - 8.1.1 Comisión por manejo de cuenta
  - 8.1.2 Comisión por operación
- **8.2 Tasas de interés**
- **8.3 Cargos no reconocidos**

> Nota de desambiguación entre 8.3 / 9.1 / 9.2:
> - **8.3 Cargos no reconocidos**: el cliente reporta el *cargo en sí* como problema. Aún no ha iniciado proceso de aclaración o no lo menciona.
> - **9.1 Aclaraciones**: el cliente describe su experiencia con el *proceso de aclaración* (tiempos, resultado, trato).
> - **9.2 Fraude / clonación**: el cliente atribuye el cargo a un *tercero malicioso* (clonación, phishing, robo de identidad).
> - Una verbalización puede tener las tres etiquetas si el cliente narra el caso completo. Es comportamiento esperado, no error.

#### 9. **Aclaraciones, quejas y fraude**
- **9.1 Aclaraciones**
  - 9.1.1 Tiempos de respuesta de aclaraciones
  - 9.1.2 Resultado de la aclaración
  - 9.1.3 Trato durante el proceso de aclaración
- **9.2 Fraude / clonación / phishing**
- **9.3 Disputas / devoluciones**

#### 10. **Procesos y requisitos**
- **10.1 Documentación solicitada**
  - 10.1.1 INE / identificaciones (incluye INE del extranjero)
  - 10.1.2 Comprobantes (domicilio, ingresos)
- **10.2 Tiempos de validación de datos**
- **10.3 Procesos burocráticos / vueltas innecesarias**
- **10.4 Diferenciación cliente / no-cliente**
  - 10.4.1 Restricciones a no-clientes (trámites no permitidos)
  - 10.4.2 Trato o tiempos distintos a no-clientes

#### 11. **Programas y beneficios**
- **11.1 Banca preferente / Priority**
- **11.2 Promociones y meses sin intereses**
- **11.3 Programa de puntos / recompensas**

#### 12. **Comunicación y notificaciones**
- **12.1 SMS / correo / push**
- **12.2 Información proactiva al cliente**
- **12.3 Publicidad / spam**

#### 13. **Marca y confianza**
- **13.1 Lealtad / antigüedad como cliente**
- **13.2 Comparación con otros bancos**
- **13.3 Transición y cambios institucionales**
  - 13.3.1 Comparación antes / después de la separación de Citi
  - 13.3.2 Cambios percibidos en servicio o marca

#### 14. **Elogio o queja genérica sin tema específico**
- **14.1 Elogio genérico** ("excelente", "todo bien")
- **14.2 Queja genérica** ("mal servicio" sin contexto)

> Bolsa controlada, no equivalente a "Otros". Sirve para no inflar categorías temáticas con contenido que no las tiene, sin descartar la señal débil de polaridad.

#### 15. **Otros / No clasificable**
- Comentarios fuera de dominio, sarcasmo críptico, balbuceo, texto corrupto.

---

## Resumen volumétrico estimado

- **L1:** 15 categorías raíz (cumple el >8 del KPI con holgura).
- **L2:** 48 subcategorías.
- **L3:** ~90 aspectos neutrales (dentro del rango defendible de 80-100 al arrancar).
- **Metadatos transversales:** 4 atributos extraídos en paralelo.

Las hojas L3 con <100 menciones/mes en producción se colapsan a su L2 padre vía el active learning loop, y los clusters bottom-up que justifiquen apertura nueva se promueven a L3 con evidencia volumétrica.
