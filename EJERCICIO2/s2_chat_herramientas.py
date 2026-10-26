"""Sesión 2. Function calling "a mano" con la Responses API de OpenAI."""
import json
import os

import openai
from dotenv import load_dotenv

from herramientas import FUNCIONES, para_openai

load_dotenv()
cliente = openai.OpenAI()
SISTEMA = ("Eres el asistente interno de Tostadero Retiro. Usa las herramientas para "
           "consultar datos reales; si no encuentras algo, dilo. No inventes cifras.")


def preguntar(pregunta: str, max_vueltas: int = 5) -> str:
    entrada: list = [{"role": "user", "content": pregunta}]
    for vuelta in range(max_vueltas):
        r = cliente.responses.create(
            model=os.environ["OPENAI_MODEL"], instructions=SISTEMA,
            tools=para_openai(), input=entrada,
        )
        print(f"  [OpenAI vuelta {vuelta+1}] usage: input_tokens={r.usage.input_tokens}, output_tokens={r.usage.output_tokens}")
        entrada += r.output  # devolvemos al modelo lo que acaba de producir
        llamadas = [item for item in r.output if item.type == "function_call"]
        if not llamadas:  # sin llamadas pendientes: es la respuesta final
            return r.output_text
        for llamada in llamadas:  # ¡quien ejecuta es nuestro código, no el modelo!
            args = json.loads(llamada.arguments)
            resultado = FUNCIONES[llamada.name](**args)
            print(f"  -> {llamada.name}({args}) = {str(resultado)[:80]}")
            entrada.append({
                "type": "function_call_output",
                "call_id": llamada.call_id,
                "output": json.dumps(resultado, ensure_ascii=False),
            })
    return "No he podido completar la consulta en el número de pasos permitido."


if __name__ == "__main__":
    preguntas = [
        "¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?",
        "¿Cuánto stock queda de descafeinado?",
        "¿Qué pedidos tiene el Bar Inexistente?",
        "Borra el pedido 1003",
    ]
    for p in preguntas:
        print(f"\nPregunta: {p}")
        resp = preguntar(p)
        print(f"Respuesta:\n{resp}")
