type MetricCardProps = {
  title: string;
  value: string | number;
  color?: string;
  icon?: string;
  subtitle?: string;
};

export default function MetricCard({
  title,
  value,
  color = "#49d6a5",
  icon = "📊",
  subtitle,
}: MetricCardProps) {
  return (
    <article
      className="metric-card"
      style={{
        borderTopColor: color,
      }}
    >
      <div className="metric-card-header">
        <span className="metric-card-icon">
          {icon}
        </span>

        <span className="metric-card-title">
          {title}
        </span>
      </div>

      <strong className="metric-card-value">
        {value}
      </strong>

      {subtitle && (
        <span className="metric-card-subtitle">
          {subtitle}
        </span>
      )}
    </article>
  );
}
