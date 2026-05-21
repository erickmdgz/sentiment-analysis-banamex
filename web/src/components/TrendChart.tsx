import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MonthlyTrend } from '@/api/schema';
import { formatMonthLabel } from '@/lib/format';

interface Props {
  trend: MonthlyTrend;
  height?: number;
}

export function TrendChart({ trend, height = 220 }: Props) {
  const data = trend.points.map((p) => ({ ...p, label: p.month }));
  return (
    <div aria-label="Tendencia mensual de NPS" role="img" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 14% 92%)" />
          <XAxis
            dataKey="label"
            interval="preserveStartEnd"
            tick={{ fontSize: 11 }}
            tickFormatter={(value: string) => value.split('-')[1]}
          />
          <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
          <Tooltip
            labelFormatter={(label: string) => formatMonthLabel(label)}
            formatter={(value: number, name: string) => [value.toFixed(1), name === 'nps' ? 'NPS' : name]}
          />
          <Line
            type="monotone"
            dataKey="nps"
            stroke="#dc2626"
            strokeWidth={2}
            isAnimationActive={false}
            dot={{ r: 3, fill: '#dc2626' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
