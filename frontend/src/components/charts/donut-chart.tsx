'use client';

import { cn } from '@/lib/utils';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface DonutChartProps {
  title?: string;
  description?: string;
  data: { name: string; value: number; color?: string }[];
  colors?: string[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
  showLegend?: boolean;
  centerLabel?: string;
  centerValue?: string | number;
  className?: string;
}

const defaultColors = ['#00f5ff', '#00ff88', '#ff00ff', '#ffff00', '#ff6600', '#9d4edd'];

export function DonutChart({
  title,
  description,
  data,
  colors = defaultColors,
  height = 300,
  innerRadius = 60,
  outerRadius = 80,
  showLegend = true,
  centerLabel,
  centerValue,
  className,
}: DonutChartProps) {
  return (
    <Card className={cn('glass border-border/50', className)}>
      {(title || description) && (
        <CardHeader className="pb-2">
          {title && <CardTitle className="text-base font-medium">{title}</CardTitle>}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent className="pt-0">
        <div style={{ height }} className="relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={innerRadius}
                outerRadius={outerRadius}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color || colors[index % colors.length]}
                    stroke="transparent"
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#12121f',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                }}
                labelStyle={{ color: '#e4e4e7', fontWeight: 500 }}
              />
              {showLegend && (
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ paddingTop: '20px' }}
                  formatter={(value) => (
                    <span style={{ color: '#e4e4e7', fontSize: '12px' }}>{value}</span>
                  )}
                />
              )}
            </PieChart>
          </ResponsiveContainer>

          {/* Center Label */}
          {(centerLabel || centerValue) && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center" style={{ marginBottom: showLegend ? '40px' : '0' }}>
                {centerValue && (
                  <div className="text-2xl font-bold font-mono">{centerValue}</div>
                )}
                {centerLabel && (
                  <div className="text-xs text-muted-foreground">{centerLabel}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
