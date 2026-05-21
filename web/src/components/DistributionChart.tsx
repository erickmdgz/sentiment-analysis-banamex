import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { NPSDistribution } from '@/api/schema';
import { NPS_GROUP_COLOR } from '@/lib/colors';
import { formatInt, formatPct } from '@/lib/format';

interface Props {
  distribution: NPSDistribution;
  height?: number;
}

export function DistributionChart({ distribution, height = 220 }: Props) {
  const data = [
    {
      name: 'Promotor',
      value: distribution.promoters_pct,
      count: distribution.promoters_count,
    },
    {
      name: 'Pasivo',
      value: distribution.passives_pct,
      count: distribution.passives_count,
    },
    {
      name: 'Detractor',
      value: distribution.detractors_pct,
      count: distribution.detractors_count,
    },
  ];

  return (
    <div aria-label="Distribución NPS" role="img" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            isAnimationActive={false}
            label={(entry) => `${entry.name} ${formatPct(entry.value as number)}`}
          >
            {data.map((d) => (
              <Cell key={d.name} fill={NPS_GROUP_COLOR[d.name as 'Promotor' | 'Pasivo' | 'Detractor']} />
            ))}
          </Pie>
          <Tooltip
            formatter={(_value, name) => {
              const item = data.find((d) => d.name === name);
              if (!item) return name;
              return [`${formatPct(item.value)} · ${formatInt(item.count)} respuestas`, name];
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
