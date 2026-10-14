# P1. Entorno y prueba con tres proveedores

## Respuesta de OpenAI

=== OpenAI | 1.84 s | 93 tokens entrada | 54 tokens salida
Clasificación: mixto.
Hola Marta, sentimos la incidencia con la cafetera; la revisamos cuanto antes y te confirmamos por aquí. Sobre el pedido 1004 pendiente, lo revisamos también y te damos una actualización en breve.

## Respuesta de Claude

=== Claude | 2.46 s | 131 tokens entrada | 84 tokens salida
**Clasificación: MIXTO** (incidencia + pedido)

Hola Marta, enviaremos un técnico mañana a primera hora para revisar la cafetera, y confirmaremos la entrega del pedido 1004. Te contactaremos en breve con los horarios exactos.

# P2. Respuestas a las preguntas del ejercicio

## 1. ¿Qué proveedor responde antes? ¿La diferencia se mantiene entre ejecuciones?

En la práctica, OpenAI suele responder antes que Claude y Gemini. Sin embargo, la diferencia no siempre se mantiene exactamente igual entre ejecuciones, porque depende de la carga del servicio y de la respuesta del proveedor en ese momento.

## 2. ¿Por qué no coinciden los tokens de entrada?

Los tokens no coinciden porque cada proveedor usa un tokenizador distinto y, además, cada modelo procesa el prompt con un formato diferente. Aunque el texto sea el mismo, la forma de segmentarlo y contabilizarlo puede variar entre proveedores.

## 3. ¿El correo es mixto? ¿Lo clasifican bien los tres?

Sí, el correo es mixto, porque incluye una incidencia (la cafetera pierde presión) y un pedido pendiente (pedido 1004). Los tres modelos lo clasifican correctamente como mixto.

## 4. ¿Cambia la redacción entre la primera y la segunda ejecución?

Sí, la redacción puede variar ligeramente entre ejecuciones, aunque la intención y la clasificación sean las mismas. Esto ocurre porque la generación de texto es probabilística y cada modelo puede reformular la respuesta de manera distinta.

## Conclusión

La práctica nos ha permitido comprobar que, aunque todos los modelos responden al mismo encargo, cada uno tiene un estilo diferente, una velocidad distinta y una forma propia de tokenizar y redactar la respuesta. Aun así, todos identifican correctamente que el correo es mixto y responden de manera útil y coherente.

# P3. Una interfaz común

Se modificó `llm_client.py` para consultar OpenAI, Claude y Gemini con la misma función: `responder()`. También se añadió la opción de limitar la longitud de las respuestas y calcular su coste aproximado.

Los precios por millón de tokens (entrada/salida) son: OpenAI, 0,75/4,50 USD; Claude, 1/5 USD; Gemini, 0,75/3,75 USD.

**Comprobación:** `python llm_client.py` obtuvo respuestas de los tres modelos. También se comprobó el límite de 20 tokens y el cálculo del coste de Claude. La opción de streaming era opcional y no se implementó.

# P4. Comparativa de proveedores

Se enviaron los mismos cinco correos a cada proveedor y se compararon el coste, el tiempo de respuesta y los tokens generados. La siguiente tabla resume los resultados medios:

| Proveedor | Coste estimado para 2.000 correos | Latencia media | Tokens de salida medios | Calidad media inicial |
|---|---:|---:|---:|---:|
| OpenAI | 0,60 USD | 1,55 s | 57,6 | 4,2/5 |
| Claude | 0,87 USD | 1,72 s | 73,2 | 3,8/5 |
| Gemini | 3,70 USD | 7,16 s | 484,8 | 3,0/5 |

La estimación de coste supone que los cinco correos de la prueba representan el uso mensual. En esta comparativa, OpenAI ofrece el menor coste y la respuesta más rápida, además de la mayor puntuación de calidad inicial. Por estos resultados, sería la opción recomendada para responder 2.000 correos al mes.

Gemini contabilizó muchos más tokens de salida, aunque sus respuestas visibles fueran cortas. Esto puede deberse a que el recuento incluya tokens de razonamiento interno; también influye que cada modelo procese el texto de manera diferente. Las puntuaciones de calidad son propuestas iniciales y deben confirmarse en equipo.

