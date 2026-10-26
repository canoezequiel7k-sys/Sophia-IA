from datetime import datetime


class SystemClock:
    """Adaptador que usa el reloj local del equipo."""

    def now(self) -> datetime:
        """Devuelve la fecha actual con su zona horaria."""
        return datetime.now().astimezone()
