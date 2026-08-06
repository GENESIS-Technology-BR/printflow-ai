type HealthGaugeProps = {
  value: number;
};

function getHealthLabel(value: number): string {
  if (value >= 85) {
    return "Excelente";
  }

  if (value >= 70) {
    return "Boa";
  }

  if (value >= 50) {
    return "Atenção";
  }

  return "Crítica";
}

function getHealthColor(value: number): string {
  if (value >= 85) {
    return "#49d6a5";
  }

  if (value >= 70) {
    return "#5ba8ff";
  }

  if (value >= 50) {
    return "#ffbe55";
  }

  return "#ff647c";
}

export default function HealthGauge({
  value,
}: HealthGaugeProps) {
  const safeValue = Math.max(
    0,
    Math.min(value, 100),
  );

  const color = getHealthColor(safeValue);

  return (
    <article className="health-panel">
      <div>
        <span className="health-eyebrow">
          Saúde geral do parque
        </span>

        <h3>
          {getHealthLabel(safeValue)}
        </h3>

        <p>
          Indicador calculado com disponibilidade,
          comunicação e condição dos equipamentos.
        </p>
      </div>

      <div
        className="health-gauge"
        style={{
          background: `conic-gradient(
            ${color} ${safeValue * 3.6}deg,
            #263248 0deg
          )`,
        }}
      >
        <div className="health-gauge-center">
          <strong>{safeValue}%</strong>
          <span>Health Score</span>
        </div>
      </div>
    </article>
  );
}
