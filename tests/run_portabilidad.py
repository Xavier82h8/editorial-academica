#!/usr/bin/env python3
"""Prueba de humo de portabilidad: skills en formato abierto, rutas, despachador, instalador y catálogo de reglas.

Uso: python tests/run_portabilidad.py
Comprueba:
- todo skills/*/SKILL.md tiene frontmatter con `name` (= carpeta, minúsculas y guiones) y `description` <= 1024 caracteres;
- toda ruta `references/...` o `scripts/...` mencionada en un SKILL.md existe (en la skill o, con `<raíz>/`, en el repositorio);
- `${CLAUDE_PLUGIN_ROOT}` solo aparece en los SKILL.md dentro de la frase explicativa (que nombra EDITORIAL_ROOT);
- la documentación para usuarios no usa `python -I` (solo las pruebas);
- `editorial.py <sub> --help` sale 0 para todos los subcomandos;
- `instalar.py --cli X --proyecto <tmp>` crea la estructura esperada, resuelve la raíz real en el SKILL.md instalado y se desinstala;
- commands/*.toml están al día con commands/*.md (y son TOML válido si hay tomllib);
- `catalogo.py --comprobar` OK; gemini-extension.json válido; AGENTS.md <= 200 líneas.
Salida: 0 todo OK; 1 alguna falla.
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PY = sys.executable
fallas, total = [], 0


def check(ok, msg):
    global total
    total += 1
    if not ok:
        fallas.append(msg)
        print(f"[FALLA] {msg}")
    return ok


def correr(*args, cwd=None):
    r = subprocess.run([PY, *map(str, args)], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def frontmatter(texto):
    m = re.match(r"---\r?\n(.*?)\r?\n---", texto, re.S)
    if not m:
        return None
    import yaml
    try:
        d = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return d if isinstance(d, dict) else None


def prueba_skills():
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    check(len(skills) >= 6, f"se esperaban >= 6 skills, hay {len(skills)}")
    patron = re.compile(r"(<raíz>/)?((?:references|scripts)/[\w.+-]+(?:/[\w.+-]+)*\.[A-Za-z]+)")
    for f in skills:
        carpeta = f.parent.name
        texto = f.read_text(encoding="utf-8")
        fm = frontmatter(texto)
        if not check(fm is not None, f"{carpeta}: frontmatter ausente o YAML inválido"):
            continue
        nombre, desc = fm.get("name"), fm.get("description")
        check(nombre == carpeta, f"{carpeta}: name {nombre!r} distinto de la carpeta")
        check(isinstance(nombre, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", nombre) is not None,
              f"{carpeta}: name no es minúsculas-guiones")
        check(isinstance(desc, str) and 0 < len(desc) <= 1024, f"{carpeta}: description vacía o > 1024 caracteres")
        for m in patron.finditer(texto):
            rel = m.group(2)
            existe = (ROOT / rel).exists() if m.group(1) else ((f.parent / rel).exists() or (ROOT / rel).exists())
            check(existe, f"{carpeta}: la ruta mencionada no existe: {m.group(0)}")
        for n, linea in enumerate(texto.splitlines(), 1):
            if "${CLAUDE_PLUGIN_ROOT}" in linea:
                check("EDITORIAL_ROOT" in linea, f"{carpeta}:{n}: ${{CLAUDE_PLUGIN_ROOT}} fuera de la frase explicativa")


def prueba_docs_sin_I():
    archivos = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "GEMINI.md"]
    for d in ("commands", "skills", "agents"):
        archivos += sorted((ROOT / d).rglob("*.md"))
    for f in archivos:
        if not f.exists():
            continue
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in re.finditer(r"python3? -I\s+(\S+)", linea):
                check(m.group(1).strip("`\"'").replace("<raíz>/", "").startswith("tests/"),
                      f"{f.relative_to(ROOT)}:{n}: `-I` en documentación de usuario (solo se deja en tests): {m.group(0)}")


def prueba_despachador():
    sys.path.insert(0, str(SCRIPTS))
    import editorial
    for sub in editorial.COMANDOS:
        code, out = correr(SCRIPTS / "editorial.py", sub, "--help")
        check(code == 0 and "usage" in out.lower(), f"editorial.py {sub} --help sale {code}")
    code, _ = correr(SCRIPTS / "editorial.py", "--help")
    check(code == 0, "editorial.py --help no sale 0")
    code, _ = correr(SCRIPTS / "editorial.py", "no-existe")
    check(code == 2, "editorial.py <desconocido> debe salir con 2")


def prueba_instalador():
    esperado = {
        "codex": (".agents/skills", "AGENTS.md"), "gemini": (".agents/skills", "GEMINI.md"),
        "cursor": (".agents/skills", "AGENTS.md"), "copilot": (".github/skills", "AGENTS.md"),
        "opencode": (".opencode/skills", "AGENTS.md"),
    }
    extra = {"gemini": [".gemini/commands/auditar.toml"], "cursor": [".cursor/agents/juez-formato.md"],
             "opencode": [".opencode/agents/juez-formato.md", ".opencode/commands/auditar.md"]}
    skills = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists())
    raiz = ROOT.as_posix()
    for cli_id, (carpeta, instr) in esperado.items():
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            code, out = correr(SCRIPTS / "instalar.py", "--cli", cli_id, "--proyecto", tmp)
            check(code == 0, f"instalar --cli {cli_id} sale {code}: {out[-200:]}")
            for s in skills:
                md = tmp / carpeta / s / "SKILL.md"
                if not check(md.exists(), f"{cli_id}: falta {carpeta}/{s}/SKILL.md"):
                    continue
                t = md.read_text(encoding="utf-8")
                check("<raíz>" not in t, f"{cli_id}/{s}: queda el marcador <raíz> sin resolver")
            ed = (tmp / carpeta / "editorial-academica" / "SKILL.md")
            check(ed.exists() and raiz in ed.read_text(encoding="utf-8"), f"{cli_id}: el SKILL.md instalado no contiene la raíz real")
            check((tmp / instr).exists() and raiz in (tmp / instr).read_text(encoding="utf-8"), f"{cli_id}: {instr} ausente o sin raíz")
            for e in extra.get(cli_id, []):
                check((tmp / e).exists(), f"{cli_id}: falta {e}")
            # no sobrescribe un AGENTS.md existente
            (tmp / instr).write_text("MIO\n", encoding="utf-8")
            code, out = correr(SCRIPTS / "instalar.py", "--cli", cli_id, "--proyecto", tmp)
            check((tmp / instr).read_text(encoding="utf-8") == "MIO\n" and "no se modifica" in out,
                  f"{cli_id}: sobrescribió o no avisó sobre {instr} existente")
            code, out = correr(SCRIPTS / "instalar.py", "--cli", cli_id, "--proyecto", tmp, "--desinstalar")
            check(code == 0 and not (tmp / carpeta / "apa7").exists(), f"{cli_id}: --desinstalar no quitó las skills")
            check((tmp / instr).read_text(encoding="utf-8") == "MIO\n", f"{cli_id}: --desinstalar tocó el {instr} del usuario")
    code, out = correr(SCRIPTS / "instalar.py", "--cli", "claude")
    check(code == 0 and "claude plugin install" in out, "instalar --cli claude debe imprimir `claude plugin install`")
    with tempfile.TemporaryDirectory() as tmp:
        code, out = correr(SCRIPTS / "instalar.py", "--cli", "codex", "--proyecto", tmp, "--simular")
        check(code == 0 and not any(pathlib.Path(tmp).iterdir()), "--simular escribió archivos")


def prueba_toml():
    sys.path.insert(0, str(SCRIPTS))
    import instalar
    try:
        import tomllib
    except ImportError:
        tomllib = None
    for md in sorted((ROOT / "commands").glob("*.md")):
        t = md.with_suffix(".toml")
        if not check(t.exists(), f"falta {t.name}: python scripts/instalar.py --generar-toml"):
            continue
        actual = t.read_text(encoding="utf-8").replace("\r\n", "\n")
        check(actual == instalar.md_a_toml(md.read_text(encoding="utf-8")),
              f"{t.name} desactualizado respecto a {md.name}: python scripts/instalar.py --generar-toml")
        if tomllib:
            try:
                d = tomllib.loads(actual)
                check(bool(d.get("prompt")) and bool(d.get("description")), f"{t.name}: sin prompt o description")
            except tomllib.TOMLDecodeError as e:
                check(False, f"{t.name}: TOML inválido ({e})")


def prueba_catalogo_y_extension():
    code, out = correr(SCRIPTS / "catalogo.py", "--comprobar")
    check(code == 0, f"catalogo.py --comprobar: {out.strip()[-200:]}")
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    try:
        ext = json.loads((ROOT / "gemini-extension.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        check(False, f"gemini-extension.json ilegible: {e}")
        return
    check(ext.get("name") == plugin["name"] and re.fullmatch(r"[a-z0-9-]+", ext.get("name", "")) is not None,
          "gemini-extension.json: name distinto del plugin o inválido")
    check(ext.get("version") == plugin["version"], f"gemini-extension.json: version {ext.get('version')} != plugin.json {plugin['version']}")
    check(bool(ext.get("description")), "gemini-extension.json: sin description")
    check(ext.get("contextFileName") and (ROOT / ext["contextFileName"]).exists(), "gemini-extension.json: contextFileName no existe")
    check(len((ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()) <= 200, "AGENTS.md supera 200 líneas")
    check("EDITORIAL_ROOT" in (ROOT / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md no menciona EDITORIAL_ROOT")
    # caracteres de control en el código (un «\b» que se escribió como retroceso dejó una regex que nunca coincidía)
    for carpeta in ("scripts", "tests", "ejemplos", "skills"):
        for py in (ROOT / carpeta).rglob("*.py"):
            malos = sorted({c for c in py.read_bytes() if c < 0x20 and c not in (9, 10, 13)})
            check(not malos, f"{py.relative_to(ROOT)}: caracteres de control {[hex(c) for c in malos]}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for f in (prueba_skills, prueba_docs_sin_I, prueba_despachador, prueba_instalador, prueba_toml, prueba_catalogo_y_extension):
        f()
    if fallas:
        print(f"\nportabilidad: {len(fallas)} fallas de {total} comprobaciones")
        sys.exit(1)
    print(f"portabilidad: OK ({total} comprobaciones)")


if __name__ == "__main__":
    main()
