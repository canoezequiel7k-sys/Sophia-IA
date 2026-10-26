import os
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from companera.application.phrases import MOOD_LABELS
from companera.application.companion import CheckInUseCase
from companera.application.knowledge import (
    KnowledgeEntry,
    RecordInteractionUseCase,
    SearchKnowledgeUseCase,
)
from companera.application.ports import MemoryRepository
from companera.domain.models import Mood


def _normalize_answer(text: str) -> str:
    """Compara texto sin distinguir mayúsculas ni tildes."""
    normalized = unicodedata.normalize("NFD", text.casefold().strip())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _open_windows_terminal(start_sophia: bool = False) -> bool:
    """Abre Windows Terminal, opcionalmente iniciando otra sesión de Sophia."""
    terminal = shutil.which("wt.exe") or shutil.which("wt")
    if terminal is None:
        return False
    command = [terminal, "-w", "new"]
    if start_sophia:
        main_script = Path(__file__).resolve().parents[2] / "main.py"
        command.extend([sys.executable, str(main_script)])
    subprocess.Popen(command, shell=False)
    return True


def _clear_terminal() -> None:
    """Limpia la pantalla sin tocar la memoria ni los archivos."""
    if os.name == "nt":
        os.system("cls")
    else:
        print("\033[2J\033[H", end="", flush=True)
    print("\033[93mclear\033[0m — terminal limpia.")


def run_companion(
    use_case: CheckInUseCase,
    memory: MemoryRepository,
    knowledge: SearchKnowledgeUseCase,
    record_interaction: RecordInteractionUseCase,
) -> None:
    """Mantiene la charla y atiende comandos desde la terminal."""
    print("Sophia IA: Hola. Puedo charlar y ayudarte con Python usando reglas simples.")
    print("Sophia IA: Escribí 'sop -help' para ver los comandos.")
    pending_context: KnowledgeEntry | None = None
    while True:
        try:
            answer = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSophia IA: Hasta pronto.")
            return
        command = _normalize_answer(answer).strip(" .!?")
        if command in {
            "salir", "adios", "chau", "chao", "cierrate", "cerrate",
            "cerrar", "cierra", "apagate", "sop -close", "sop --close",
        }:
            print("Sophia IA: Hasta pronto.")
            return
        if command in {"/ayuda", "sop -help", "sop --help", "help"}:
            print("Sophia IA: Comandos básicos:")
            print("  sop -help       mostrar esta ayuda")
            print("  clear           limpiar la terminal (no borra la memoria)")
            print("  sop -close      cerrar Sophia")
            print("  sop -new        abrir otra terminal con Sophia")
            print("  sop -terminal   abrir una terminal de Windows")
            print("  /memoria        consultar los recuerdos")
            print("  /borrar         borrar recuerdos con confirmación")
            print("También podés escribir 'salir' o 'ciérrate' para cerrar.")
            continue
        if command in {"clear", "cls", "limpiar", "limpia la terminal"}:
            _clear_terminal()
            continue
        if command == "/memoria":
            records = memory.history()
            if not records:
                print("Sophia IA: Todavía no tengo recuerdos guardados.")
            else:
                print(f"Sophia IA: Recuerdo {len(records)} conversaciones:")
                for record in records:
                    print(f"  Vos ({record.created_at:%d/%m/%Y %H:%M}): {record.text}")
                    if record.reply:
                        print(f"  Sophia IA: {record.reply}")
            continue
        if command == "/borrar":
            try:
                confirmation = input(
                    "Sophia IA: ¿Borro toda la memoria? Escribí 'sí' para confirmar: "
                )
            except (EOFError, KeyboardInterrupt):
                print("\nSophia IA: No borré nada.")
                return
            if _normalize_answer(confirmation) in {"si", "s"}:
                memory.clear()
                print("Sophia IA: Listo, borré mis recuerdos.")
            else:
                print("Sophia IA: No borré nada.")
            continue
        if not answer:
            print("Sophia IA: Cuando quieras, contame cómo estás.")
            continue
        normalized_answer = command
        # Si ofrecimos una nota, esperamos aquí la respuesta sí/no.
        if pending_context is not None and normalized_answer in {
            "si", "s", "yes", "claro", "dale", "mostrame", "mostrar"
        }:
            print(f"\n{pending_context.content}\n")
            record_interaction.execute(
                f"Sí, mostrar {pending_context.title}",
                pending_context.content,
            )
            pending_context = None
            continue
        if pending_context is not None and normalized_answer in {
            "no", "ahora no", "despues", "luego"
        }:
            print("Sophia IA: Está bien. ¿Qué otro tema querés buscar?")
            record_interaction.execute(
                f"No mostrar {pending_context.title}",
                "Se ofreció el contexto completo y el usuario prefirió no verlo.",
            )
            pending_context = None
            continue

        if command in {
            "sop -new", "sop --new", "abre una terminal de sophia",
            "abrir otra terminal de sophia", "abrime otra terminal de sophia",
        }:
            try:
                if _open_windows_terminal(start_sophia=True):
                    reply = "Listo, abrí otra terminal con Sophia IA."
                else:
                    reply = "No encontré Windows Terminal para abrir otra sesión."
            except OSError as error:
                reply = f"No pude abrir otra sesión de Sophia: {error}"
            print(f"Sophia IA: {reply}")
            record_interaction.execute(answer, reply)
            continue

        if command in {
            "sop -terminal", "sop --terminal", "abre una terminal",
            "abrime una terminal", "abrir terminal", "abre windows terminal",
            "abrime windows terminal", "abrir windows terminal",
        }:
            try:
                if _open_windows_terminal():
                    reply = "Listo, abrí una terminal nueva de Windows."
                else:
                    reply = "No encontré Windows Terminal. Revisá que esté instalado."
            except OSError as error:
                reply = f"No pude abrir Windows Terminal: {error}"
            print(f"Sophia IA: {reply} ¿Necesitás algo más?")
            record_interaction.execute(answer, reply)
            continue

        if command in {"gracias", "muchas gracias", "gracias sophia", "te agradezco"}:
            reply = "¡De nada! ¿Necesitás algo más?"
            print(f"Sophia IA: {reply}")
            record_interaction.execute(answer, reply)
            continue

        if command in {
            "no", "nada", "nada mas", "no necesito nada",
            "no necesito nada mas", "no gracias", "eso es todo",
        }:
            print("Sophia IA: Está bien. Hasta pronto.")
            record_interaction.execute(answer, "La persona indicó que no necesitaba más ayuda.")
            return

        if command in {"si", "s", "yes", "claro", "necesito algo mas"}:
            reply = "Claro, decime qué necesitás."
            print(f"Sophia IA: {reply}")
            record_interaction.execute(answer, reply)
            continue

        if command in {"hola", "buenas", "buen dia", "buenas tardes", "buenas noches"}:
            reply = "¡Hola! ¿Qué necesitás?"
            print(f"Sophia IA: {reply}")
            record_interaction.execute(answer, reply)
            continue

        matches = knowledge.execute(answer)
        if matches:
            # Primero damos un resumen; el contenido completo queda a elección.
            selected = matches[0]
            print(f"Sophia IA: Encontré «{selected.title}» en {selected.source}.")
            print(f"Sophia IA: {selected.summary}")
            prompt = (
                f"Encontré «{selected.title}»: {selected.summary} "
                f"¿Querés que te muestre el contexto completo? (sí/no)"
            )
            record_interaction.execute(answer, prompt)
            if len(matches) > 1:
                alternatives = ", ".join(entry.title for entry in matches[1:4])
                print(f"Sophia IA: También aparece relacionado con: {alternatives}.")
            print(f"Sophia IA: ¿Querés que te muestre el contexto completo de «{selected.title}»? (sí/no)")
            pending_context = selected
            continue
        reply = use_case.respond(answer)
        print(f"Sophia IA ({MOOD_LABELS[Mood(reply.user_mood)]}): {reply.text}")
