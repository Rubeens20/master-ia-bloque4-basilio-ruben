# P4. Análisis de la comparativa

Se compararon los tres modelos con los mismos cinco correos. Las puntuaciones de calidad son una propuesta inicial; el equipo debe revisarlas y cambiarlas si está de acuerdo con otras valoraciones.

| Proveedor | Coste estimado para 2.000 correos | Latencia media | Tokens de salida medios | Calidad media propuesta |
|---|---:|---:|---:|---:|
| OpenAI | 0,60 USD | 1,55 s | 57,6 | 4,2/5 |
| Claude | 0,87 USD | 1,72 s | 73,2 | 3,8/5 |
| Gemini | 3,70 USD | 7,16 s | 484,8 | 3,0/5 |

El coste mensual es una estimación: se calcula suponiendo que los cinco correos de la prueba representan el uso y se repiten hasta llegar a 2.000. El coste real puede cambiar según los correos y las tarifas vigentes.

Gemini registra muchos más tokens de salida aunque sus respuestas visibles sean cortas. Una posible explicación es que el modelo también contabilice tokens usados en su razonamiento interno. Además, cada modelo puede tokenizar el texto de manera diferente.

Con los resultados de esta prueba elegiríamos OpenAI para responder 2.000 correos al mes: tuvo el menor coste y la menor latencia, y recibió la mayor puntuación media propuesta. La conclusión es provisional porque se basa en solo cinco correos y las puntuaciones de calidad deben acordarse en equipo.
