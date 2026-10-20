"""Sesión 2. Salidas estructuradas: de un correo libre a un objeto validado."""
import os
from typing import Literal

import anthropic
import openai
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()


class Linea(BaseModel):
    producto: str = Field(description="Producto tal y como lo menciona el cliente")
    cantidad: int = Field(description="Unidades o kilos pedidos")


class CorreoClasificado(BaseModel):
    tipo: Literal["pedido", "incidencia", "consulta", "mixto"]
    cliente: str | None = Field(description="Nombre del negocio si aparece; si no, null")
    lineas: list[Linea] = Field(description="Vacía si no hay pedido")
    urgente: bool
    resumen: str = Field(description="Una sola frase en español")


SISTEMA = "Extraes información de correos de clientes de un distribuidor de café para hostelería."


def con_openai(correo: str) -> CorreoClasificado:
    r = openai.OpenAI().responses.parse(
        model=os.environ["OPENAI_MODEL"], instructions=SISTEMA, input=correo,
        text_format=CorreoClasificado,
    )
    return r.output_parsed


def con_claude(correo: str) -> CorreoClasificado:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://openrouter.ai/api").removesuffix("/v1")
    cliente = anthropic.Anthropic(base_url=base_url)
    r = cliente.messages.parse(
        model=os.environ["ANTHROPIC_MODEL"], max_tokens=1024, system=SISTEMA,
        messages=[{"role": "user", "content": correo}],
        output_format=CorreoClasificado,
    )
    return r.parsed_output


def con_gemini(correo: str) -> CorreoClasificado:
    if os.getenv("GEMINI_API_KEY"):  # opcional: API nativa de Gemini
        cliente = genai.Client()  # en una variable: si no, el SDK cierra el cliente antes de usarlo
        r = cliente.interactions.create(
            model=os.environ["GEMINI_MODEL"].removeprefix("google/"),
            system_instruction=SISTEMA, input=correo,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": CorreoClasificado.model_json_schema(),
            },
        )
        return CorreoClasificado.model_validate_json(r.output_text)
    # Por defecto, vía OpenRouter con Chat Completions
    cliente = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                            api_key=os.environ["OPENROUTER_API_KEY"])
    r = cliente.chat.completions.parse(
        model=os.environ["GEMINI_MODEL"],
        messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": correo}],
        response_format=CorreoClasificado,
    )
    return r.choices[0].message.parsed


# Base de datos simulada de clientes registrados
BASE_DATOS_CLIENTES = {
    "Bar La Esquina",
    "Hotel Prado Suites",
    "Lumbre",
    "Cafetería Central",
    "Coffee Break Bistro",
    "Bar El Parque",
    "Taberna Sol",
    "Restaurante El Faro",
    "Bar Manolo",
    "Granja Café",
}


def buscar_cliente(nombre: str) -> bool:
    """Comprueba si el cliente existe en la base de datos."""
    if not nombre:
        return False
    nombre_limpio = nombre.strip().lower()
    return any(nombre_limpio == cliente.strip().lower() for cliente in BASE_DATOS_CLIENTES)


# Conjunto de evaluación ampliado con casos límite y difíciles (17 casos)
CASOS = [
    # 1-6: Casos base iniciales
    ("Necesito 20 kg del blend de hostelería para el viernes. Bar La Esquina.", "pedido"),
    ("El molino hace un ruido raro desde ayer, ¿podéis venir?", "incidencia"),
    ("¿Tenéis café descafeinado de especialidad?", "consulta"),
    ("Mandadme 5 kg de Etiopía y, de paso, la cafetera gotea. Lumbre.", "mixto"),
    ("URGENTE: sin café para mañana, 10 kg de blend. Hotel Prado Suites", "pedido"),
    ("Buenas, ¿la factura de septiembre ya está emitida?", "consulta"),

    # 7: Ironía / sarcasmo con queja por retraso pero solicitud operativa de café
    ("¡Qué maravilla de servicio! Llevamos tres días sin café y los clientes encantados tomando agua caliente. Mandadnos 15 kg de tueste natural ya de una vez. Cafetería Central.", "pedido"),

    # 8: Ironía pura (incidencia con sarcasmo evidente)
    ("Precioso el regalo de hoy: el repartidor ha dejado la caja en el charco de la entrada y está todo el grano empapado. Un aplauso. Bar Manolo.", "incidencia"),

    # 9: Dos clientes mencionados en el mismo correo
    ("Buenas, gestiono dos locales: para Bar El Parque enviad 10 kg de Colombia, pero para Taberna Sol cancelad lo previsto esta semana.", "mixto"),

    # 10: Correo en inglés (cliente internacional)
    ("Good morning, could you please send us 8 kg of espresso blend by Thursday? Thanks, Coffee Break Bistro.", "pedido"),

    # 11: Correo sin nombre de negocio (incidencia anónima)
    ("Hola, el lote de café descafeinado que nos trajisteis ayer sabe a quemado y amargo, creemos que está defectuoso.", "incidencia"),

    # 12: Correo sin nombre de negocio (pedido sin firmar)
    ("Por favor, enviad 6 kg de café arábica 100% antes de las 11:00 de mañana.", "pedido"),

    # 13: Cliente nuevo / NO registrado en base de datos (pedido)
    ("Hola, nos gustaría encargar 25 kg de café en grano para el nuevo restaurante. Bar Sin Registrar.", "pedido"),

    # 14: Cliente nuevo / NO registrado en base de datos (incidencia)
    ("La máquina pierde agua por el portafiltros desde esta mañana, ¿podéis mandar a un técnico? Pizzería Il Forno.", "incidencia"),

    # 15: Consulta comercial de tarifas y volumen
    ("Buenos días, quisiéramos saber el precio por kilo si os pedimos más de 50 kg al mes de café de origen. Granja Café.", "consulta"),

    # 16: Consulta técnica sobre producto y alérgenos
    ("Hola, ¿podríais enviarnos la ficha técnica y de alérgenos del blend arábica? Restaurante El Faro.", "consulta"),

    # 17: Mixto (consulta de precio con pedido condicional de stock)
    ("¿A qué precio tenéis el descafeinado al agua? Si tenéis stock, mandadnos 5 kg junto con el pedido habitual. Bar La Esquina.", "mixto"),
]


if __name__ == "__main__":
    for nombre, extraer in [("OpenAI", con_openai), ("Claude", con_claude), ("Gemini", con_gemini)]:
        aciertos = 0
        print(f"\n--- Evaluando {nombre} ({len(CASOS)} casos) ---")
        for correo, esperado in CASOS:
            resultado = extraer(correo)
            acierto = resultado.tipo == esperado
            aciertos += acierto

            # Log si hay fallo en la clasificación de tipo
            if not acierto:
                print(f"  [FALLO TIPO] Esperado '{esperado}' pero obtuvo '{resultado.tipo}' | Texto: {correo[:50]}...")

            # Validación de negocio 1: el esquema garantiza la forma, no que tenga sentido físico
            if any(l.cantidad <= 0 for l in resultado.lineas):
                print(f"  [AVISO CANTIDAD] Cantidad no válida (<= 0) en: {correo[:40]}...")

            # Validación de negocio 2: comprobar existencia del cliente en la base de datos
            if resultado.cliente and not buscar_cliente(resultado.cliente):
                print(f"  [AVISO CLIENTE NO REGISTRADO] El cliente '{resultado.cliente}' no existe en la base de datos.")

        print(f"{nombre}: {aciertos}/{len(CASOS)} tipos correctos ({aciertos/len(CASOS):.1%})")

