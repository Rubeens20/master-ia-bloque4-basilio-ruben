"""Sesión 3. P4: Enrutador: workflow delante del agente."""
import os
import sys
from dotenv import load_dotenv

from llm_client import LLM
from s2_extraer_correo import con_openai, CASOS
from s3_agente import Agente, SISTEMA, Herramienta
from herramientas import DEFINICIONES, FUNCIONES

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

SISTEMA_CONSULTAS = """Eres el asistente de atención al cliente de Tostadero Retiro S.L.
Tu labor es responder consultas generales sobre café, disponibilidad habitual de productos,
servicios a hostelería, horarios y tarifas de manera amable, clara y concisa.
Instrucciones:
1. Responde brevemente (máximo 2 párrafos) y con tono cordial.
2. Si preguntan por descafeinado u orígenes, confirma que disponemos de cafés de especialidad.
3. Si la consulta requiere datos privados, incidencias o pedidos ya tramitados, remite al cliente
   a que proporcione sus datos para que el equipo técnico o comercial le atienda."""

# Construcción del agente reutilizando herramientas de negocio
herramientas = [
    Herramienta(d["name"], d["description"], d["parameters"], FUNCIONES[d["name"]],
                requiere_aprobacion=(d["name"] == "crear_incidencia"))
    for d in DEFINICIONES
]
agente = Agente(SISTEMA, herramientas, auto_aprobar=True)


def atender(correo: str, modelo_barato: str = "gemini") -> tuple[str, str, dict]:
    """Enruta el correo según su clasificación:
    - 'consulta' -> camino barato y directo (sin herramientas).
    - otros ('pedido', 'incidencia', 'mixto') -> camino agéntico complejo con herramientas."""
    clasificacion = con_openai(correo)

    if clasificacion.tipo == "consulta":
        if modelo_barato == "gemini":
            resp = LLM("gemini").responder(SISTEMA_CONSULTAS, correo)
        else:
            resp = LLM("openai", modelo=modelo_barato).responder(SISTEMA_CONSULTAS, correo)
        uso = {
            "camino": f"barato ({modelo_barato})",
            "llamadas": 1,
            "tokens_entrada": resp.tokens_entrada,
            "tokens_salida": resp.tokens_salida,
        }
        return resp.texto, clasificacion.tipo, uso

    texto = agente.ejecutar(correo)
    uso = {
        "camino": "agente (claude)",
        "llamadas": agente.ultimo_uso["llamadas"],
        "tokens_entrada": agente.ultimo_uso["tokens_entrada"],
        "tokens_salida": agente.ultimo_uso["tokens_salida"],
    }
    return texto, clasificacion.tipo, uso


def evaluar_ahorro(casos_muestra: list[tuple[str, str]] | None = None):
    casos = casos_muestra or CASOS
    print(f"\n=======================================================")
    print(f"EVALUACIÓN DE AHORRO CON ENRUTADOR ({len(casos)} casos)")
    print(f"=======================================================\n")

    # Métrica 1: Camino 100% Agente (sin enrutador)
    total_agente = {"llamadas": 0, "in": 0, "out": 0}
    # Métrica 2: Enrutador con Gemini en camino barato
    total_enrutador_gemini = {"llamadas": 0, "in": 0, "out": 0, "consultas": 0, "agente": 0}
    # Métrica 3: Enrutador con GPT-5.4-nano en camino barato
    total_enrutador_nano = {"llamadas": 0, "in": 0, "out": 0}

    print(f"{'#':<3} | {'Tipo':<10} | {'Llam. Agente':<13} | {'Tok Agente':<12} | {'Tok Enrut. (Gemini)':<20} | {'Tok Enrut. (Nano)'}")
    print("-" * 85)

    for i, (correo, _) in enumerate(casos, 1):
        # 1. Agente directo
        agente.ejecutar(correo)
        tok_agente_in = agente.ultimo_uso["tokens_entrada"]
        tok_agente_out = agente.ultimo_uso["tokens_salida"]
        llam_agente = agente.ultimo_uso["llamadas"]
        total_agente["llamadas"] += llam_agente
        total_agente["in"] += tok_agente_in
        total_agente["out"] += tok_agente_out

        # 2. Enrutador
        clasificacion = con_openai(correo)
        tipo = clasificacion.tipo

        if tipo == "consulta":
            total_enrutador_gemini["consultas"] += 1

            # Con Gemini
            r_gemini = LLM("gemini").responder(SISTEMA_CONSULTAS, correo)
            tok_gemini_in = r_gemini.tokens_entrada
            tok_gemini_out = r_gemini.tokens_salida
            total_enrutador_gemini["llamadas"] += 1
            total_enrutador_gemini["in"] += tok_gemini_in
            total_enrutador_gemini["out"] += tok_gemini_out

            # Con GPT-5.4-nano
            r_nano = LLM("openai", modelo="openai/gpt-5.4-nano").responder(SISTEMA_CONSULTAS, correo)
            tok_nano_in = r_nano.tokens_entrada
            tok_nano_out = r_nano.tokens_salida
            total_enrutador_nano["llamadas"] += 1
            total_enrutador_nano["in"] += tok_nano_in
            total_enrutador_nano["out"] += tok_nano_out

            print(f"{i:<3} | {tipo:<10} | {llam_agente:<13} | {tok_agente_in + tok_agente_out:<12} | {tok_gemini_in + tok_gemini_out:<20} | {tok_nano_in + tok_nano_out}")
        else:
            total_enrutador_gemini["agente"] += 1
            # Reutiliza el coste del agente ya medido
            total_enrutador_gemini["llamadas"] += llam_agente
            total_enrutador_gemini["in"] += tok_agente_in
            total_enrutador_gemini["out"] += tok_agente_out

            total_enrutador_nano["llamadas"] += llam_agente
            total_enrutador_nano["in"] += tok_agente_in
            total_enrutador_nano["out"] += tok_agente_out

            print(f"{i:<3} | {tipo:<10} | {llam_agente:<13} | {tok_agente_in + tok_agente_out:<12} | {tok_agente_in + tok_agente_out:<20} | {tok_agente_in + tok_agente_out}")

    print("-" * 85)
    print("\nRESUMEN COMPARATIVO:")
    print(f"1. SOLO AGENTE (Sin enrutador):")
    print(f"   - Total llamadas LLM: {total_agente['llamadas']}")
    print(f"   - Tokens entrada:     {total_agente['in']:,}")
    print(f"   - Tokens salida:      {total_agente['out']:,}")
    print(f"   - Total tokens:       {total_agente['in'] + total_agente['out']:,}")

    print(f"\n2. ENRUTADOR + GEMINI (google/gemini-3.8-flash):")
    print(f"   - Consultas desviadas al camino barato: {total_enrutador_gemini['consultas']}")
    print(f"   - Casos derivados al agente:           {total_enrutador_gemini['agente']}")
    print(f"   - Total llamadas LLM: {total_enrutador_gemini['llamadas']}")
    print(f"   - Tokens entrada:     {total_enrutador_gemini['in']:,}")
    print(f"   - Tokens salida:      {total_enrutador_gemini['out']:,}")
    print(f"   - Total tokens:       {total_enrutador_gemini['in'] + total_enrutador_gemini['out']:,}")

    print(f"\n3. ENRUTADOR + NANO (openai/gpt-5.4-nano):")
    print(f"   - Total llamadas LLM: {total_enrutador_nano['llamadas']}")
    print(f"   - Tokens entrada:     {total_enrutador_nano['in']:,}")
    print(f"   - Tokens salida:      {total_enrutador_nano['out']:,}")
    print(f"   - Total tokens:       {total_enrutador_nano['in'] + total_enrutador_nano['out']:,}")


if __name__ == "__main__":
    correo_prueba = "¿Tenéis café descafeinado de especialidad?"
    print(f"\n--- Probando atender() con una consulta: '{correo_prueba}' ---")
    texto, tipo, uso = atender(correo_prueba, modelo_barato="gemini")
    print(f"Tipo clasificado: {tipo}")
    print(f"Camino y modelo: {uso['camino']} (Llamadas: {uso['llamadas']}, In: {uso['tokens_entrada']}, Out: {uso['tokens_salida']})")
    print(f"Respuesta:\n{texto}\n")

    # Evaluamos con una muestra representativa de casos de la sesión 2
    muestra = [
        ("¿Tenéis café descafeinado de especialidad?", "consulta"),
        ("Buenas, ¿la factura de septiembre ya está emitida?", "consulta"),
        ("Buenos días, quisiéramos saber el precio por kilo si os pedimos más de 50 kg al mes de café de origen. Granja Café.", "consulta"),
        ("Necesito 20 kg del blend de hostelería para el viernes. Bar La Esquina.", "pedido"),
        ("El molino hace un ruido raro desde ayer, ¿podéis venir?", "incidencia"),
        ("Mandadme 5 kg de Etiopía y, de paso, la cafetera gotea. Lumbre.", "mixto"),
    ]
    evaluar_ahorro(muestra)

