from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable


SEVERITY_WEIGHT = {
    "critical": 4,
    "warning": 3,
    "opportunity": 2,
    "info": 1,
}


def _printer_name(printer: dict[str, Any]) -> str:
    return (
        printer.get("custom_name")
        or printer.get("hostname")
        or printer.get("name")
        or printer.get("ip")
        or "Impressora"
    )


def _finding(
    *,
    finding_id: str,
    category: str,
    severity: str,
    title: str,
    problem: str,
    impact: str,
    recommendation: str,
    printer: dict[str, Any] | None = None,
    confidence: float = 0.9,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "category": category,
        "severity": severity,
        "title": title,
        "problem": problem,
        "impact": impact,
        "recommendation": recommendation,
        "printer_uuid": printer.get("uuid") if printer else None,
        "printer_name": _printer_name(printer) if printer else None,
        "unit_name": printer.get("unit_name") if printer else None,
        "sector_name": printer.get("sector_name") if printer else None,
        "confidence": round(max(0.0, min(float(confidence), 1.0)), 2),
        "evidence": evidence or {},
    }


def build_intelligence(
    printers: Iterable[dict[str, Any]],
    history: Iterable[Any],
    *,
    today: date | None = None,
    now: datetime | None = None,
    max_findings: int = 10,
) -> dict[str, Any]:
    current_date = today or date.today()
    current_time = now or datetime.now(timezone.utc)
    printer_list = [printer for printer in printers if printer.get("active", True)]
    printer_map = {
        printer.get("uuid"): printer
        for printer in printer_list
        if printer.get("uuid")
    }

    usage_by_printer: dict[str, list[Any]] = defaultdict(list)
    for row in history:
        usage_by_printer[getattr(row, "printer_uuid", "")].append(row)

    findings: list[dict[str, Any]] = []

    for printer in printer_list:
        printer_uuid = printer.get("uuid") or str(printer.get("id") or "unknown")
        name = _printer_name(printer)
        status = str(printer.get("status") or "unknown").lower()
        health_score = int(printer.get("health_score") or 0)

        if status == "offline":
            findings.append(
                _finding(
                    finding_id=f"offline:{printer_uuid}",
                    category="availability",
                    severity="critical",
                    title=f"{name} está offline",
                    problem="O equipamento está sem comunicação com o Printflow.",
                    impact="Pode interromper o atendimento do setor e ocultar novas leituras de contador.",
                    recommendation="Validar energia, rede e acesso SNMP. Se o equipamento foi retirado, marque-o como inativo.",
                    printer=printer,
                    confidence=0.99,
                    evidence={"status": status, "health_score": health_score},
                )
            )
        elif health_score < 70:
            reasons = printer.get("health_reasons") or []
            findings.append(
                _finding(
                    finding_id=f"health:{printer_uuid}",
                    category="health",
                    severity="warning",
                    title=f"{name} requer atenção",
                    problem="A saúde operacional do equipamento caiu abaixo do nível recomendado.",
                    impact="Há maior risco de indisponibilidade ou perda de qualidade no monitoramento.",
                    recommendation="Revisar os motivos de saúde e priorizar uma verificação preventiva.",
                    printer=printer,
                    confidence=0.9,
                    evidence={"health_score": health_score, "reasons": reasons[:3]},
                )
            )

        last_seen_text = printer.get("last_seen")
        if last_seen_text and status != "offline":
            try:
                last_seen = datetime.fromisoformat(str(last_seen_text).replace("Z", "+00:00"))
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                age_hours = max((current_time - last_seen).total_seconds() / 3600, 0)
                if age_hours >= 6:
                    severity = "critical" if age_hours >= 24 else "warning"
                    findings.append(
                        _finding(
                            finding_id=f"stale:{printer_uuid}",
                            category="communication",
                            severity=severity,
                            title=f"Coleta atrasada em {name}",
                            problem=f"A última comunicação ocorreu há aproximadamente {age_hours:.0f} horas.",
                            impact="Os dados exibidos podem não representar a situação atual do equipamento.",
                            recommendation="Validar o Agent, conectividade com a impressora e disponibilidade da rede local.",
                            printer=printer,
                            confidence=0.97,
                            evidence={"hours_without_contact": round(age_hours, 1)},
                        )
                    )
            except (TypeError, ValueError):
                pass

    for printer_uuid, usage_rows in usage_by_printer.items():
        printer = printer_map.get(printer_uuid)
        if not printer:
            continue

        rows = sorted(usage_rows, key=lambda row: getattr(row, "usage_date"))
        recent_14 = [
            row for row in rows
            if getattr(row, "usage_date") >= current_date - timedelta(days=13)
        ]
        anomalies = sum(max(int(getattr(row, "anomaly_count", 0) or 0), 0) for row in recent_14)
        if anomalies:
            findings.append(
                _finding(
                    finding_id=f"counter-anomaly:{printer_uuid}",
                    category="counter",
                    severity="warning",
                    title=f"Anomalia de contador em {_printer_name(printer)}",
                    problem=f"Foram identificadas {anomalies} ocorrência(s) de contador inconsistente nos últimos 14 dias.",
                    impact="Relatórios de volume e custo podem ficar imprecisos se a origem não for confirmada.",
                    recommendation="Conferir o contador físico e validar o OID utilizado para este fabricante/modelo.",
                    printer=printer,
                    confidence=0.96,
                    evidence={"anomaly_count_14d": anomalies},
                )
            )

        daily = {
            getattr(row, "usage_date"): max(int(getattr(row, "pages_printed", 0) or 0), 0)
            for row in recent_14
        }
        observed_days = len(daily)
        total_14 = sum(daily.values())

        if observed_days >= 7 and total_14 <= 50:
            findings.append(
                _finding(
                    finding_id=f"underused:{printer_uuid}",
                    category="optimization",
                    severity="opportunity",
                    title=f"Possível subutilização: {_printer_name(printer)}",
                    problem=f"O equipamento registrou apenas {total_14} página(s) em {observed_days} dias com histórico recente.",
                    impact="Pode existir custo fixo, manutenção e espaço dedicados a um equipamento pouco utilizado.",
                    recommendation="Avaliar consolidação com outra impressora do mesmo setor antes de renovar ou substituir o equipamento.",
                    printer=printer,
                    confidence=0.74,
                    evidence={"pages_14d": total_14, "observed_days": observed_days},
                )
            )

        if observed_days >= 8:
            dates = sorted(daily)
            recent_dates = dates[-3:]
            baseline_dates = dates[:-3][-7:]
            if len(recent_dates) >= 2 and len(baseline_dates) >= 4:
                recent_avg = sum(daily[item] for item in recent_dates) / len(recent_dates)
                baseline_avg = sum(daily[item] for item in baseline_dates) / len(baseline_dates)
                if baseline_avg >= 10 and recent_avg >= max(50, baseline_avg * 1.5):
                    growth = ((recent_avg / baseline_avg) - 1) * 100
                    findings.append(
                        _finding(
                            finding_id=f"volume-spike:{printer_uuid}",
                            category="usage",
                            severity="warning",
                            title=f"Aumento de volume em {_printer_name(printer)}",
                            problem=f"A média recente subiu aproximadamente {growth:.0f}% em relação ao padrão anterior.",
                            impact="O crescimento pode antecipar consumo de toner, manutenção e custo do equipamento.",
                            recommendation="Confirmar se o aumento é esperado pelo setor e acompanhar custo e consumíveis nos próximos dias.",
                            printer=printer,
                            confidence=0.82,
                            evidence={
                                "recent_daily_average": round(recent_avg, 1),
                                "baseline_daily_average": round(baseline_avg, 1),
                                "growth_percent": round(growth, 1),
                            },
                        )
                    )

    findings.sort(
        key=lambda item: (
            -SEVERITY_WEIGHT.get(item["severity"], 0),
            -item["confidence"],
            item["title"],
        )
    )
    findings = findings[:max_findings]

    counts = {
        level: sum(1 for item in findings if item["severity"] == level)
        for level in ("critical", "warning", "opportunity", "info")
    }
    attention_count = counts["critical"] + counts["warning"]

    if counts["critical"]:
        headline = f"{counts['critical']} item(ns) crítico(s) exigem ação imediata."
    elif counts["warning"]:
        headline = f"{counts['warning']} ponto(s) precisam de atenção hoje."
    elif counts["opportunity"]:
        headline = f"Ambiente estável, com {counts['opportunity']} oportunidade(s) de otimização."
    else:
        headline = "Nenhum desvio relevante identificado no momento."

    score = max(
        0,
        100
        - counts["critical"] * 18
        - counts["warning"] * 8
        - counts["opportunity"] * 2,
    )

    return {
        "engine": "rules-v1",
        "generated_at": current_time.isoformat(),
        "score": score,
        "headline": headline,
        "attention_count": attention_count,
        "counts": counts,
        "findings": findings,
        "analysis_window_days": 14,
    }
