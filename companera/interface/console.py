from companera.application.companion import CheckInUseCase


def run_companion(use_case: CheckInUseCase) -> None:
    print("Luma: Hola. ¿Cómo estás hoy? (escribí 'salir' para terminar)")
    while True:
        try:
            answer = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nLuma: Hasta pronto.")
            return
        if answer.lower() in {"salir", "adiós", "adios"}:
            print("Luma: Hasta pronto.")
            return
        if not answer:
            print("Luma: Cuando quieras, contame cómo estás.")
            continue
        reply = use_case.respond(answer)
        print(f"Luma: {reply.text}")
