"""Build the training tasks of the agent (agent/bench/tasks_train.jsonl).

    uv run python -m agent.make_train_tasks
    uv run python -m agent.validate_bench --bench agent/bench/tasks_train.jsonl

The tasks have the same format as the benchmark (tasks.jsonl and tasks_ood.jsonl) but they use
only the 19 drugs of the corpus that appear in neither of the two benchmarks, so what the agent
learns from them is how to work (search, calculate, cite) and not the data of the test tasks.
Every fact comes from a sentence of a data sheet that is copied literally in evidence, and the
number the answer should have is computed from the same arithmetic the task needs, so the file
can be checked with agent.validate_bench like the benchmarks. The weights change from task to
task and the output is always the same (no randomness).
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from agent.validate_bench import evaluate_expression

OUT = Path(__file__).resolve().parent / "bench" / "tasks_train.jsonl"

KB = "search_knowledge_base"
CALC = "dose_calculator"
CONVERT = "convert_units"

# one evidence = (file of the corpus, sentence copied from it)
CEFTRIAXONA = ("ceftriaxona_62635.md", "se puede administrar una dosis intramuscular única de 50 mg/kg de ceftriaxona")
CEFUROXIMA = ("cefuroxima_62907.md", "una dosis de 60 mg/kg/día es adecuada para la mayoría de las infecciones")
CEFTAZIDIMA = ("ceftazidima_67007.md", "100-150 mg/kg/día divididos en tres dosis, máximo 6 g/día")
CEFOTAXIMA_NINOS = ("cefotaxima_57720.md", "reciben de 50 a 100 mg de cefotaxima (hasta 150 mg) por kilogramo de peso corporal diariamente")
CEFOTAXIMA_ADULTOS = ("cefotaxima_57720.md", "generalmente reciben de 1 a 2 g de cefotaxima cada 12 horas")
ERTAPENEM = ("ertapenem_02216001.md", "la dosis de INVANZ es de 15 mg/kg, administrados dos veces al día (no exceder 1 g/día)")
PIPERACILINA_NINOS = ("piperacilina_68080.md", "80 mg de piperacilina/10 mg de tazobactam por kg de peso corporal/cada 6 horas")
# The data sheet of piperacilina/tazobactam has the table of children's doses flattened: each dose
# line comes before its indication line, and the teacher model reads the pairs the other way
# round (100 mg/kg for the neutropenic child). The text alone does not settle it, so no task
# built on this evidence is kept. The ids of the other tasks do not change.
EXCLUDED_EVIDENCE = {PIPERACILINA_NINOS}
PIPERACILINA_ADULTOS = ("piperacilina_68080.md", "La dosis habitual es de 4 g de piperacilina/0,5 g de tazobactam administrados cada 8 horas")
AMOXICILINA_NINOS = ("amoxicilina_65131.md", "Niños de 3 meses o más: 25 mg/5 mg por kg de peso cada 8 horas")
AMOXICILINA_ADULTOS = ("amoxicilina_65131.md", "Para el tratamiento de infecciones indicadas en la sección 4.1: 1.000 mg/200 mg cada 8 horas")
FENTANILO = ("fentanilo_41764.md", "dosis de 50-100 µg/kg (1-2 mL/kg)")
BICARBONATO_DOSIS = ("sodio-bicarbonato_49811.md", "una dosis inicial de 1 mEq/kg (1 ml/kg de bicarbonato sódico 1M)")
BICARBONATO_VELOCIDAD = ("sodio-bicarbonato_49811.md", "Velocidad máxima de perfusión: hasta 1,5 mL/kg de peso corporal/hora")
POTASIO = ("cloruro-de-potasio_60353.md", "0,15 mmol de potasio/kg de peso corporal/ hora")
CLINDAMICINA_MAXIMA = ("clindamicina_63667.md", "aunque la dosis máxima recomendada es de 2,7 g/día")
CLINDAMICINA_EIP = ("clindamicina_63667.md", "debe iniciarse con 900 mg cada 8 horas por vía intravenosa")
IMIPENEM = ("imipenem_71285.md", "se administren 1.000 mg/1.000 mg cada seis horas")
MEROPENEM = ("meropenem_72610.md", "Infecciones complicadas del tracto urinario 500 mg o 1 g")
MORFINA = ("morfina_37472.md", "Adultos: dolor: 5,8 – 23,4 mg de hidrocloruro de morfina trihidrato cada 4 horas")
FLUCONAZOL_DOSIS = ("fluconazol_65723.md", "En infecciones con riesgo para la vida, la dosis diaria puede ser incrementada a 800 mg al día")
FLUCONAZOL_BOLSA = ("fluconazol_65723.md", "Cada 200 ml de solución para perfusión contiene 400 mg de fluconazol")
LEVOFLOXACINO = ("levofloxacino_68867.md", "Cada bolsa de 100 ml de solución para perfusión contiene 500 mg de levofloxacino")

# Tasks that depend on the weight (or the volume): text and expr use {w}. The two texts are used
# in turns. clause is how the task is written inside a task with three patients.
PER_KG = [
    dict(id="ceftriaxona", evidence=[CEFTRIAXONA], expr="50 * {w}", units=["mg", "mg/dosis"],
         weights=[12, 16, 20, 24, 28, 30],
         texts=["Un niño de {w} kg con otitis media aguda recibe el tratamiento inicial con ceftriaxona intramuscular, en la dosis única que indica la ficha técnica. ¿Cuántos mg de ceftriaxona recibe?",
                "Según la ficha técnica, ¿cuántos mg de ceftriaxona intramuscular, en dosis única, hay que dar a un niño de {w} kg con otitis media aguda en el tratamiento inicial?"],
         clause="un niño de {w} kg con otitis media aguda recibe la dosis única intramuscular de ceftriaxona"),
    dict(id="cefuroxima", evidence=[CEFUROXIMA], expr="60 * {w}", units=["mg", "mg/día"],
         weights=[10, 14, 18, 22, 26, 30],
         texts=["Un niño de {w} kg (menos de 40 kg) con neumonía adquirida en la comunidad recibe cefuroxima intravenosa con la dosis diaria que la ficha técnica considera adecuada para la mayoría de las infecciones. ¿Cuántos mg de cefuroxima recibe al día?",
                "¿Cuántos mg de cefuroxima por vía intravenosa al día corresponden a un niño de {w} kg (menor de 40 kg) con neumonía adquirida en la comunidad, con la dosis diaria adecuada para la mayoría de las infecciones según la ficha técnica?"],
         clause="un niño de {w} kg recibe la dosis diaria de cefuroxima adecuada para la mayoría de las infecciones"),
    dict(id="ceftazidima", evidence=[CEFTAZIDIMA], expr="100 * {w}", units=["mg", "mg/día"],
         weights=[12, 16, 20, 24, 28, 32],
         texts=["Un niño de {w} kg (menos de 40 kg) con una infección complicada del tracto urinario recibe ceftazidima con la dosis diaria normal más baja del intervalo de la ficha técnica. ¿Cuántos mg de ceftazidima recibe al día?",
                "Según la ficha técnica de la ceftazidima, ¿cuántos mg al día recibe un niño de {w} kg (menos de 40 kg) con una infección complicada del tracto urinario si se le da la dosis diaria más baja del intervalo?"],
         clause="un niño de {w} kg con una infección urinaria complicada recibe la dosis diaria más baja de ceftazidima"),
    dict(id="cefotaxima_ninos", evidence=[CEFOTAXIMA_NINOS], expr="50 * {w}", units=["mg", "mg/día"],
         weights=[8, 12, 18, 24, 30, 36],
         texts=["Un niño de {w} kg (menor de 12 años) recibe cefotaxima con la dosis diaria más baja del intervalo que indica la ficha técnica para lactantes y niños. ¿Cuántos mg de cefotaxima recibe al día?",
                "¿Cuántos mg al día de cefotaxima corresponden a un niño de {w} kg menor de 12 años si se aplica el extremo bajo de la dosis diaria por kilogramo de la ficha técnica?"],
         clause="un niño de {w} kg recibe la dosis diaria más baja de cefotaxima"),
    dict(id="ertapenem_dosis", evidence=[ERTAPENEM], expr="15 * {w}", units=["mg", "mg/dosis"],
         weights=[10, 14, 18, 22, 26, 30],
         texts=["Un niño de {w} kg (de 3 meses a 12 años) recibe ertapenem intravenoso con la dosis por kg que indica la ficha técnica. ¿Cuántos mg de ertapenem le corresponden en cada dosis?",
                "Según la ficha técnica, ¿cuántos mg de ertapenem por vía intravenosa hay que administrar en cada dosis a un niño de {w} kg de entre 3 meses y 12 años?"],
         clause="un niño de {w} kg recibe una dosis de ertapenem"),
    dict(id="ertapenem_dia", evidence=[ERTAPENEM], expr="15 * {w} * 2", units=["mg", "mg/día"],
         weights=[10, 14, 18, 22, 26, 30],
         texts=["Un niño de {w} kg (de 3 meses a 12 años) recibe ertapenem intravenoso con la pauta de la ficha técnica, que lo administra dos veces al día. ¿Cuántos mg de ertapenem recibe en un día?",
                "¿Cuántos mg de ertapenem recibe en 24 horas un niño de {w} kg de entre 3 meses y 12 años con la dosis por kg de la ficha técnica, repartida en dos administraciones?"],
         clause="un niño de {w} kg recibe la dosis diaria de ertapenem"),
    dict(id="piperacilina_ninos", evidence=[PIPERACILINA_NINOS], expr="80 * {w}", units=["mg", "mg/dosis"],
         weights=[14, 18, 22, 26, 28, 30],
         texts=["Un niño de {w} kg (de 2 a 12 años) con fiebre neutropénica recibe piperacilina/tazobactam con la dosis por peso de la ficha técnica. ¿Cuántos mg de piperacilina recibe en cada administración?",
                "Según la ficha técnica, ¿cuántos mg de piperacilina (con tazobactam) corresponden en cada administración a un niño de {w} kg de 2 a 12 años con neutropenia febril?"],
         clause="un niño de {w} kg con fiebre neutropénica recibe una administración de piperacilina"),
    dict(id="amoxicilina_dosis", evidence=[AMOXICILINA_NINOS], expr="25 * {w}", units=["mg", "mg/dosis"],
         weights=[8, 12, 16, 20, 24, 28],
         texts=["Un niño de {w} kg (de 3 meses o más y menos de 40 kg) recibe amoxicilina/ácido clavulánico intravenoso con la dosis por kg de la ficha técnica. ¿Cuántos mg de amoxicilina recibe en cada dosis?",
                "Según la ficha técnica, ¿cuántos mg de amoxicilina (con ácido clavulánico) hay que dar en cada dosis a un niño de {w} kg de 3 meses o más?"],
         clause="un niño de {w} kg recibe una dosis de amoxicilina"),
    dict(id="amoxicilina_dia", evidence=[AMOXICILINA_NINOS], expr="25 * {w} * 3", units=["mg", "mg/día"],
         weights=[8, 12, 16, 20, 24, 28],
         texts=["Un niño de {w} kg (de 3 meses o más y menos de 40 kg) recibe amoxicilina/ácido clavulánico intravenoso con la pauta de la ficha técnica, cada 8 horas. ¿Cuántos mg de amoxicilina recibe en 24 horas?",
                "¿Cuántos mg de amoxicilina (con ácido clavulánico) recibe en un día un niño de {w} kg con la pauta de la ficha técnica para niños de 3 meses o más?"],
         clause="un niño de {w} kg recibe la dosis diaria de amoxicilina"),
    dict(id="fentanilo_ug", evidence=[FENTANILO], expr="50 * {w}", units=["µg", "mcg", "microgramos"],
         weights=[55, 65, 70, 75, 80, 90],
         texts=["Un adulto de {w} kg recibe fentanilo como agente anestésico, con la dosis más baja por kg que indica la ficha técnica para esa técnica. ¿Cuántos µg de fentanilo recibe?",
                "Según la ficha técnica, ¿cuántos microgramos de fentanilo corresponden a un adulto de {w} kg con la dosis anestésica más baja del intervalo por kg?"],
         clause="un adulto de {w} kg recibe la dosis anestésica más baja de fentanilo (en µg)"),
    dict(id="fentanilo_ml", evidence=[FENTANILO], expr="2 * {w}", units=["mL"],
         weights=[55, 65, 70, 75, 80, 90],
         texts=["Un adulto de {w} kg recibe fentanilo como agente anestésico, con la dosis más alta del intervalo por kg que indica la ficha técnica para esa técnica. ¿Cuántos mL de solución son?",
                "Según la ficha técnica, ¿cuántos mL de fentanilo hay que administrar a un adulto de {w} kg con el extremo alto de la dosis anestésica por kg?"],
         clause="un adulto de {w} kg recibe el volumen más alto de fentanilo (en mL)"),
    dict(id="bicarbonato_dosis", evidence=[BICARBONATO_DOSIS], expr="1 * {w}", units=["mEq", "meq"],
         weights=[55, 60, 65, 70, 80, 90],
         texts=["Un adulto de {w} kg en paro cardíaco recibe la dosis inicial de bicarbonato sódico intravenoso que indica la ficha técnica. ¿Cuántos mEq recibe?",
                "Según la ficha técnica, ¿cuántos mEq de bicarbonato sódico intravenoso son la dosis inicial para un adulto de {w} kg en paro cardíaco?"],
         clause="un adulto de {w} kg en paro cardíaco recibe la dosis inicial de bicarbonato sódico (en mEq)"),
    dict(id="bicarbonato_velocidad", evidence=[BICARBONATO_VELOCIDAD], expr="1.5 * {w}", units=["mL/h", "mL/hora"],
         weights=[50, 55, 65, 70, 75, 85],
         texts=["Un paciente de {w} kg recibe bicarbonato sódico en perfusión a la velocidad máxima de la ficha técnica. ¿A cuántos mL/h va la perfusión?",
                "¿Cuál es, en mL/h, la velocidad máxima de perfusión de bicarbonato sódico para un paciente de {w} kg según la ficha técnica?"],
         clause="un paciente de {w} kg recibe bicarbonato sódico a la velocidad máxima (en mL/h)"),
    dict(id="potasio", evidence=[POTASIO], expr="0.15 * {w}", units=["mmol/h", "mmol/hora"],
         weights=[40, 45, 50, 55, 60, 65],  # up to 65 kg: above that 0.15 mmol/kg/h passes the 10 mmol/h of the data sheet
         texts=["Un paciente de {w} kg recibe cloruro de potasio en perfusión como suplemento de la nutrición parenteral, a la velocidad máxima por kg de peso que indica la ficha técnica para ese uso. ¿Cuántos mmol de potasio por hora recibe?",
                "Según la ficha técnica, ¿cuántos mmol/h de potasio es la velocidad máxima de perfusión de cloruro de potasio como suplemento de la nutrición parenteral para un paciente de {w} kg?"],
         clause="un paciente de {w} kg recibe cloruro de potasio a la velocidad máxima (en mmol/h)"),
]

# Tasks without weight. A clause is how the task is written when it goes inside a task with two
# drugs. category conversion means that a conversion of units is needed (g to mg).
FIXED = [
    dict(id="clindamicina_maxima", evidence=[CLINDAMICINA_MAXIMA], expr="2.7 * 1000", units=["mg", "mg/día"], conversion=True,
         text="Según la ficha técnica de la clindamicina, ¿cuántos mg al día son la dosis máxima recomendada en adultos?"),
    dict(id="clindamicina_eip", evidence=[CLINDAMICINA_EIP], expr="900 * 3", units=["mg", "mg/día"],
         text="Un adulto hospitalizado con enfermedad inflamatoria pélvica aguda empieza el tratamiento con clindamicina intravenosa como indica la ficha técnica. ¿Cuántos mg de clindamicina recibe en 24 horas?",
         clause="clindamicina intravenosa con la pauta de la ficha técnica para la enfermedad inflamatoria pélvica aguda"),
    dict(id="cefotaxima_adultos", evidence=[CEFOTAXIMA_ADULTOS], expr="2 * 1000 * 2", units=["mg", "mg/día"], conversion=True,
         text="Un adulto recibe cefotaxima con la dosis más alta del intervalo habitual de la ficha técnica, cada 12 horas. ¿Cuántos mg de cefotaxima recibe al día?",
         clause="cefotaxima con la dosis más alta del intervalo habitual de la ficha técnica, cada 12 horas"),
    dict(id="imipenem", evidence=[IMIPENEM], expr="1000 * 4", units=["mg", "mg/día"],
         text="Un adulto con una infección muy grave por un microorganismo poco sensible recibe imipenem/cilastatina con la pauta que indica la ficha técnica para esos casos. ¿Cuántos mg de imipenem recibe en 24 horas?",
         clause="imipenem/cilastatina con la pauta de la ficha técnica para infecciones muy graves por microorganismos poco sensibles"),
    dict(id="meropenem", evidence=[MEROPENEM], expr="1 * 3", units=["g", "g/día"],
         text="Un adulto con una infección complicada del tracto urinario recibe meropenem con la dosis más alta que la ficha técnica indica para esa infección, cada 8 horas. ¿Cuántos g de meropenem recibe al día?"),
    dict(id="piperacilina_adultos", evidence=[PIPERACILINA_ADULTOS], expr="4 * 3", units=["g", "g/día"],
         text="Un adulto recibe la dosis habitual de piperacilina/tazobactam de la ficha técnica. ¿Cuántos g de piperacilina recibe en 24 horas?"),
    dict(id="amoxicilina_adultos", evidence=[AMOXICILINA_ADULTOS], expr="1000 * 3", units=["mg", "mg/día"],
         text="Un adulto recibe amoxicilina/ácido clavulánico intravenoso con la pauta de la ficha técnica para las infecciones de la sección 4.1, cada 8 horas. ¿Cuántos mg de amoxicilina recibe en 24 horas?",
         clause="amoxicilina/ácido clavulánico intravenoso con la pauta de la ficha técnica para las infecciones de la sección 4.1, cada 8 horas"),
    dict(id="morfina", evidence=[MORFINA], expr="23.4 * 6", tolerance=0.05, units=["mg", "mg/día"],
         text="Un adulto con dolor recibe morfina con la dosis más alta del intervalo de la ficha técnica cada 4 horas. ¿Cuántos mg de hidrocloruro de morfina trihidrato recibe en 24 horas?"),
    dict(id="fluconazol", evidence=[FLUCONAZOL_DOSIS, FLUCONAZOL_BOLSA], expr="800 / (400 / 200)", units=["mL"],
         text="Un adulto con una infección con riesgo para la vida recibe fluconazol en perfusión con la dosis diaria aumentada que indica la ficha técnica. Con la presentación de la ficha, ¿cuántos mL de solución para perfusión son?"),
]

# Tasks with a volume as the variable.
PER_VOLUME = [
    dict(id="levofloxacino", evidence=[LEVOFLOXACINO], expr="500 / 100 * {w}", units=["mg"],
         weights=[150, 200, 250, 300, 350, 400],
         texts=["Según la ficha técnica del levofloxacino en solución para perfusión, ¿cuántos mg de levofloxacino hay en {w} mL?",
                "Una solución para perfusión de levofloxacino tiene la concentración que indica su ficha técnica (bolsa de 100 mL). ¿Cuántos mg de levofloxacino hay en {w} mL?"]),
]


def _task(number: int, category: str, text: str, expr: str, units: list[str], evidence: list,
          tools: list[str], conversion: bool = False, tolerance: float | None = None) -> dict:
    value = round(evaluate_expression(expr), 6)
    check = {"type": "number", "value": value, "unit": units}
    if tolerance is not None:
        check["tolerance"] = tolerance
    task = {
        "id": f"x{number:03d}",
        "category": category,
        "core": True,
        "split": "train",
        "task": text,
        "required_tools": tools,
    }
    if conversion:
        task["tool_alternatives"] = {CONVERT: [CALC]}
    task.update({
        "check": check,
        "answer_exprs": [expr],
        "evidence": [{"file": f, "text": t} for f, t in evidence],
        "solution": f"{expr} = {value:g}",
    })
    return task


def build_tasks() -> list[dict]:
    """Every training task, in a fixed order, with ids x001, x002, ... (the excluded ones leave a gap)."""
    pending = []  # (category, text, expr, units, evidence, tools, conversion, tolerance)
    for fact in PER_KG + PER_VOLUME:
        for i, w in enumerate(fact["weights"]):
            pending.append(("ficha_calculo", fact["texts"][i % 2].format(w=w), fact["expr"].format(w=w),
                            fact["units"], fact["evidence"], [KB, CALC], False, None))
    for fact in FIXED:
        conversion = fact.get("conversion", False)
        pending.append(("ficha_conversion" if conversion else "ficha_calculo", fact["text"], fact["expr"],
                        fact["units"], fact["evidence"], [KB, CALC, CONVERT] if conversion else [KB, CALC],
                        conversion, fact.get("tolerance")))
    # two drugs: the daily totals in mg of two adults
    daily = [f for f in FIXED if f["units"] == ["mg", "mg/día"] and "clause" in f]
    for a, b in itertools.combinations(daily, 2):
        text = (f"Un adulto recibe en 24 horas {a['clause']} y otro adulto recibe {b['clause']}. "
                "Según sus fichas técnicas, ¿cuántos mg suman en total las dos dosis diarias? Cuenta solo el antibiótico principal "
                "de cada una: no sumes la cilastatina ni el ácido clavulánico.")
        conversion = a.get("conversion", False) or b.get("conversion", False)
        pending.append(("dos_fichas", text, f"({a['expr']}) + ({b['expr']})", ["mg"], a["evidence"] + b["evidence"],
                        [KB, CALC, CONVERT] if conversion else [KB, CALC], conversion, None))
    # three patients: children's doses by weight, added in mg (the quantity of each one is in its clause)
    mg = [f for f in PER_KG if f["units"][0] == "mg"]
    for n, trio in enumerate(itertools.combinations(mg, 3)):
        if n % 11 != 0:  # a sample of the 220 combinations
            continue
        weights = [f["weights"][(n + k) % len(f["weights"])] for k, f in enumerate(trio)]
        parts = [f"{'ABC'[k]}: {f['clause'].format(w=w)}" for k, (f, w) in enumerate(zip(trio, weights))]
        text = ("Calcula, según las fichas técnicas, la cantidad de cada medicamento que indica cada caso y "
                "súmalas. " + "; ".join(parts) + ". ¿Cuántos mg suman en total los tres pacientes?")
        expr = " + ".join(f"({f['expr'].format(w=w)})" for f, w in zip(trio, weights))
        pending.append(("larga", text, expr, ["mg"], [e for f in trio for e in f["evidence"]], [KB, CALC], False, None))
    tasks = [_task(i, *args) for i, args in enumerate(pending, 1)]
    return [t for t in tasks if not any((e["file"], e["text"]) in EXCLUDED_EVIDENCE for e in t["evidence"])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    tasks = build_tasks()
    Path(args.out).write_text("\n".join(json.dumps(t, ensure_ascii=False) for t in tasks) + "\n", encoding="utf-8")
    print(f"{len(tasks)} tasks written to {args.out}")


if __name__ == "__main__":
    main()
