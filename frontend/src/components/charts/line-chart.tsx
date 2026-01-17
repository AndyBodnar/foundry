'use client';

import { cn } from '@/lib/utils';
import {
  Line,
  LineChart as RechartsLineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface LineConfig {
  dataKey: string;
  name?: string;
  color: string;
  dashed?: boolean;
}

interface LineChartProps {
  title?: string;
  description?: string;
  data: Record<string, unknown>[];
  lines: LineConfig[];
  xAxisKey?: string;
  height?: number;
  showGrid?: boolean;
  showAxis?: boolean;
  showLegend?: boolean;
  className?: string;
}

export function LineChart({
  title,
  description,
  data,
  lines,
  xAxisKey = 'name',
  height = 300,
  showGrid = true,
  showAxis = true,
  showLegend = false,
  className,
}: LineChartProps) {
  return (
    <Card className={cn('glass border-border/50', className)}>
      {(title || description) && (
        <CardHeader className="pb-2">
          {title && <CardTitle className="text-base font-medium">{title}</CardTitle>}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent className="pt-0">
        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <RechartsLineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              {showGrid && (
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  vertical={false}
                />
              )}
              {showAxis && (
                <>
                  <XAxis
                    dataKey={xAxisKey}
                    tick={{ fill: '#71717a', fontSize: 12 }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#71717a', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                </>
              )}
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
                  wrapperStyle={{ paddingTop: '10px' }}
                  iconType="line"
                />
              )}
              {lines.map((line) => (
                <Line
                  key={line.dataKey}
                  type="monotone"
                  dataKey={line.dataKey}
                  name={line.name || line.dataKey}
                  stroke={line.color}
                  strokeWidth={2}
                  strokeDasharray={line.dashed ? '5 5' : undefined}
                  dot={false}
                  activeDot={{ r: 4, fill: line.color }}
                />
              ))}
            </RechartsLineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
