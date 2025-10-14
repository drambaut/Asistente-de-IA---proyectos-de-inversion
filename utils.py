
# utils.py
# ============================================================
# Utilidades para el chatbot IDEC/IA:
# - LLM helper (Azure OpenAI)
# - Generación de DOCX con secciones ordenadas y títulos (sin mostrar IDs)
# - Validadores + Parsers de plantillas Excel
# - Guardado y carga de árboles JSON (UTF-8 con BOM)
# - Conversation flow (para importar desde app.py)
# ============================================================

from __future__ import annotations
import os
import re
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_BREAK
from openpyxl import load_workbook



SYSTEM_PRIMER = """
Contexto fijo:
- País por defecto: Colombia. Cuando se hable de departamentos/municipios/localidades, se asume Colombia.
- DNP = Departamento Nacional de Planeación (Colombia).
- IDEC = Infraestructura de Datos del Estado Colombiano.
- Usa terminología y normatividad de Colombia cuando aplique.
- Si te dan porcentajes o proporciones sin base absoluta, explica el cálculo y estima usando datos oficiales si están disponibles.
- No muestres códigos internos de árbol (C1, CI1, O1, MI1) en el texto final.
"""

# -------------------------- LLM helper --------------------------
def ask_markdown_azure(
    messages: List[Dict[str, str]],
    *,
    client,
    model_name: Optional[str] = None,
    max_tokens: int = 1800,
    temperature: float = 0.4,
    max_rounds: int = 3,
    use_primer = True
) -> str:
    """Envía mensajes a Azure OpenAI y concatena si se corta por longitud."""
    full_text, rounds = "", 0
    _messages = list(messages)
    if use_primer:
        sys = {"role": "system", "content": SYSTEM_PRIMER + "\nResponde en Markdown válido."}
        _messages = [sys] + _messages
    if model_name is None:
        model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    while rounds < max_rounds:
        rounds += 1
        resp = client.chat.completions.create(
            model=model_name, messages=_messages, temperature=temperature, max_tokens=max_tokens
        )
        choice = resp.choices[0]
        chunk = (choice.message.content or "").strip()
        full_text += chunk
        finish = getattr(choice, "finish_reason", None)
        if finish not in ("length", "content_filter"):
            break
        _messages += [
            {"role": "assistant", "content": chunk},
            {"role": "user", "content": "Por favor continúa exactamente donde te quedaste."},
        ]
    return full_text


# -------------------------- DOCX helpers --------------------------
def _add_rich_text(paragraph, text: str) -> None:
    """Aplica **negrita**, *itálica* y `monoespaciado` simple dentro de un párrafo."""
    token_re = re.compile(r'(\*\*.+?\*\*|\*.+?\*|`.+?`)')
    parts = token_re.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2]); run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1]); run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1]); run.font.name = "Courier New"; run.font.size = Pt(10)
        else:
            paragraph.add_run(part)


def _add_markdown_line(doc, line: str) -> None:
    """Convierte una línea de Markdown muy simple a estructuras de docx.
    Soporta #, ##, ###, ####; listas numeradas y con viñetas.
    """
    s = line.strip()
    if not s:
        return
    if s == '---':
        p = doc.add_paragraph(); p.add_run().add_break(WD_BREAK.LINE); return
    if s.startswith('#### '):
        doc.add_heading(s[5:], level=4); return
    if s.startswith('### '):
        doc.add_heading(s[4:], level=3); return
    if s.startswith('## '):
        doc.add_heading(s[3:], level=2); return
    if s.startswith('# '):
        doc.add_heading(s[2:], level=1); return
    if re.match(r'^\d+\.\s', s):
        p = doc.add_paragraph(style='List Number'); _add_rich_text(p, re.sub(r'^\d+\.\s', '', s, 1)); return
    if s.startswith('- ') or s.startswith('* '):
        p = doc.add_paragraph(style='List Bullet'); _add_rich_text(p, s[2:]); return
    p = doc.add_paragraph(); _add_rich_text(p, s)


def _filtered_responses_for_report(responses: dict) -> dict:
    """Filtra claves internas (e.g., uploads) para el reporte."""
    return {k: v for k, v in responses.items() if not k.startswith('upload_')}


# -------------------------- Árbol -> Outline para prompt --------------------------
def causas_tree_to_outline(tree: Dict[str, Any]) -> str:
    """Devuelve un outline sin códigos (C1, CI1, etc.)."""
    if not tree or not tree.get("items"): 
        return "(sin causas)"
    lines = ["Marco del problema: Causas y efectos"]
    for c in tree["items"]:
        cdesc = (c.get("descripcion") or "").strip()
        edesc = ((c.get("efecto_directo") or {}).get("descripcion") or "").strip()
        lines.append(f"Causa: {cdesc}")
        if edesc:
            lines.append(f"Efecto directo: {edesc}")
        cis = c.get("causas_indirectas", [])
        if cis:
            lines.append("Causas indirectas:")
            for ci in cis:
                cidesc = (ci.get("descripcion") or "").strip()
                lines.append(f"  a) {cidesc}")
                for ei in ci.get("efectos_indirectos", []):
                    lines.append(f"     * Efecto indirecto: {(ei.get('descripcion') or '').strip()}")
    return "\n".join(lines)


def objetivos_tree_to_outline(tree: Dict[str, Any]) -> str:
    """Devuelve un outline sin códigos (O1, MI1, etc.)."""
    if not tree or not tree.get("items"): 
        return "(sin objetivos)"
    lines = ["Marco de objetivos: Medios y fines"]
    for o in tree["items"]:
        odesc = (o.get("descripcion") or "").strip()
        md = ((o.get("medio_directo") or {}).get("descripcion") or "").strip()
        fd = ((o.get("fin_directo") or {}).get("descripcion") or "").strip()
        lines.append(f"Objetivo: {odesc}")
        if md: lines.append(f"Medio directo: {md}")
        if fd: lines.append(f"Fin directo: {fd}")
        mis = o.get("medios_indirectos", [])
        if mis:
            lines.append("Medios indirectos y fines:")
            for mi in mis:
                midesc = (mi.get("descripcion") or "").strip()
                lines.append(f"  a) {midesc}")
                for fi in mi.get("fines_indirectos", []):
                    lines.append(f"     * Fin indirecto: {(fi.get('descripcion') or '').strip()}")
    return "\n".join(lines)


# -------------------------- Carga/guardado JSON --------------------------
def load_tree_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def save_tree_json(tree: Dict[str, Any], out_dir: str, base_filename: str, *, encoding: str = "utf-8-sig") -> str:
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{base_filename}.json")
    with open(out_path, "w", encoding=encoding) as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    return out_path


# -------------------------- Generación de documento --------------------------
def generate_project_document(
    responses: dict,
    *,
    client,
    documents_dir: str,
    filename: Optional[str] = None,
    causas_tree: Optional[Dict[str, Any]] = None,
    objetivos_tree: Optional[Dict[str, Any]] = None,
    formularios_json_dir: Optional[str] = None,
) -> str:
    """Genera el .docx del proyecto con secciones que justifican el proyecto basado en
    los árboles de Causas/Efectos y Objetivos/Medios/Fines, manteniendo el orden de secciones definido.
    """
    if not filename:
        filename = f"proyecto_inversion_{int(time.time())}.docx"
    os.makedirs(documents_dir, exist_ok=True)
    filepath = os.path.join(documents_dir, filename)

    # Cargar árboles desde disco si no vienen en memoria
    if formularios_json_dir:
        if causas_tree is None and responses.get("upload_causa"):
            base = os.path.splitext(responses["upload_causa"])[0]  # sin .xlsx
            causas_tree = load_tree_json(os.path.join(formularios_json_dir, f"{base}.json"))
        if objetivos_tree is None and responses.get("upload_objetivo"):
            base = os.path.splitext(responses["upload_objetivo"])[0]
            objetivos_tree = load_tree_json(os.path.join(formularios_json_dir, f"{base}.json"))

    clean = _filtered_responses_for_report(responses)
    causas_outline = causas_tree_to_outline(causas_tree) if causas_tree else "(sin causas)"
    objetivos_outline = objetivos_tree_to_outline(objetivos_tree) if objetivos_tree else "(sin objetivos)"

    # Prompt con orden de secciones fijo y sin códigos de IDs visibles
    prompt = (
        "Eres un experto en formulación de proyectos bajo la Metodología General Ajustada (MGA) del Departamento Nacional de Planeación en Colombia(DNP). Redacta en ESPAÑOL "
        "y devuelve contenido en Markdown estructurado con #, ##, ### y #### (sin códigos C1/O1 visibles; "
        "no uses paréntesis con IDs). El sistema convertirá luego a Word con títulos y viñetas.\n\n"
        "ORDEN OBLIGATORIO DE SECCIONES:\n"
        "## Introducción\n"
        "## Planteamiento del problema u oportunidad\n"
        "## Población afectada y objetivo\n"
        "## Localización\n"
        "## Marco del problema: Causas y efectos\n"
        "## Marco de objetivos: Medios y fines\n"
        "## Componentes del proyecto\n"
        "## Cadena de valor\n"
        "## Conclusión y justificación final\n\n"
        "INSTRUCCIONES:\n"
        "- Integra los datos del usuario y los árboles provistos a continuación.\n"
        "- En 'Marco del problema: Causas y efectos': para cada causa, usa '### Causa' y un párrafo explicativo que conecte con la razón del proyecto; "
        "luego '#### Efecto directo' con explicación; después '#### Causas indirectas' listadas (a), b), ...) y bajo cada una viñetas con 'Efecto indirecto: ...'. "
        "No muestres códigos de IDs.\n"
        "- En 'Marco de objetivos: Medios y fines': para cada objetivo, usa '### Objetivo' con explicación; "
        "'#### Medio directo' y '#### Fin directo'; luego '#### Medios indirectos' listados (a), b), ...) y bajo cada uno viñetas con 'Fin indirecto: ...'. Sin códigos.\n"
        "- En 'Componentes del proyecto' incluye los componentes seleccionados por el usuario si existen; enuméralos con viñetas y explica brevemente su papel.\n"
        "- Mantén coherencia narrativa entre problema y objetivos, y cierra con una conclusión que justifique por qué el proyecto es sólido para recibir inversión.\n\n"
        f"Datos del usuario (JSON):\n{json.dumps(clean, ensure_ascii=False, indent=2)}\n\n"
        "Árbol de causas/efectos (outline):\n" + causas_outline + "\n\n"
        "Árbol de objetivos/medios/fines (outline):\n" + objetivos_outline + "\n\n"
        "RECUERDA: No incluyas códigos como C1, CI1, O1, MI1 en los títulos ni en el texto."
        "verifica consistencia numérica, define términos confusos y resume hallazgos clave al final de la sección"
    )

    completion = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": SYSTEM_PRIMER + "\nResponde exclusivamente en Markdown válido."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=3000,
        temperature=0.4,
    )
    md_text = (completion.choices[0].message.content or "").strip()

    # Escribir DOCX desde Markdown simple
    doc = Document()
    # Título del documento (nivel 0)
    titulo = responses.get("nombre_proyecto") or "Proyecto de Inversión - IDEC/IA"
    doc.add_heading(titulo, level=0)
    for line in md_text.splitlines():
        _add_markdown_line(doc, line)
    doc.save(filepath)
    return filepath


# -------------------------- Utilidades varias --------------------------
def _md_link(url: str, text: str) -> str:
    return f"[{text}]({url})"


def _is_yes(txt: str) -> bool:
    return bool(re.search(r"\b(sí|si)\b", txt or "", flags=re.I))


def _is_no(txt: str) -> bool:
    return bool(re.search(r"\bno\b", txt or "", flags=re.I))


def _num_from_id(id_str: str) -> int:
    m = re.findall(r"\d+", str(id_str))
    return int(m[0]) if m else 0


# -------------------------- Validación de plantillas --------------------------
def _count_nonempty(val) -> int:
    return 1 if (val is not None and str(val).strip() != "") else 0


def _validate_ws_causas(ws, start_row: int = 3) -> Tuple[bool, str, str]:
    total_any = 0
    any_expected_cells = 0
    id_hits = 0
    meaningful_rows = 0

    pat_causa = re.compile(r"^C\d+$", re.I)
    pat_ci    = re.compile(r"^C\d+CI\d+$", re.I)
    pat_ei    = re.compile(r"^C\d+CI\d+EI\d+$", re.I)

    for row in ws.iter_rows(min_row=start_row, values_only=True):
        vals = list(row)
        total_any += sum(_count_nonempty(v) for v in vals)

        vals += [None] * (11 - len(vals))
        A,B,C,D,E,F,G,H,I,J,K = vals[:11]

        any_expected_cells += sum(_count_nonempty(v) for v in (A,B,C,E,F,G,I,J,K))

        a_id = bool(A and pat_causa.match(str(A).strip()))
        f_id = bool(F and pat_ci.match(str(F).strip()))
        j_id = bool(J and pat_ei.match(str(J).strip()))
        id_hits += (1 if a_id else 0) + (1 if f_id else 0) + (1 if j_id else 0)

        direct_ok = a_id and (bool(_count_nonempty(B)) or bool(_count_nonempty(C)))
        ci_ok     = f_id and bool(_count_nonempty(G))
        ei_ok     = j_id and bool(_count_nonempty(K))
        if direct_ok or ci_ok or ei_ok:
            meaningful_rows += 1

    if total_any == 0:
        return (False, "empty", "La plantilla está vacía. Diligencia al menos una fila en las columnas requeridas.")

    if meaningful_rows > 0:
        return (True, "ok", "OK" )

    if any_expected_cells == 0 or id_hits == 0:
        return (False, "bad_shape", "El archivo no sigue la forma de la plantilla de Causas/Efectos." )

    return (False, "empty", "La plantilla está vacía. Diligencia al menos una fila en las columnas requeridas.")


def _validate_ws_objetivos(ws, start_row: int = 3) -> Tuple[bool, str, str]:
    total_any = 0
    any_expected_cells = 0
    id_hits = 0
    meaningful_rows = 0

    pat_obj  = re.compile(r"^O\d+$", re.I)
    pat_mi   = re.compile(r"^O\d+MI\d+$", re.I)
    pat_fi   = re.compile(r"^O\d+MI\d+FI\d+$", re.I)

    for row in ws.iter_rows(min_row=start_row, values_only=True):
        vals = list(row)
        total_any += sum(_count_nonempty(v) for v in vals)

        vals += [None] * (12 - len(vals))
        A,B,C,D,E,F,G,H,I,J,K,L = vals[:12]

        any_expected_cells += sum(_count_nonempty(v) for v in (A,B,C,D,F,G,H,J,K,L))

        a_id = bool(A and pat_obj.match(str(A).strip()))
        g_id = bool(G and pat_mi.match(str(G).strip()))
        k_id = bool(K and pat_fi.match(str(K).strip()))
        id_hits += (1 if a_id else 0) + (1 if g_id else 0) + (1 if k_id else 0)

        direct_ok = a_id and (bool(_count_nonempty(B)) or bool(_count_nonempty(C)) or bool(_count_nonempty(D)))
        mi_ok     = g_id and bool(_count_nonempty(H))
        fi_ok     = k_id and bool(_count_nonempty(L))
        if direct_ok or mi_ok or fi_ok:
            meaningful_rows += 1

    if total_any == 0:
        return (False, "empty", "La plantilla está vacía. Diligencia al menos una fila en las columnas requeridas.")

    if meaningful_rows > 0:
        return (True, "ok", "OK" )

    if any_expected_cells == 0 or id_hits == 0:
        return (False, "bad_shape", "El archivo no sigue la forma de la plantilla de Objetivos/Medios/Fines." )

    return (False, "empty", "La plantilla está vacía. Diligencia al menos una fila en las columnas requeridas.")


def validate_excel_bytes(tipo: str, data: bytes, *, sheet: Optional[str] = None, start_row: int = 3) -> Tuple[bool, str, str]:
    tipo = (tipo or "").lower()
    if tipo not in ("causa", "objetivo"):
        return (False, "bad_type", "Tipo inválido. Use 'causa' u 'objetivo'.")
    try:
        wb = load_workbook(BytesIO(data), data_only=True)
    except Exception:
        return (False, "not_xlsx", "El archivo no es un Excel válido (.xlsx)." )
    ws = wb[sheet] if sheet else wb.active
    if tipo == "causa":
        return _validate_ws_causas(ws, start_row=start_row)
    else:
        return _validate_ws_objetivos(ws, start_row=start_row)


# -------------------------- Parsers Excel --------------------------
# Causas: A,B,C  | D (sep) | E,F,G (CI) | H (sep) | I,J,K (Efectos Indirectos)
def parse_causas_xlsx(xlsx_path: str, *, sheet: Optional[str] = None, start_row: int = 3) -> Dict[str, Any]:
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    causas: Dict[str, Any] = {}
    ci_to_parent: Dict[str, str] = {}

    for row in ws.iter_rows(min_row=start_row, values_only=True):
        vals = list(row); vals += [None] * (11 - len(vals))
        A,B,C,D,E,F,G,H,I,J,K = vals[:11]

        if A:
            id_causa = str(A).strip()
            causas.setdefault(id_causa, {
                "id": id_causa,
                "descripcion": (str(B).strip() if B else None),
                "efecto_directo": {"descripcion": (str(C).strip() if C else None)},
                "causas_indirectas": {}
            })

        parent = str(E).strip() if E else None
        ci_id  = str(F).strip() if F else None
        ci_desc= str(G).strip() if G else None
        if parent and ci_id:
            base = causas.setdefault(parent, {
                "id": parent, "descripcion": None,
                "efecto_directo": {"descripcion": None},
                "causas_indirectas": {}
            })
            base["causas_indirectas"].setdefault(ci_id, {
                "id": ci_id, "descripcion": ci_desc, "efectos_indirectos": []
            })
            if ci_desc:
                base["causas_indirectas"][ci_id]["descripcion"] = ci_desc
            ci_to_parent[ci_id] = parent

            if "*" in causas:
                pend = causas["*"]["causas_indirectas"].pop(ci_id, None)
                if pend:
                    base["causas_indirectas"][ci_id]["efectos_indirectos"].extend(pend.get("efectos_indirectos", []))
                    if not base["causas_indirectas"][ci_id].get("descripcion"):
                        base["causas_indirectas"][ci_id]["descripcion"] = pend.get("descripcion")
                if not causas["*"]["causas_indirectas"]:
                    causas.pop("*", None)

        ci_ref   = str(I).strip() if I else None
        eff_id   = str(J).strip() if J else None
        eff_desc = str(K).strip() if K else None
        if ci_ref and eff_id:
            parent = ci_to_parent.get(ci_ref)
            ci_node = None
            if parent and parent in causas:
                ci_node = causas[parent]["causas_indirectas"].setdefault(
                    ci_ref, {"id":ci_ref,"descripcion":None,"efectos_indirectos":[]}
                )
            else:
                for c in causas.values():
                    if ci_ref in c["causas_indirectas"]:
                        ci_node = c["causas_indirectas"][ci_ref]; break
                if ci_node is None:
                    dummy = causas.setdefault("*", {
                        "id":"*","descripcion":None,
                        "efecto_directo":{"descripcion":None},
                        "causas_indirectas": {}
                    })
                    ci_node = dummy["causas_indirectas"].setdefault(
                        ci_ref, {"id":ci_ref,"descripcion":None,"efectos_indirectos":[]}
                    )
            ci_node["efectos_indirectos"].append({"id": eff_id, "descripcion": eff_desc})

    out: List[Dict[str, Any]] = []
    for cid, c in list(causas.items()):
        if cid == "*": continue
        c["causas_indirectas"] = list(c["causas_indirectas"].values())
        has_content = c.get("descripcion") or (c.get("efecto_directo") or {}).get("descripcion") or c["causas_indirectas"]
        if not has_content: continue
        out.append(c)

    out.sort(key=lambda x: (_num_from_id(x.get("id", "")), x.get("id", "")))
    return {"tipo": "causas", "items": out}


# Objetivos: A,B,C,D | E (sep) | F,G,H (MI) | I (sep) | J,K,L (Fines Indirectos)
def parse_objetivos_xlsx(xlsx_path: str, *, sheet: Optional[str] = None, start_row: int = 3) -> Dict[str, Any]:
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    objetivos: Dict[str, Any] = {}
    mi_to_parent: Dict[str, str] = {}

    for row in ws.iter_rows(min_row=start_row, values_only=True):
        vals = list(row); vals += [None] * (12 - len(vals))
        A,B,C,D,E,F,G,H,I,J,K,L = vals[:12]

        if A:
            id_obj = str(A).strip()
            objetivos.setdefault(id_obj, {
                "id": id_obj,
                "descripcion": (str(B).strip() if B else None),
                "medio_directo": {"descripcion": (str(C).strip() if C else None)},
                "fin_directo": {"descripcion": (str(D).strip() if D else None)},
                "medios_indirectos": {}
            })

        parent = str(F).strip() if F else None
        mi_id  = str(G).strip() if G else None
        mi_desc= str(H).strip() if H else None
        if parent and mi_id:
            base = objetivos.setdefault(parent, {
                "id": parent,
                "descripcion": None,
                "medio_directo": {"descripcion": None},
                "fin_directo": {"descripcion": None},
                "medios_indirectos": {}
            })
            base["medios_indirectos"].setdefault(mi_id, {
                "id": mi_id, "descripcion": mi_desc, "fines_indirectos": []
            })
            if mi_desc:
                base["medios_indirectos"][mi_id]["descripcion"] = mi_desc
            mi_to_parent[mi_id] = parent

            if "*" in objetivos:
                pend = objetivos["*"]["medios_indirectos"].pop(mi_id, None)
                if pend:
                    base["medios_indirectos"][mi_id]["fines_indirectos"].extend(pend.get("fines_indirectos", []))
                    if not base["medios_indirectos"][mi_id].get("descripcion"):
                        base["medios_indirectos"][mi_id]["descripcion"] = pend.get("descripcion")
                if not objetivos["*"]["medios_indirectos"]:
                    objetivos.pop("*", None)

        mi_ref  = str(J).strip() if J else None
        fi_id   = str(K).strip() if K else None
        fi_desc = str(L).strip() if L else None
        if mi_ref and fi_id:
            parent = mi_to_parent.get(mi_ref)
            mi_node = None
            if parent and parent in objetivos:
                mi_node = objetivos[parent]["medios_indirectos"].setdefault(
                    mi_ref, {"id":mi_ref,"descripcion":None,"fines_indirectos":[]}
                )
            else:
                for o in objetivos.values():
                    if mi_ref in o["medios_indirectos"]:
                        mi_node = o["medios_indirectos"][mi_ref]; break
                if mi_node is None:
                    dummy = objetivos.setdefault("*", {
                        "id":"*","descripcion":None,
                        "medio_directo":{"descripcion":None},
                        "fin_directo":{"descripcion":None},
                        "medios_indirectos": {}
                    })
                    mi_node = dummy["medios_indirectos"].setdefault(
                        mi_ref, {"id":mi_ref,"descripcion":None,"fines_indirectos":[]}
                    )
            mi_node["fines_indirectos"].append({"id": fi_id, "descripcion": fi_desc})

    out: List[Dict[str, Any]] = []
    for oid, o in list(objetivos.items()):
        if oid == "*": continue
        o["medios_indirectos"] = list(o["medios_indirectos"].values())
        has_content = o.get("descripcion") or (o.get("medio_directo") or {}).get("descripcion") or (o.get("fin_directo") or {}).get("descripcion") or o["medios_indirectos"]
        if not has_content: continue
        out.append(o)

    out.sort(key=lambda x: (_num_from_id(x.get("id", "")), x.get("id", "")))
    return {"tipo": "objetivos", "items": out}


# -------------------------- Render rápido de árboles a MD (para preview) --------------------------
def causas_tree_to_markdown(tree: Dict[str, Any]) -> str:
    if not tree or "items" not in tree: return ""
    lines = ["### Árbol de Causas y Efectos"]
    for c in tree["items"]:
        lines.append(f"- **{c['id']}**: {c.get('descripcion','') or ''}")
        ed = (c.get("efecto_directo") or {}).get("descripcion")
        if ed: lines.append(f"  - *Efecto directo:* {ed}")
        for ci in c.get("causas_indirectas", []):
            lines.append(f"  - **{ci['id']}**: {ci.get('descripcion','') or ''}")
            for ei in ci.get("efectos_indirectos", []):
                lines.append(f"    - {ei['id']}: {ei.get('descripcion','') or ''}")
    return "\n".join(lines)


def objetivos_tree_to_markdown(tree: Dict[str, Any]) -> str:
    if not tree or "items" not in tree: return ""
    lines = ["### Árbol de Objetivos, Medios y Fines"]
    for o in tree["items"]:
        lines.append(f"- **{o['id']}**: {o.get('descripcion','') or ''}")
        md = (o.get("medio_directo") or {}).get("descripcion")
        fd = (o.get("fin_directo") or {}).get("descripcion")
        if md: lines.append(f"  - *Medio directo:* {md}")
        if fd: lines.append(f"  - *Fin directo:* {fd}")
        for mi in o.get("medios_indirectos", []):
            lines.append(f"  - **{mi['id']}**: {mi.get('descripcion','') or ''}")
            for fi in mi.get("fines_indirectos", []):
                lines.append(f"    - {fi['id']}: {fi.get('descripcion','') or ''}")
    return "\n".join(lines)


# -------------------------- Orquestación post-upload --------------------------
def process_uploaded_excel(tipo: str, filepath: str, out_dir: str) -> Dict[str, Any]:
    tipo = (tipo or "").lower()
    if tipo not in ("causa", "objetivo"):
        raise ValueError("tipo debe ser 'causa' u 'objetivo'")
    if tipo == "causa":
        tree = parse_causas_xlsx(filepath)
        preview_md = causas_tree_to_markdown(tree)
    else:
        tree = parse_objetivos_xlsx(filepath)
        preview_md = objetivos_tree_to_markdown(tree)
    base = os.path.splitext(os.path.basename(filepath))[0]
    out_path = save_tree_json(tree, out_dir, base)
    return {"json_path": out_path, "tree": tree, "preview_md": preview_md}


# -------------------------- Conversation Flow --------------------------
conversation_flow = {
    "intro_bienvenida": {
        "prompt":
            "👋 ¡Hola! Soy tu asistente virtual para ayudarte en la formulación de proyectos de inversión relacionados con Infraestructura de Datos (IDEC) o Inteligencia Artificial (IA). Vamos a empezar paso a paso.\n\n"
            "Te acompañaré paso a paso para estructurar tu proyecto conforme a la Metodología General Ajustada (MGA) del Departamento Nacional de Planeación.\n\n"
            "🧰 Te haré preguntas clave para estructurar el proyecto.\n\n"
            "❓ Antes de continuar, ¿todo está claro? o ¿tienes algunas preguntas?" ,
        "options": [
            "Sí, entiendo el proceso y deseo continuar",
            "Tengo dudas respecto al proceso, me gustaría resolverlas antes de empezar"
        ],
        "next_step": "pregunta_3_entidad"
    },
    "gate_1_ciclo": {
        "prompt": "🔎 ¿Conoces el ciclo de inversión pública y las fases que lo componen?",
        "options": ["Sí, lo conozco", "No, no lo conozco"],
        "next_step": "gate_2_herramienta"
    },
    "gate_2_herramienta": {
        "prompt": "🧭 ¿Comprende que esta herramienta es de orientación y que el borrador resultante puede emplearse como insumo o apoyo en la etapa de formulación?",
        "options": ["Sí, lo comprendo", "No, no lo tengo claro"],
        "next_step": "pregunta_3_entidad"
    },

    "pregunta_3_entidad": {"prompt": "🏢 ¿Cuál es el nombre de tu entidad?", "next_step": "rol_abierto"},
    "rol_abierto": {
        "prompt": "👤 ¿Cuál es su rol dentro de la entidad (por ejemplo: Director de área, Coordinador, Profesional especializado, Analista, Asesor, Técnico operativo, Contratista de apoyo)?",
        "next_step": "elige_vertical"
    },

    "elige_vertical": {
        "prompt": "💡 ¿Deseas construir un proyecto de inversión asociando componentes de tecnologías de la información y las comunicaciones en temas de Infraestructura de datos (IDEC) o Inteligencia Artificial (IA)?",
        "options": ["Sí, en IDEC", "Sí, en IA", "No (Cierre de la conversación)"],
        "next_step": "nombre_proyecto"
    },

    "idec_componentes": {
        "prompt":
            "📚 La siguiente es la lista de los componentes que integran la IDEC, por favor selecciona los componentes que deseas incluir en tu proyecto de inversión. Selección múltiple :\n",
        "next_step": "nombre_proyecto"
    },

    "nombre_proyecto": {"prompt": "📝 ¿Cuál es el nombre del proyecto de inversión?", "next_step": "poblacion_afectada"},
    "poblacion_afectada": {"prompt": "👥 ¿Cuál es la población afectada por el proyecto de inversión? Descríbela y asocia un número", "next_step": "poblacion_objetivo"},
    "poblacion_objetivo": {"prompt": "🎯 ¿Cuál es la población objetivo que pretende ser beneficiada de la intervención que realiza el proyecto de inversión? Descríbela y asocia un número", "next_step": "localizacion"},
    "localizacion": {"prompt": "📍 ¿Cuál es la localización en la que se enmarca el proyecto (Ejemplo: Territorial-Territorio Norte, nacional-Colombia, departamental-Cundinamarca)?", "next_step": "problema_oportunidad"},
    "problema_oportunidad": {"prompt": "🧩 ¿Cuál es la problemática o la oportunidad que tu proyecto de inversión busca atender o resolver?", "next_step": "upload_causas"},

    "upload_causas": {"prompt": "📄 Cargue la plantilla diligenciada con las causas estructuradas. Recuerde que cada causa debe incluir dos causas indirectas, un efecto directo y un efecto indirecto.", "next_step": "upload_objetivos"},
    "upload_objetivos": {"prompt": "🎯 Cargue la plantilla diligenciada con los objetivos estructurados. Recuerde que cada objetivo debe incluir un medio directo, al menos un medio indirecto, un fin directo y un fin indirecto.", "next_step": "cadena_valor"},

    "cadena_valor": {"prompt": "🔗 ¿Cómo se constituye tu cadena de valor?", "next_step": "finalizado"}
}
