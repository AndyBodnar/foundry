'use client';

import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: LucideIcon;
  iconColor?: 'cyan' | 'magenta' | 'green' | 'yellow' | 'orange' | 'purple';
  className?: string;
}

const iconColors = {
  cyan: 'text-neon-cyan bg-neon-cyan/10',
  magenta: 'text-neon-magenta bg-neon-magenta/10',
  green: 'text-neon-green bg-neon-green/10',
  yellow: 'text-neon-yellow bg-neon-yellow/10',
  orange: 'text-neon-orange bg-neon-orange/10',
  purple: 'text-neon-purple bg-neon-purple/10',
};

export function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  iconColor = 'cyan',
  className,
}: StatCardProps) {
  const getTrendIcon = () => {
    if (change === undefined) return null;
    if (change > 0) return <TrendingUp className="h-3 w-3" />;
    if (change < 0) return <TrendingDown className="h-3 w-3" />;
    return <Minus className="h-3 w-3" />;
  };

  const getTrendColor = () => {
    if (change === undefined) return '';
    if (change > 0) return 'text-neon-green';
    if (change < 0) return 'text-destructive';
    return 'text-muted-foreground';
  };

  return (
    <Card className={cn('glass border-border/50 hover:border-primary/30 transition-all duration-300', className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold font-mono tracking-tight">{value}</p>
            {(change !== undefined || changeLabel) && (
              <div className={cn('flex items-center gap-1 text-xs', getTrendColor())}>
                {getTrendIcon()}
                <span>
                  {change !== undefined && `${change > 0 ? '+' : ''}${change}%`}
                  {changeLabel && ` ${changeLabel}`}
                </span>
              </div>
            )}
          </div>
          {Icon && (
            <div className={cn('p-3 rounded-lg', iconColors[iconColor])}>
              <Icon className="h-5 w-5" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
