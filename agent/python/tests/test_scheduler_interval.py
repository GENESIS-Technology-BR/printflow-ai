from core.scheduler import AgentScheduler


class Logger:
    def info(self, *args):
        pass

    def exception(self, *args):
        pass


def test_scheduler_keeps_five_minute_interval() -> None:
    scheduler = AgentScheduler(300, Logger())
    assert scheduler.interval_seconds == 300


def test_scheduler_never_accepts_dangerously_short_interval() -> None:
    scheduler = AgentScheduler(5, Logger())
    assert scheduler.interval_seconds == 30
