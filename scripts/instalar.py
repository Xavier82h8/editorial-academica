#!/usr/bin/env python3
"""Instalador de editorial-academica para otras CLI de agentes (Codex, Gemini CLI, Cursor, GitHub Copilot CLI, OpenCode, Claude Code).

Uso:
  python scripts/instalar.py --cli codex|gemini|cursor|copilot|opencode|claude [--proyecto DIR] [--enlazar]
                             [--sin-agentes] [--forzar] [--simular] [--desinstalar]
  python scripts/instalar.py --generar-toml          genera commands/*.toml (Gemini) a partir de commands/*.md

Qué hace (según la documentación oficial de cada CLI; ver AGENTS.md y el plan F4):
- Copia (o enlaza con --enlazar: symlink, junction en Windows) cada skills/<n>/ a la carpeta de skills de la CLI:
    codex, gemini  .agents/skills  (usuario: ~/.agents/skills)      cursor   .agents/skills  (usuario: ~/.cursor/skills)
    copilot        .github/skills  (usuario: ~/.copilot/skills)     opencode .opencode/skills (usuario: ~/.config/opencode/skills)
  Con --proyecto DIR se instala en DIR; sin él, en el directorio de usuario.
- En los SKILL.md (y demás .md) copiados sustituye el marcador `<raíz>` por la ruta absoluta de este repositorio. Con --enlazar
  no se modifica nada (sería editar el repositorio): define EDITORIAL_ROOT=<ruta del repositorio>.
- Con --proyecto deja AGENTS.md (GEMINI.md en Gemini) con la raíz ya resuelta si no existe; si existe, NO lo toca: imprime el
  bloque a añadir.
- Agentes: OpenCode (.opencode/agents, mode: subagent) y Cursor (.cursor/agents) los reciben generados desde agents/*.md.
  En las demás CLI los agentes son pasos descritos en AGENTS.md. Comandos: OpenCode (.opencode/commands/*.md) y Gemini
  (.gemini/commands/*.toml) reciben los de commands/*.md generados; Gemini también puede instalarse como extensión
  (`gemini extensions install <url-del-repo>`, que usa gemini-extension.json y commands/*.toml).
- claude: imprime `claude plugin marketplace add` / `claude plugin install` (no copia nada).
- --desinstalar quita exactamente lo que dejó la instalación (manifiesto `.editorial-academica.<cli>.json`). --simular
  imprime lo que haría sin escribir nada.
Salida: 0 correcto; 2 error de uso o de entrada.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cli  # noqa: E402

MARCADOR = "<raíz>"
CLIS = {  # destino de skills en el proyecto / en el usuario, archivo de instrucciones, agentes, comandos
    "codex": {"skills": (".agents/skills", "~/.agents/skills"), "instr": "AGENTS.md"},
    "gemini": {"skills": (".agents/skills", "~/.agents/skills"), "instr": "GEMINI.md",
               "comandos": ("toml", ".gemini/commands", "~/.gemini/commands")},
    "cursor": {"skills": (".agents/skills", "~/.cursor/skills"), "instr": "AGENTS.md",
               "agentes": (".cursor/agents", "~/.cursor/agents")},
    "copilot": {"skills": (".github/skills", "~/.copilot/skills"), "instr": "AGENTS.md"},
    "opencode": {"skills": (".opencode/skills", "~/.config/opencode/skills"), "instr": "AGENTS.md",
                 "agentes": (".opencode/agents", "~/.config/opencode/agents"),
                 "comandos": ("md", ".opencode/commands", "~/.config/opencode/commands")},
    "claude": {},
}
NOTA_RAIZ_TOML = ("(La raíz del plugin, `<raíz>`, es la variable de entorno EDITORIAL_ROOT o la carpeta de esta extensión, "
                  "p. ej. ~/.gemini/extensions/editorial-academica.)\n\n")


class Plan:
    """Acumula acciones y las ejecuta (o solo las imprime con --simular)."""

    def __init__(self, simular):
        self.simular = simular
        self.creados = []  # [{"ruta":..., "tipo": "dir"|"archivo"|"enlace"}]

    def decir(self, msg):
        print(("[simular] " if self.simular else "") + msg)

    def escribir(self, ruta, texto):
        self.decir(f"escribir {ruta}")
        if not self.simular:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(texto, encoding="utf-8", newline="\n")
        self.creados.append({"ruta": str(ruta), "tipo": "archivo"})

    def copiar_skill(self, origen, destino, raiz):
        self.decir(f"copiar {origen.name}/ -> {destino}")
        if not self.simular:
            if destino.exists():
                shutil.rmtree(destino)
            shutil.copytree(origen, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for f in destino.rglob("*.md"):
                t = f.read_text(encoding="utf-8")
                if MARCADOR in t:
                    f.write_text(t.replace(MARCADOR, raiz), encoding="utf-8", newline="\n")
        self.creados.append({"ruta": str(destino), "tipo": "dir"})

    def enlazar_skill(self, origen, destino):
        self.decir(f"enlazar {destino} -> {origen}")
        if not self.simular:
            destino.parent.mkdir(parents=True, exist_ok=True)
            quitar_enlace_o_dir(destino)
            if os.name == "nt":
                r = subprocess.run(["cmd", "/c", "mklink", "/J", str(destino), str(origen)], capture_output=True, text=True)
                if r.returncode:
                    cli.error(f"no se pudo crear la junction {destino}: {r.stdout.strip() or r.stderr.strip()}")
            else:
                os.symlink(origen, destino, target_is_directory=True)
        self.creados.append({"ruta": str(destino), "tipo": "enlace"})


def quitar_enlace_o_dir(ruta):
    """Borra un symlink/junction sin seguirlo (nunca rmtree sobre un enlace); un directorio real, con rmtree."""
    if os.path.islink(ruta):
        os.unlink(ruta)
    elif ruta.exists():
        if os.name == "nt" and es_junction(ruta):
            os.rmdir(ruta)
        else:
            shutil.rmtree(ruta)


def es_junction(ruta):
    f = getattr(os.path, "isjunction", None)
    if f:
        return f(ruta)
    try:
        return bool(os.lstat(ruta).st_file_attributes & 0x400) and not os.path.islink(ruta)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (AttributeError, OSError):
        return False


def partir_frontmatter(texto):
    texto = texto.replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n?(.*)\Z", texto, re.S)
    if not m:
        return {}, texto
    import yaml
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


def md_a_toml(texto, raiz=None):
    """commands/<x>.md (frontmatter + $ARGUMENTS) -> comando TOML de Gemini (`description`, `prompt`, `{{args}}`)."""
    fm, cuerpo = partir_frontmatter(texto)
    cuerpo = cuerpo.strip("\n").replace("$ARGUMENTS", "{{args}}")
    if raiz:
        cuerpo = cuerpo.replace("${CLAUDE_PLUGIN_ROOT}", raiz).replace(MARCADOR, raiz)
    else:
        cuerpo = NOTA_RAIZ_TOML + cuerpo.replace("${CLAUDE_PLUGIN_ROOT}", MARCADOR)
    cuerpo = cuerpo.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    desc = json.dumps(str(fm.get("description", "")), ensure_ascii=False)
    return f'description = {desc}\nprompt = """\n{cuerpo}\n"""\n'


def md_a_comando_opencode(texto, raiz):
    fm, cuerpo = partir_frontmatter(texto)
    cuerpo = cuerpo.strip("\n").replace("${CLAUDE_PLUGIN_ROOT}", raiz).replace(MARCADOR, raiz)
    return f"---\ndescription: {json.dumps(str(fm.get('description', '')), ensure_ascii=False)}\n---\n{cuerpo}\n"


def md_a_agente(texto, raiz, cli_id):
    """agents/<x>.md (frontmatter de Claude: model, tools) -> agente de OpenCode (mode: subagent) o de Cursor."""
    fm, cuerpo = partir_frontmatter(texto)
    cuerpo = cuerpo.strip("\n").replace("${CLAUDE_PLUGIN_ROOT}", raiz).replace(MARCADOR, raiz)
    cab = [f"description: {json.dumps(str(fm.get('description', '')), ensure_ascii=False)}"]
    if cli_id == "opencode":
        cab.append("mode: subagent")
    else:
        cab.insert(0, f"name: {fm.get('name', '')}")
    return "---\n" + "\n".join(cab) + f"\n---\n{cuerpo}\n"


def instrucciones(raiz):
    t = (ROOT / "AGENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    return (f"> Raíz de editorial-academica en esta máquina: `{raiz}` (equivale a `EDITORIAL_ROOT`).\n\n"
            + t.replace(MARCADOR, raiz))


def bloque_para_anadir(raiz):
    return (f"## editorial-academica\n\nEditorial y juez APA 7 / IEEE. Raíz: `{raiz}` (variable `EDITORIAL_ROOT`). Scripts: "
            f"`python {raiz}/scripts/editorial.py <subcomando>` (`--help`). Lee `{raiz}/AGENTS.md` para flujos y reglas duras; "
            f"las skills están instaladas en la carpeta de skills de esta CLI.\n")


def generar_toml(simular=False):
    """commands/*.toml para la extensión de Gemini CLI, generados desde commands/*.md (no se editan a mano)."""
    cmds = sorted((ROOT / "commands").glob("*.md"))
    for md in cmds:
        destino = md.with_suffix(".toml")
        if simular:
            print(f"[simular] escribir {destino}")
        else:
            destino.write_text(md_a_toml(md.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
            print(f"escrito {destino.relative_to(ROOT)}")
    return len(cmds)


def mensajes_claude(raiz):
    nombre = "editorial-academica"
    try:
        nombre = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["name"]
    except (OSError, ValueError, KeyError):
        pass
    print("Claude Code instala el plugin desde un marketplace; ejecuta (en una terminal):\n"
          f"  claude plugin marketplace add {raiz}\n"
          f"  claude plugin install editorial-academica@{nombre}\n"
          "Con el repositorio publicado: `claude plugin marketplace add <dueño>/<repo>`. Dentro de Claude Code: `/plugin`.\n"
          "Verifica con `/editorial-academica:auditar` o `claude plugin list`.")


def base_y_manifiesto(a, nombre_cli):
    base = pathlib.Path(a.proyecto).resolve() if a.proyecto else pathlib.Path.home()
    return base, base / f".editorial-academica.{nombre_cli}.json"


def dest(base, par, proyecto):
    return base / par[0] if proyecto else pathlib.Path(os.path.expanduser(par[1]))


def desinstalar(a, cfg):
    base, manifiesto = base_y_manifiesto(a, a.cli)
    if not manifiesto.exists():
        cli.error(f"no hay instalación registrada ({manifiesto.name} no existe en {base})")
    datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    plan = Plan(a.simular)
    for item in datos["creados"]:
        r = pathlib.Path(item["ruta"])
        plan.decir(f"quitar {r}")
        if a.simular or not (r.exists() or os.path.islink(r)):
            continue
        if item["tipo"] == "archivo":
            r.unlink()
        else:
            quitar_enlace_o_dir(r)
        for padre in (r.parent, r.parent.parent):  # carpetas que quedaron vacías (.agents/skills, .agents…)
            try:
                if padre != base and not any(padre.iterdir()):
                    padre.rmdir()
            except OSError:
                pass
    if not a.simular:
        manifiesto.unlink()
    plan.decir(f"desinstalado {a.cli}")


def instalar(a, cfg):
    raiz = ROOT.as_posix()
    base, manifiesto = base_y_manifiesto(a, a.cli)
    previo = set()
    if manifiesto.exists():
        previo = {c["ruta"] for c in json.loads(manifiesto.read_text(encoding="utf-8"))["creados"]}
    if not a.proyecto:
        print(f"Instalación de usuario en {pathlib.Path.home()} (usa --proyecto DIR para un proyecto).")
    plan = Plan(a.simular)
    # skills
    carpeta = dest(base, cfg["skills"], a.proyecto)
    skills = sorted(d for d in (ROOT / "skills").iterdir() if (d / "SKILL.md").exists())
    for s in skills:
        d = carpeta / s.name
        if (d.exists() or os.path.islink(d)) and str(d) not in previo and not a.forzar:
            print(f"AVISO: {d} ya existe y no es de esta instalación; se omite (--forzar lo reemplaza).", file=sys.stderr)
            continue
        if a.enlazar:
            plan.enlazar_skill(s, d)
        else:
            plan.copiar_skill(s, d, raiz)
    # agentes y comandos
    if not a.sin_agentes and "agentes" in cfg:
        carpeta_ag = dest(base, cfg["agentes"], a.proyecto)
        for f in sorted((ROOT / "agents").glob("*.md")):
            plan.escribir(carpeta_ag / f.name, md_a_agente(f.read_text(encoding="utf-8"), raiz, a.cli))
    if "comandos" in cfg:
        formato, *par = cfg["comandos"]
        carpeta_cm = dest(base, par, a.proyecto)
        for f in sorted((ROOT / "commands").glob("*.md")):
            t = f.read_text(encoding="utf-8")
            if formato == "toml":
                plan.escribir(carpeta_cm / (f.stem + ".toml"), md_a_toml(t, raiz))
            else:
                plan.escribir(carpeta_cm / f.name, md_a_comando_opencode(t, raiz))
    # instrucciones
    nombre = cfg["instr"]
    if a.proyecto:
        objetivo = base / nombre
        if objetivo.exists():
            print(f"{nombre} ya existe en {base}: no se modifica. Añade este bloque:\n\n{bloque_para_anadir(raiz)}")
        else:
            plan.escribir(objetivo, instrucciones(raiz))
    else:
        print(f"Para activar las instrucciones, añade a tu archivo global de {nombre} de {a.cli}:\n\n{bloque_para_anadir(raiz)}")
    if a.enlazar:
        print(f"Con --enlazar los SKILL.md conservan `{MARCADOR}`: define EDITORIAL_ROOT={raiz} en el entorno de {a.cli}.")
    if not a.simular:
        base.mkdir(parents=True, exist_ok=True)
        manifiesto.write_text(json.dumps({"cli": a.cli, "raiz": raiz, "creados": plan.creados}, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    sin_agentes = "agentes" not in cfg
    if sin_agentes:
        print(f"Nota: {a.cli} no recibe agentes generados; los agentes de agents/*.md son pasos secuenciales descritos en {nombre}.")
    print(f"Verifica: abre {a.cli} y pide «audita este documento con editorial-academica», o ejecuta "
          f"`python {raiz}/scripts/editorial.py --version`.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Instala editorial-academica en otra CLI de agentes.")
    ap.add_argument("--cli", choices=sorted(CLIS), help="CLI destino")
    ap.add_argument("--proyecto", metavar="DIR", help="instala en este proyecto (si no, en el directorio de usuario)")
    ap.add_argument("--enlazar", action="store_true", help="symlink/junction en vez de copiar (define EDITORIAL_ROOT)")
    ap.add_argument("--sin-agentes", action="store_true", help="no genera agentes (OpenCode, Cursor)")
    ap.add_argument("--forzar", action="store_true", help="reemplaza skills existentes que no son de esta instalación")
    ap.add_argument("--simular", action="store_true", help="imprime lo que haría sin escribir nada")
    ap.add_argument("--desinstalar", action="store_true", help="quita lo que dejó la instalación")
    ap.add_argument("--generar-toml", action="store_true", help="genera commands/*.toml (extensión de Gemini) desde commands/*.md")
    a = ap.parse_args(argv)
    cli.utf8()
    if a.generar_toml:
        generar_toml(a.simular)
        return 0
    if not a.cli:
        ap.error("falta --cli (o --generar-toml)")
    if a.proyecto and not pathlib.Path(a.proyecto).is_dir():
        cli.error(f"--proyecto: no existe la carpeta {a.proyecto}")
    cfg = CLIS[a.cli]
    if a.cli == "claude":
        mensajes_claude(ROOT.as_posix())
        return 0
    (desinstalar if a.desinstalar else instalar)(a, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
