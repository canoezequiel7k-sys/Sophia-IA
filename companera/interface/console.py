from companera.application.phrases import MOOD_LABELS
from companera.application.companion import CheckInUseCase
from companera.application.ports import MemoryRepository
from companera.domain.models import Mood


def run_companion(use_case: CheckInUseCase, memory: MemoryRepository) -> None:
    print("Sophia IA: Hola. Puedo charlar y ayudarte con Python usando reglas simples.")
    print("Sophia IA: ¿Qué querés programar o resolver hoy? Escribí /ayuda para ver los comandos.")
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
        reply = use_case.respond(answer)
        print(f"Sophia IA ({MOOD_LABELS[Mood(reply.user_mood)]}): {reply.text}")
