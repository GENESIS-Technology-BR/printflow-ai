from __future__ import annotations

import logging
import signal
import time
from collections.abc import Callable


class AgentScheduler:
    def __init__(
        self,
        interval_seconds: int,
        logger: logging.Logger,
    ) -> None:
        self.interval_seconds = max(
            interval_seconds,
            30,
        )
        self.logger = logger
        self.running = True

        signal.signal(
            signal.SIGINT,
            self._stop,
        )

        signal.signal(
            signal.SIGTERM,
            self._stop,
        )

    def _stop(
        self,
        signum: int,
        frame: object,
    ) -> None:
        del signum
        del frame

        self.running = False

        self.logger.info(
            "Solicitação de encerramento recebida."
        )

    def run(
        self,
        task: Callable[[], int],
    ) -> int:
        while self.running:
            started_at = time.monotonic()

            try:
                task()
            except Exception:
                self.logger.exception(
                    "Falha inesperada durante o ciclo."
                )

            if not self.running:
                break

            elapsed = time.monotonic() - started_at

            wait_seconds = max(
                self.interval_seconds - int(elapsed),
                1,
            )

            self.logger.info(
                "Próximo ciclo em %s segundos.",
                wait_seconds,
            )

            for _ in range(wait_seconds):
                if not self.running:
                    break

                time.sleep(1)

        self.logger.info(
            "Scheduler encerrado."
        )

        return 0
