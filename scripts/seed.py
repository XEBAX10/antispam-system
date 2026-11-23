"""
Script semilla - AntiSpam System
Pobla Neo4j con datos sinteticos para que todo el equipo pueda probar:

  - 5 operadoras, 20 troncales, 12 prefijos
  - ~4.000 usuarios (personas y empresas) y ~4.500 lineas
  - 6 campanas de fraude (anillos) con 25 lineas SPAM cada una
  - 10 numeros "rotativos" por campana (sin reportes, llaman a las mismas victimas -> RF-22)
  - 50.000+ CDRs (relaciones LLAMO)
  - ~3.000 reportes comunitarios (relaciones REPORTO)

Uso (con Docker corriendo):
    docker compose exec api python -m scripts.seed            # agrega los datos
    docker compose exec api python -m scripts.seed --limpiar  # borra todo y vuelve a poblar
"""
import random
import sys
from datetime import datetime, timedelta, timezone

from app.database import driver
from app.init_db import crear_constraints

random.seed(42)  # misma semilla = mismos datos para todo el equipo

ZONA = timezone(timedelta(hours=-5))  # hora Colombia
HOY = datetime.now(ZONA)
TAMANO_LOTE = 5000

TOTAL_CDRS = 50000
TOTAL_USUARIOS = 4000
LINEAS_POR_CAMPANA = 25
ROTATIVOS_POR_CAMPANA = 10
VICTIMAS_POR_CAMPANA = 300
TOTAL_REPORTES = 3000

CATEGORIAS = ["ROBOCALL_MUDA", "TELEMARKETING_NO_AUTORIZADO", "COBRANZA", "FRAUDE_SUPLANTACION"]
CIUDADES = ["Cali", "Bogota", "Medellin", "Tulua", "Barranquilla", "Cartagena", "Pereira", "Bucaramanga"]
NOMBRES = ["Ana", "Luis", "Maria", "Carlos", "Laura", "Andres", "Sofia", "Juan", "Valentina", "Diego",
           "Camila", "Jorge", "Daniela", "Felipe", "Paula", "Santiago", "Isabella", "Mateo"]
APELLIDOS = ["Gomez", "Rodriguez", "Martinez", "Lopez", "Garcia", "Hernandez", "Ramirez", "Torres",
             "Rivera", "Montoya", "Castro", "Vargas", "Rojas", "Ortiz", "Moreno", "Arias"]
EMPRESAS = ["Banco Andino", "Clinica del Valle", "EPS Salud Total", "Seguros Pacifico", "Universidad Central",
            "Gas Natural Valle", "Energia del Occidente", "Aerolinea Condor", "Tienda Exito Norte", "Notaria 3"]
COMENTARIOS = {
    "ROBOCALL_MUDA": "Llaman y cuelgan sin decir nada",
    "TELEMARKETING_NO_AUTORIZADO": "Ofrecen planes que nunca pedi",
    "COBRANZA": "Llaman a cobrar una deuda que no es mia",
    "FRAUDE_SUPLANTACION": "Dicen ser del banco y piden mis claves",
}


# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------
def ejecutar_por_lotes(session, query, filas, nombre):
    """Inserta una lista grande en lotes usando UNWIND."""
    for i in range(0, len(filas), TAMANO_LOTE):
        lote = filas[i:i + TAMANO_LOTE]
        session.run(query, {"filas": lote})
    print(f"  {nombre}: {len(filas)}")


def fecha_aleatoria(dias_atras=90):
    return HOY - timedelta(days=random.randint(0, dias_atras),
                           hours=random.randint(0, 23),
                           minutes=random.randint(0, 59),
                           seconds=random.randint(0, 59))


numeros_usados = set()


def nuevo_numero(prefijo):
    """Genera un numero E.164 unico dentro del prefijo, ej: 573001234567."""
    while True:
        numero = prefijo + str(random.randint(0, 9999999)).zfill(7)
        if numero not in numeros_usados:
            numeros_usados.add(numero)
            return numero


# ------------------------------------------------------------------
# 1. Catalogo base: operadoras, troncales, prefijos
# ------------------------------------------------------------------
def generar_catalogo():
    operadoras = [
        {"operadora_id": "OP-01", "nombre": "Claro", "pais": "CO", "nivel_confianza": 90.0, "estado": "ACTIVA"},
        {"operadora_id": "OP-02", "nombre": "Movistar", "pais": "CO", "nivel_confianza": 88.0, "estado": "ACTIVA"},
        {"operadora_id": "OP-03", "nombre": "Tigo", "pais": "CO", "nivel_confianza": 85.0, "estado": "ACTIVA"},
        {"operadora_id": "OP-04", "nombre": "WOM", "pais": "CO", "nivel_confianza": 75.0, "estado": "ACTIVA"},
        {"operadora_id": "OP-05", "nombre": "VoIP Express", "pais": "CO", "nivel_confianza": 40.0, "estado": "ACTIVA"},
    ]

    # Prefijos reales de celulares en Colombia (57 + 3xx)
    prefijos = [
        ("57300", "OP-01"), ("57310", "OP-01"), ("57311", "OP-01"),
        ("57315", "OP-02"), ("57316", "OP-02"), ("57318", "OP-02"),
        ("57301", "OP-03"), ("57304", "OP-03"), ("57305", "OP-03"),
        ("57323", "OP-04"), ("57324", "OP-04"),
        ("57333", "OP-05"),
    ]
    lista_prefijos = []
    for codigo, operadora_id in prefijos:
        confianza = 45.0 if operadora_id == "OP-05" else round(random.uniform(70, 95), 1)
        lista_prefijos.append({
            "codigo": codigo, "pais": "CO", "region": random.choice(CIUDADES),
            "nivel_confianza": confianza, "estado": "ACTIVO", "operadora_id": operadora_id,
        })

    # 4 troncales por operadora (las de VoIP Express son de baja confianza)
    troncales = []
    contador = 1
    for op in operadoras:
        for _ in range(4):
            baja = op["operadora_id"] == "OP-05"
            troncales.append({
                "troncal_id": f"TR-{contador:03d}",
                "nombre": f"Troncal {op['nombre']} {contador}",
                "tipo": random.choice(["SIP", "PBX"]),
                "ciudad": random.choice(CIUDADES),
                "pais": "CO",
                "nivel_confianza": round(random.uniform(20, 45), 1) if baja else round(random.uniform(70, 98), 1),
                "politica_trafico": "RESTRINGIDO" if baja else "PERMITIDO",
                "operadora_id": op["operadora_id"],
            })
            contador += 1

    return operadoras, lista_prefijos, troncales


# ------------------------------------------------------------------
# 2. Usuarios y lineas
# ------------------------------------------------------------------
def nueva_linea(numero, prefijo, troncal_id, estado="LEGITIMA", score=0.0, categoria=None):
    fecha = fecha_aleatoria(365)
    return {
        "numero": numero, "estado": estado, "spam_score": score,
        "categoria_predominante": categoria, "pais": "CO",
        "fecha_registro": fecha, "ultima_actualizacion": fecha,
        "prefijo": prefijo, "troncal_id": troncal_id,
    }


def generar_usuarios_y_lineas(prefijos, troncales):
    # Prefijos/troncales "normales" (no VoIP Express)
    prefijos_normales = [p for p in prefijos if p["operadora_id"] != "OP-05"]
    troncales_por_op = {}
    for t in troncales:
        troncales_por_op.setdefault(t["operadora_id"], []).append(t["troncal_id"])

    usuarios, lineas, posee = [], [], []

    for i in range(1, TOTAL_USUARIOS + 1):
        es_empresa = i <= len(EMPRESAS)
        usuario_id = f"USR-{i:05d}"
        usuarios.append({
            "usuario_id": usuario_id,
            "nombre": EMPRESAS[i - 1] if es_empresa else f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
            "correo": f"usuario{i}@correo.com",
            "tipo": "EMPRESA" if es_empresa else "PERSONA",
            "estado": "ACTIVO",
            "fecha_registro": fecha_aleatoria(365),
        })
        # Algunas personas tienen 2 lineas; las empresas tienen 3
        cantidad = 3 if es_empresa else (2 if random.random() < 0.12 else 1)
        for _ in range(cantidad):
            p = random.choice(prefijos_normales)
            numero = nuevo_numero(p["codigo"])
            troncal = random.choice(troncales_por_op[p["operadora_id"]])
            lineas.append(nueva_linea(numero, p["codigo"], troncal))
            posee.append({"usuario_id": usuario_id, "numero": numero})

    return usuarios, lineas, posee


# ------------------------------------------------------------------
# 3. Campanas de fraude (anillos) + numeros rotativos
# ------------------------------------------------------------------
def generar_campanas(prefijos, troncales):
    tipos = [
        ("ROBOCALL", "ROBOCALL_MUDA"),
        ("VISHING", "FRAUDE_SUPLANTACION"),
        ("TELEMARKETING", "TELEMARKETING_NO_AUTORIZADO"),
        ("VISHING", "FRAUDE_SUPLANTACION"),
        ("TELEMARKETING", "COBRANZA"),
        ("ROBOCALL", "ROBOCALL_MUDA"),
    ]
    # Los anillos usan la operadora barata y troncales de baja confianza (SIM Farm)
    troncales_sospechosas = [t["troncal_id"] for t in troncales if t["operadora_id"] == "OP-05"]
    prefijos_anillo = ["57333", "57323", "57324", "57304"]

    campanas, lineas_spam, miembros, rotativos = [], [], [], []
    for n, (tipo_amenaza, categoria) in enumerate(tipos, start=1):
        campana_id = f"CAMP-{n:02d}"
        prefijo = prefijos_anillo[(n - 1) % len(prefijos_anillo)]
        troncal = troncales_sospechosas[(n - 1) % len(troncales_sospechosas)]

        numeros_campana = []
        scores = []
        for _ in range(LINEAS_POR_CAMPANA):
            numero = nuevo_numero(prefijo)
            score = round(random.uniform(75, 99), 1)
            scores.append(score)
            lineas_spam.append(nueva_linea(numero, prefijo, troncal, "FRAUDULENTA", score, categoria))
            miembros.append({"numero": numero, "campana_id": campana_id})
            numeros_campana.append(numero)

        # Rotativos: mismo prefijo y troncal, pero limpios y sin campana (los detecta RF-22)
        numeros_rotativos = []
        for _ in range(ROTATIVOS_POR_CAMPANA):
            numero = nuevo_numero(prefijo)
            rotativos.append(nueva_linea(numero, prefijo, troncal))
            numeros_rotativos.append(numero)

        campanas.append({
            "campana_id": campana_id,
            "nombre": f"Anillo {n} - {tipo_amenaza.title()}",
            "descripcion": f"Lineas coordinadas de {categoria.lower()} saliendo por {troncal}",
            "tipo_amenaza": tipo_amenaza,
            "estado": "ACTIVA",
            "spam_score": round(sum(scores) / len(scores), 1),
            "fecha_deteccion": fecha_aleatoria(60),
            # datos auxiliares (no se guardan en el nodo)
            "_categoria": categoria,
            "_lineas": numeros_campana,
            "_rotativos": numeros_rotativos,
            "_troncal": troncal,
        })

    return campanas, lineas_spam, miembros, rotativos


# ------------------------------------------------------------------
# 4. CDRs (LLAMO) y reportes (REPORTO)
# ------------------------------------------------------------------
def nuevo_cdr(origen, destino, troncal_id, tipo, corta):
    contestada = random.random() < (0.45 if corta else 0.8)
    if corta:
        duracion = random.randint(0, 4) if contestada else 0
    else:
        duracion = random.randint(15, 900) if contestada else 0
    bloqueada = tipo != "NORMAL" and random.random() < 0.15
    if bloqueada:
        duracion, contestada = 0, False
    return {
        "origen": origen, "destino": destino,
        "cdr_id": "",  # se asigna al final
        "troncal_id": troncal_id,
        "fecha_hora": fecha_aleatoria(90),
        "duracion_segundos": duracion,
        "estado_contestacion": "CONTESTADA" if contestada else "NO_CONTESTADA",
        "resultado_validacion": "BLOQUEADO" if bloqueada else "PERMITIDO",
        "tipo_llamada": tipo,
    }


def generar_cdrs_y_reportes(lineas, campanas, posee):
    troncal_de = {l["numero"]: l["troncal_id"] for l in lineas}
    normales = [l["numero"] for l in lineas]
    dueno_de = {p["numero"]: p["usuario_id"] for p in posee}

    cdrs, reportes = [], []

    # Cada campana tiene su propio grupo de victimas
    for c in campanas:
        c["_victimas"] = random.sample(normales, VICTIMAS_POR_CAMPANA)

    # a) Llamadas SPAM (~50% del total): cortas, desde las lineas del anillo
    llamadas_spam = TOTAL_CDRS // 2
    for _ in range(llamadas_spam):
        c = random.choice(campanas)
        tipo = "ROBOCALL" if c["tipo_amenaza"] == "ROBOCALL" else "SPAM"
        cdrs.append(nuevo_cdr(random.choice(c["_lineas"]), random.choice(c["_victimas"]),
                              c["_troncal"], tipo, corta=random.random() < 0.8))

    # b) Rotativos: llaman a las MISMAS victimas del anillo (6% del total)
    llamadas_rotativas = int(TOTAL_CDRS * 0.06)
    for _ in range(llamadas_rotativas):
        c = random.choice(campanas)
        cdrs.append(nuevo_cdr(random.choice(c["_rotativos"]), random.choice(c["_victimas"]),
                              c["_troncal"], "NORMAL", corta=random.random() < 0.7))

    # c) Trafico legitimo entre lineas normales
    while len(cdrs) < TOTAL_CDRS:
        origen, destino = random.sample(normales, 2)
        cdrs.append(nuevo_cdr(origen, destino, troncal_de[origen], "NORMAL", corta=random.random() < 0.05))

    for i, cdr in enumerate(cdrs, start=1):
        cdr["cdr_id"] = f"CDR-{i:06d}"

    # d) Reportes: una victima reporta una linea del anillo que la llamo
    #    (sin duplicados victima-linea, para respetar RF-05)
    pares_usados = set()
    llamadas_spam_lista = [c for c in cdrs if c["tipo_llamada"] != "NORMAL"]
    categoria_de = {}
    for c in campanas:
        for numero in c["_lineas"]:
            categoria_de[numero] = c["_categoria"]

    intentos = 0
    while len(reportes) < TOTAL_REPORTES and intentos < TOTAL_REPORTES * 10:
        intentos += 1
        llamada = random.choice(llamadas_spam_lista)
        par = (llamada["destino"], llamada["origen"])
        if par in pares_usados:
            continue
        pares_usados.add(par)
        # 85% de las veces la categoria coincide con la del anillo
        categoria = categoria_de[llamada["origen"]] if random.random() < 0.85 else random.choice(CATEGORIAS)
        reportes.append({
            "victima": llamada["destino"],
            "reportado": llamada["origen"],
            "reporte_id": f"REP-{len(reportes) + 1:05d}",
            "reportante_usuario_id": dueno_de[llamada["destino"]],
            "categoria": categoria,
            "comentario": COMENTARIOS[categoria],
            "fecha_reporte": llamada["fecha_hora"] + timedelta(minutes=random.randint(1, 120)),
            "estado": "VALIDO",
        })

    return cdrs, reportes


# ------------------------------------------------------------------
# 5. Carga en Neo4j
# ------------------------------------------------------------------
def limpiar(session):
    print("Borrando datos anteriores...")
    session.run("MATCH ()-[r:LLAMO]->() CALL { WITH r DELETE r } IN TRANSACTIONS OF 10000 ROWS")
    session.run("MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS")


def cargar():
    operadoras, prefijos, troncales = generar_catalogo()
    usuarios, lineas, posee = generar_usuarios_y_lineas(prefijos, troncales)
    campanas, lineas_spam, miembros, rotativos = generar_campanas(prefijos, troncales)
    todas_lineas = lineas + lineas_spam + rotativos
    cdrs, reportes = generar_cdrs_y_reportes(lineas, campanas, posee)

    crear_constraints()

    with driver.session() as session:
        if "--limpiar" in sys.argv:
            limpiar(session)
        else:
            hay_cdrs = session.run("MATCH ()-[r:LLAMO]->() RETURN count(r) > 0 AS hay").single()["hay"]
            if hay_cdrs:
                print("Ya hay CDRs cargados. Usa --limpiar para borrar y volver a poblar.")
                return

        print("Cargando datos en Neo4j...")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MERGE (o:Operadora {operadora_id: f.operadora_id})
            SET o += f
        """, operadoras, "Operadoras")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (o:Operadora {operadora_id: f.operadora_id})
            MERGE (p:Prefijo {codigo: f.codigo})
            SET p.pais = f.pais, p.region = f.region,
                p.nivel_confianza = f.nivel_confianza, p.estado = f.estado
            MERGE (p)-[:ASIGNADO_A]->(o)
        """, prefijos, "Prefijos")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (o:Operadora {operadora_id: f.operadora_id})
            MERGE (t:Troncal {troncal_id: f.troncal_id})
            SET t.nombre = f.nombre, t.tipo = f.tipo, t.ciudad = f.ciudad, t.pais = f.pais,
                t.nivel_confianza = f.nivel_confianza, t.politica_trafico = f.politica_trafico
            MERGE (t)-[:OPERADA_POR]->(o)
        """, troncales, "Troncales")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MERGE (u:Usuario {usuario_id: f.usuario_id})
            SET u += f
        """, usuarios, "Usuarios")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (p:Prefijo {codigo: f.prefijo})
            MATCH (t:Troncal {troncal_id: f.troncal_id})
            MERGE (l:Linea {numero: f.numero})
            SET l.estado = f.estado, l.spam_score = f.spam_score,
                l.categoria_predominante = f.categoria_predominante, l.pais = f.pais,
                l.fecha_registro = f.fecha_registro, l.ultima_actualizacion = f.ultima_actualizacion
            MERGE (l)-[:PERTENECE_A_PREFIJO]->(p)
            MERGE (l)-[:SALE_POR]->(t)
        """, todas_lineas, "Lineas")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (u:Usuario {usuario_id: f.usuario_id})
            MATCH (l:Linea {numero: f.numero})
            MERGE (u)-[:POSEE]->(l)
        """, posee, "Relaciones POSEE")

        nodos_campana = [{k: v for k, v in c.items() if not k.startswith("_")} for c in campanas]
        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MERGE (c:Campana {campana_id: f.campana_id})
            SET c += f
        """, nodos_campana, "Campanas")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (l:Linea {numero: f.numero})
            MATCH (c:Campana {campana_id: f.campana_id})
            MERGE (l)-[:MIEMBRO_DE]->(c)
        """, miembros, "Relaciones MIEMBRO_DE")

        # CREATE (no MERGE): puede haber varias llamadas entre el mismo par de lineas
        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (a:Linea {numero: f.origen})
            MATCH (b:Linea {numero: f.destino})
            CREATE (a)-[:LLAMO {
                cdr_id: f.cdr_id, troncal_id: f.troncal_id, fecha_hora: f.fecha_hora,
                duracion_segundos: f.duracion_segundos, estado_contestacion: f.estado_contestacion,
                resultado_validacion: f.resultado_validacion, tipo_llamada: f.tipo_llamada
            }]->(b)
        """, cdrs, "CDRs (LLAMO)")

        ejecutar_por_lotes(session, """
            UNWIND $filas AS f
            MATCH (v:Linea {numero: f.victima})
            MATCH (r:Linea {numero: f.reportado})
            CREATE (v)-[:REPORTO {
                reporte_id: f.reporte_id, reportante_usuario_id: f.reportante_usuario_id,
                categoria: f.categoria, comentario: f.comentario,
                fecha_reporte: f.fecha_reporte, estado: f.estado
            }]->(r)
        """, reportes, "Reportes (REPORTO)")

    print("\nListo. Revisa en http://localhost:7474 con:  MATCH (n) RETURN labels(n), count(*)")


if __name__ == "__main__":
    cargar()
    driver.close()
