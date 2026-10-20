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

