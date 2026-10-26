"""Sesión 2. Function calling con la Messages API de Claude (Anthropic)."""
import json
import os

import anthropic
from dotenv import load_dotenv

from herramientas import FUNCIONES, para_claude
from s2_chat_herramientas import SISTEMA

load_dotenv()

base_url = os.getenv("ANTHROPIC_BASE_URL", "https://openrouter.ai/api").removesuffix("/v1")
cliente = anthropic.Anthropic(base_url=base_url)


def preguntar_claude(pregunta: str, max_vueltas: int = 5) -> str:
    mensajes: list = [{"role": "user", "content": pregunta}]
    for vuelta in range(max_vueltas):
        r = cliente.messages.create(
            model=os.environ["ANTHROPIC_MODEL"],
            max_tokens=1024,
            system=SISTEMA,
            tools=para_claude(),
            messages=mensajes,
        )
        print(f"  [Claude vuelta {vuelta+1}] usage: input_tokens={r.usage.input_tokens}, output_tokens={r.usage.output_tokens}")

        # Agregamos la respuesta completa del asistente al historial
        mensajes.append({"role": "assistant", "content": r.content})

        if r.stop_reason != "tool_use":
            # Sin llamadas a herramientas pendientes: extraemos el texto de respuesta
            textos = [block.text for block in r.content if getattr(block, "type", None) == "text"]
            return "\n".join(textos)

        # Procesamos las llamadas a herramientas solicitadas por el modelo
        respuestas_herramientas = []
        for block in r.content:
            if getattr(block, "type", None) == "tool_use":
                args = block.input
                resultado = FUNCIONES[block.name](**args)
                print(f"  -> {block.name}({args}) = {str(resultado)[:80]}")
                respuestas_herramientas.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        mensajes.append({"role": "user", "content": respuestas_herramientas})

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
        resp = preguntar_claude(p)
        print(f"Respuesta:\n{resp}")

