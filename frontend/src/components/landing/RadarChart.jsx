import { riskDimensions } from "../../data/riskDimensions.js";

const radarSize = 420;
const radarCenter = radarSize / 2;
const radarRadius = 128;

function radarPoint(index, value = 10) {
  const angle = (Math.PI * 2 * index) / riskDimensions.length - Math.PI / 2;
  const radius = (value / 10) * radarRadius;

  return {
    x: radarCenter + Math.cos(angle) * radius,
    y: radarCenter + Math.sin(angle) * radius,
  };
}

const radarPolygonPoints = riskDimensions
  .map((dimension, index) => {
    const point = radarPoint(index, dimension.score);
    return `${point.x},${point.y}`;
  })
  .join(" ");

const radarOverallScore = Math.round(
  (riskDimensions.reduce((total, dimension) => total + dimension.score, 0) / riskDimensions.length) * 10,
);

function radarRingPoints(level) {
  return riskDimensions
    .map((_, index) => {
      const point = radarPoint(index, level);
      return `${point.x},${point.y}`;
    })
    .join(" ");
}

function radarTextAnchor(point) {
  if (Math.abs(point.x - radarCenter) < 12) {
    return "middle";
  }

  return point.x < radarCenter ? "end" : "start";
}

export function RadarChart() {
  return (
    <div className="radar-chart">
      <svg viewBox={`0 0 ${radarSize} ${radarSize}`} role="img" aria-label="Radar chart of OllyUW sample scores">
        {[2, 4, 6, 8, 10].map((level) => (
          <polygon className="radar-ring" points={radarRingPoints(level)} key={level} />
        ))}
        {riskDimensions.map((dimension, index) => {
          const edge = radarPoint(index, 10);

          return (
            <line
              className="radar-axis"
              x1={radarCenter}
              y1={radarCenter}
              x2={edge.x}
              y2={edge.y}
              key={dimension.code}
            />
          );
        })}
        <polygon className="radar-area" points={radarPolygonPoints} />
        {riskDimensions.map((dimension, index) => {
          const point = radarPoint(index, dimension.score);

          return <circle className="radar-dot" cx={point.x} cy={point.y} r="4.5" key={dimension.code} />;
        })}
        {riskDimensions.map((dimension, index) => {
          const labelPoint = radarPoint(index, 12.2);

          return (
            <text
              className="radar-label"
              x={labelPoint.x}
              y={labelPoint.y}
              textAnchor={radarTextAnchor(labelPoint)}
              dominantBaseline="middle"
              key={dimension.code}
            >
              <tspan className="radar-label-code">{dimension.code}</tspan>
              <tspan className="radar-label-score"> {dimension.score.toFixed(1)}</tspan>
              <tspan x={labelPoint.x} dy="15">
                {dimension.label}
              </tspan>
            </text>
          );
        })}
        <text className="radar-center-label" x={radarCenter} y={radarCenter - 6} textAnchor="middle">
          Risk
        </text>
        <text className="radar-center-score" x={radarCenter} y={radarCenter + 24} textAnchor="middle">
          {radarOverallScore}
        </text>
      </svg>
    </div>
  );
}
