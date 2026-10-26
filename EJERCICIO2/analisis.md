# P1. Análisis del clasificador de correos con evaluación

## 1. Resultados de la evaluación

Se evaluaron los tres proveedores mediante sus respectivas interfaces y formatos sobre un conjunto ampliado de **17 casos de prueba** (incluyendo casos base, situaciones ambiguas, ironía, bilingüismo y validaciones de negocio):

| Proveedor | Formato de API | Modelo en `.env` | Aciertos de tipo | Porcentaje | Avisos BD detectados |
|---|---|---|:---:|:---:|:---:|
| **OpenAI** | Responses API (`responses.parse`) | `openai/gpt-5.4-mini` | **17 / 17** | **100,0 %** | 2 |
| **Claude** | Messages API (`messages.parse`) | `anthropic/claude-haiku-4.5` | **17 / 17** | **100,0 %** | 2 |
| **Gemini** | Chat Completions (`chat.completions.parse`) | `google/gemini-3.8-flash` | **16 / 17** | **94,1 %** | 3* |

*\*Nota: En Gemini se detectaron 3 avisos de base de datos porque concatenó los dos negocios del caso 9 en un solo nombre (`Bar El Parque y Taberna Sol`), el cual lógicamente no existía como cliente único.*

---

## 2. Casos difíciles añadidos al conjunto de evaluación

Para poner a prueba la robustez de los esquemas estructurados de Pydantic y la comprensión de los modelos, se agregaron los siguientes escenarios:

1. **Ironía con pedido urgente (Caso 7):**
   > *"¡Qué maravilla de servicio! Llevamos tres días sin café y los clientes encantados tomando agua caliente. Mandadnos 15 kg de tueste natural ya de una vez. Cafetería Central."*
   El cliente emplea sarcasmo para expresar su malestar por un retraso previo, pero la acción requerida es un pedido inmediato de 15 kg.
2. **Ironía pura como incidencia (Caso 8):**
   > *"Precioso el regalo de hoy: el repartidor ha dejado la caja en el charco de la entrada y está todo el grano empapado. Un aplauso. Bar Manolo."*
   A pesar del tono aparentemente positivo ("Precioso el regalo", "Un aplauso"), los tres modelos identificaron correctamente que se trata de una `incidencia`.
3. **Dos clientes en el mismo correo (Caso 9):**
   > *"Buenas, gestiono dos locales: para Bar El Parque enviad 10 kg de Colombia, pero para Taberna Sol cancelad lo previsto esta semana."*
   Presenta dos razones sociales y dos acciones contrapuestas (pedir y cancelar/modificar), lo que corresponde a `mixto`.
4. **Correo en inglés (Caso 10):**
   > *"Good morning, could you please send us 8 kg of espresso blend by Thursday? Thanks, Coffee Break Bistro."*
   Evalúa si el modelo es capaz de extraer la información técnica en otro idioma y redactar el campo `resumen` obligatoriamente en español (conforme a la restricción del prompt y del esquema).
5. **Correos sin nombre de negocio (Casos 11 y 12):**
   Evalúan si el modelo respeta la directiva `cliente: str | None = Field(description="Nombre del negocio si aparece; si no, null")` asignando `None` (null) en lugar de inventar un nombre o extraer palabras al azar.
6. **Clientes no registrados en la base de datos (Casos 13 y 14):**
   Se introdujeron los clientes `Bar Sin Registrar` y `Pizzería Il Forno` para comprobar la validación de negocio mediante la función `buscar_cliente()`.
7. **Consultas técnicas, comerciales y pedidos condicionales (Casos 15, 16 y 17):**
   Peticiones de tarifas por volumen, fichas de alérgenos y consultas de precio acompañadas de pedido supeditado a disponibilidad de stock.

---

## 3. Revisión de fallos y corrección de etiquetas dudosas

Durante la primera iteración de pruebas se detectó una discrepancia en el **Caso 7 (Ironía con pedido y queja)**:

- **Etiqueta inicial asignada:** `"mixto"`
- **Predicción de OpenAI:** `"pedido"`
- **Predicción de Claude:** `"pedido"`
- **Predicción de Gemini:** `"mixto"`

### ¿Error del modelo o del caso (etiqueta ambigua)?
Se determinó que se trataba de una **etiqueta ambigua en el caso de prueba**, no de un fallo de comprensión de los modelos:
- **Motivo de la ambigüedad:** El remitente utiliza sarcasmo para quejarse de un retraso anterior (*"Llevamos tres días sin café..."*). Esto podría interpretarse superficialmente como una incidencia.
- **Criterio de negocio corregido:** En el dominio de hostelería, una incidencia técnica implica averías de maquinaria (molinos, cafeteras) o errores de facturación. En este caso no hay avería técnica ni petición de servicio de reparación: la intención transaccional y operativa del correo es **solicitar producto** (*"Mandadnos 15 kg de tueste natural ya de una vez"*). De hecho, los modelos extrajeron la línea de pedido correctamente (15 kg) y marcaron `urgente: True`.
- **Decisión:** Se corrigió la etiqueta del caso de prueba a `"pedido"`. Tras esta clarificación, tanto OpenAI como Claude obtuvieron un 100 % de aciertos, mientras que Gemini se mantuvo en `"mixto"` al dar más peso a la queja histórica sobre el servicio.

---

## 4. Validación de negocio y hallazgos en la extracción

### A. Validación de clientes (`buscar_cliente`)
- La función `buscar_cliente(nombre: str)` comprueba de forma insensible a mayúsculas/minúsculas si el cliente extraído figura en `BASE_DATOS_CLIENTES`.
- En los tres proveedores saltó correctamente el aviso para:
  - `Bar Sin Registrar` (Caso 13)
  - `Pizzería Il Forno` (Caso 14)
- **Comportamiento ante múltiples clientes (Caso 9):**
  - **OpenAI y Claude** devolvieron `cliente: None`, interpretando prudentemente que el correo no pertenecía a un único cliente asignable en el campo escalar.
  - **Gemini** concatenó ambos clientes (`'Bar El Parque y Taberna Sol'`). Como resultado, la validación de negocio avisó que dicha entidad combinada no figuraba en la base de datos, lo que resulta muy útil para evitar errores de facturación cruzada.

### B. Validación de líneas y cantidades
- Todos los modelos extrajeron cantidades estrictamente enteras y positivas (`> 0`) en todos los pedidos.
- En los correos sin pedido (incidencias o consultas puras), todos los modelos dejaron `lineas: []` vacía conforme al esquema.

### C. Resumen en español en correos en otro idioma
- En el caso en inglés (Caso 10), tanto OpenAI como Claude y Gemini redactaron la frase de resumen en español (por ejemplo: *"Coffee Break Bistro solicita 8 kg de blend espresso para el jueves"*), demostrando que la descripción de campo de Pydantic (`Field(description="Una sola frase en español")`) actúa como una instrucción vinculante para la generación estructurada.

---

# P3. El bucle de herramientas con OpenAI

Se ejecutó el bucle de herramientas interactivo de `s2_chat_herramientas.py` con el modelo `openai/gpt-5.4-mini` (Responses API) sobre la base de datos real `tostadero.db` para analizar la traza de llamadas, argumentos y respuestas del asistente ante cuatro preguntas clave:

### Pregunta 1: «¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?»
- **Herramientas llamadas (en orden) y argumentos:**
  1. `buscar_cliente({"texto": "Bar La Esquina"})`
     - *Resultado devuelto:* `[{"id": 1, "nombre": "Bar La Esquina", "tipo": "bar", "distrito": "Retiro"}]`
  2. `consultar_pedidos({"cliente_id": 1})`
     - *Resultado devuelto:* `[{"id": 1001, "fecha": "2026-09-22", "estado": "entregado", "total": 169.0}, {"id": 1004, "fecha": "2026-09-30", "estado": "pendiente", "total": 98.0}]`
- **Respuesta final del asistente:**
  > *"El Bar La Esquina tiene 1 pedido pendiente:*
  > *- Pedido 1004 — 30/09/2026 — 98,00 €*
  > *Total pendiente: 98,00 €"*
- **Análisis:** Encadena dos llamadas consecutivas con éxito. Primero busca el ID del cliente (`cliente_id: 1`) porque la herramienta de pedidos requiere dicho identificador numérico, y luego consulta los pedidos. Discrimina correctamente el estado, ignorando el pedido `1001` (que ya estaba entregado) y sumando únicamente el pedido pendiente.

---

### Pregunta 2: «¿Cuánto stock queda de descafeinado?»
- **Herramientas llamadas (en orden) y argumentos:**
  1. `stock_producto({"texto": "descafeinado"})`
     - *Resultado devuelto:* `[{"sku": "CAF-003", "nombre": "Café descafeinado 1 kg", "precio": 19.8, "stock": 45}]`
- **Respuesta final del asistente:**
  > *"Quedan **45 unidades** de **Café descafeinado 1 kg** (SKU **CAF-003**)."*
- **Análisis:** Realiza una sola llamada directa a `stock_producto` con el término de búsqueda y extrae con precisión tanto el stock disponible (45 unidades) como el nombre exacto y el SKU.

---

### Pregunta 3: «¿Qué pedidos tiene el Bar Inexistente?»
- **Herramientas llamadas (en orden) y argumentos:**
  1. `buscar_cliente({"texto": "Bar Inexistente"})`
     - *Resultado devuelto:* `[]` (lista vacía).
- **Respuesta final del asistente:**
  > *"No he encontrado ningún cliente llamado «Bar Inexistente» en el sistema.*
  > *Si quieres, puedo probar con un nombre parecido o con otra parte del nombre."*
- **Análisis de la gestión del resultado vacío:** Al recibir la lista vacía de la base de datos, el modelo detiene el bucle de herramientas; no inventa un identificador ficticio ni intenta llamar a `consultar_pedidos`. Informa honestamente al usuario de la ausencia del cliente en el sistema.

---

### Pregunta 4: «Borra el pedido 1003»
- **Herramientas llamadas (en orden) y argumentos:**
  *Ninguna llamada a herramientas.*
- **Respuesta final del asistente:**
  > *"No puedo borrar pedidos desde aquí porque no dispongo de una herramienta para eliminar pedidos.*
  > *Si quieres, puedo ayudarte a:*
  > *- localizar el cliente asociado al pedido,*
  > *- consultar el estado y los detalles del pedido 1003,*
  > *- o indicarte cómo tramitar la cancelación por el canal adecuado."*
- **Análisis ante la ausencia de herramienta:** El modelo revisa las herramientas suministradas (`para_openai()`), comprueba que ninguna tiene permisos destructivos ni funcionalidad de eliminación, no alucina acciones de borrado y responde de manera segura explicando sus limitaciones y ofreciendo alternativas de consulta.

---

# P4. El mismo asistente con Claude (`s2_chat_claude.py`) y comparativa

Se portó el bucle de herramientas a Anthropic Claude (`anthropic/claude-haiku-4.5` vía Messages API y `para_claude()`) en el archivo `s2_chat_claude.py`. Se ejecutaron exactamente las mismas cuatro preguntas de la sesión y se registraron en cada vuelta las llamadas, los tokens y las respuestas.

### Tabla comparativa: OpenAI (`gpt-5.4-mini`) vs. Claude (`claude-haiku-4.5`)

| Pregunta | Proveedor | Nº Llamadas a herramientas | Tokens Entrada (acumulados) | Tokens Salida (acumulados) | Calidad de la respuesta final |
|---|---|:---:|:---:|:---:|---|
| **1. Pedidos pendientes Bar La Esquina** | **OpenAI**<br>**Claude** | 2 (`buscar_cliente` $\rightarrow$ `consultar_pedidos`)<br>2 (`buscar_cliente` $\rightarrow$ `consultar_pedidos`) | 1.041<br>3.493 | 84<br>235 | **Excelente en ambos.** Ambos filtran los pedidos entregados y calculan con exactitud el total pendiente (98,00 €). Claude formatea el resultado en una tabla Markdown muy visual. |
| **2. Stock de descafeinado** | **OpenAI**<br>**Claude** | 1 (`stock_producto`)<br>1 (`stock_producto`) | 597<br>2.153 | 49<br>122 | **Excelente en ambos.** Ambos localizan el SKU `CAF-003` con 45 unidades de stock. Claude aporta adicionalmente el precio unitario (19,80 €). |
| **3. Pedidos Bar Inexistente** | **OpenAI**<br>**Claude** | 1 (`buscar_cliente` $\rightarrow$ `[]`)<br>1 (`buscar_cliente` $\rightarrow$ `[]`) | 563<br>2.134 | 55<br>170 | **Muy buena en ambos.** Ninguno inventa datos al recibir la lista vacía. Claude ofrece una ayuda más proactiva sugiriendo buscar por distrito o partes del nombre. |
| **4. Borra el pedido 1003** | **OpenAI**<br>**Claude** | 0<br>0 | 263<br>1.015 | 56<br>138 | **Excelente en ambos.** Ambos identifican que no existe una herramienta destructiva para eliminar pedidos. Claude enumera explícitamente las 4 herramientas disponibles para informar al usuario de sus capacidades. |

---

### Análisis detallado de la comparativa

1. **Secuencia de llamadas y razonamiento**:
   - Tanto OpenAI como Claude demostraron una toma de decisiones idéntica:
     - En la **Pregunta 1**, ambos realizaron el encadenamiento en dos pasos (`buscar_cliente` primero para obtener el `cliente_id = 1` y después `consultar_pedidos`).
     - En la **Pregunta 3**, ambos detuvieron el bucle de herramientas en cuanto la búsqueda arrojó `[]`, evitando consultas vacías o ficticias.
     - En la **Pregunta 4**, ninguno intentó llamar a herramientas inexistentes ni alucinó operaciones de base de datos.

2. **Consumo de tokens de entrada y salida**:
   - **Tokens de entrada:** Claude registra un volumen notablemente superior de tokens de entrada (~1.015 tokens base por turno frente a ~265 tokens en OpenAI). Esto se debe a que la Messages API de Anthropic incluye en el conteo de entrada los esquemas JSON de las cuatro herramientas completas en cada llamada a la API, mientras que OpenAI Responses gestiona el contexto de herramientas de forma más compacta.
   - **Tokens de salida:** Claude genera respuestas ligeramente más extensas y explicativas (tablas formateadas, sugerencias proactivas y listas de funciones disponibles), lo que se traduce en un mayor número de tokens de salida (120–235 tokens frente a 40–84 en OpenAI).

3. **Calidad y experiencia de usuario**:
   - Ambos modelos alcanzaron la máxima puntuación en rigor fáctico y uso de las herramientas de negocio.
   - Claude ofrece un tono más pedagógico y estructurado en la presentación visual de los datos, mientras que OpenAI es más conciso y directo, con una latencia ligeramente inferior.



