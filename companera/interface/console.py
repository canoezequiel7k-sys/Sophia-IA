from companera.application.phrases import MOOD_LABELS
from companera.application.companion import CheckInUseCase
from companera.application.knowledge import (
    KnowledgeEntry,
    RecordInteractionUseCase,
    SearchKnowledgeUseCase,
)
from companera.application.ports import MemoryRepository
from companera.domain.models import Mood
import unicodedata


def _normalize_answer(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def run_companion(
    use_case: CheckInUseCase,
    memory: MemoryRepository,
    knowledge: SearchKnowledgeUseCase,
    record_interaction: RecordInteractionUseCase,
) -> None:
    print("Sophia IA: Hola. Puedo charlar y ayudarte con Python usando reglas simples.")
    print("Sophia IA: También puedo buscar temas en tus apuntes Python (.md). Escribí /ayuda para ver los comandos.")
    pending_context: KnowledgeEntry | None = None
    while True:
        try:
            answer = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSophia IA: Hasta pronto.")
            return
        command = answer.lower()
        if command in {"salir", "adiós", "adios"}:
            print("Sophia IA: Hasta pronto.")
            return
        if command == "/ayuda":
            print("Sophia IA: Comandos: /ayuda, /memoria, /borrar, salir")
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
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nSophia IA: No borré nada.")
                return
            if confirmation in {"sí", "si"}:
                memory.clear()
                print("Sophia IA: Listo, borré mis recuerdos.")
            else:
                print("Sophia IA: No borré nada.")
            continue
        if not answer:
            print("Sophia IA: Cuando quieras, contame cómo estás.")
            continue
        normalized_answer = _normalize_answer(answer).strip(" .!?")
        if pending_context is not None and normalized_answer in {
            "si", "sí", "s", "yes", "claro", "dale", "mostrame", "mostrar"
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

        matches = knowledge.execute(answer)
        if matches:
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
