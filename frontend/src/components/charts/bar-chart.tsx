'use client';

import { cn } from '@/lib/utils';
import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface BarChartProps {
  title?: string;
  description?: string;
  data: Record<string, unknown>[];
  dataKey: string;
  xAxisKey?: string;
  color?: string;
  colors?: string[];
  height?: number;
  showGrid?: boolean;
  showAxis?: boolean;
  horizontal?: boolean;
  className?: string;
}

export function BarChart({
  title,
  description,
  data,
  dataKey,
  xAxisKey = 'name',
  color = '#00f5ff',
  colors,
  height = 300,
  showGrid = true,
  showAxis = true,
  horizontal = false,
  className,
}: BarChartProps) {
  const ChartComponent = horizontal ? (
    <RechartsBarChart data={data} layout="vertical" margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
      {showGrid && (
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(255,255,255,0.05)"
          horizontal={false}
        />
      )}
      {showAxis && (
        <>
          <XAxis
            type="number"
            tick={{ fill: '#71717a', fontSize: 12 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey={xAxisKey}
            tick={{ fill: '#71717a', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={80}
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
        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
      />
      <Bar dataKey={dataKey} radius={[0, 4, 4, 0]}>
        {data.map((_, index) => (
          <Cell
            key={`cell-${index}`}
            fill={colors ? colors[index % colors.length] : color}
          />
        ))}
      </Bar>
    </RechartsBarChart>
  ) : (
    <RechartsBarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
      />
      <Bar dataKey={dataKey} radius={[4, 4, 0, 0]}>
        {data.map((_, index) => (
          <Cell
            key={`cell-${index}`}
            fill={colors ? colors[index % colors.length] : color}
          />
        ))}
      </Bar>
    </RechartsBarChart>
  );

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
            {ChartComponent}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
