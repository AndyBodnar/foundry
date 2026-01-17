'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import type {
  ExperimentStatus,
  ModelStage,
  DeploymentStatus,
  AlertSeverity,
  DriftStatus,
} from '@/types';

type StatusType = ExperimentStatus | ModelStage | DeploymentStatus | AlertSeverity | DriftStatus;

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
  showDot?: boolean;
  size?: 'sm' | 'default';
}

const statusConfig: Record<StatusType, { label: string; className: string; dotClassName: string }> = {
  // Experiment Status
  RUNNING: {
    label: 'Running',
    className: 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30 hover:bg-neon-cyan/20',
    dotClassName: 'bg-neon-cyan pulse-cyan',
  },
  COMPLETED: {
    label: 'Completed',
    className: 'bg-neon-green/10 text-neon-green border-neon-green/30 hover:bg-neon-green/20',
    dotClassName: 'bg-neon-green',
  },
  FAILED: {
    label: 'Failed',
    className: 'bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/20',
    dotClassName: 'bg-destructive',
  },
  PENDING: {
    label: 'Pending',
    className: 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30 hover:bg-neon-yellow/20',
    dotClassName: 'bg-neon-yellow',
  },
  CANCELLED: {
    label: 'Cancelled',
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
    dotClassName: 'bg-muted-foreground',
  },

  // Model Stage
  NONE: {
    label: 'None',
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
    dotClassName: 'bg-muted-foreground',
  },
  STAGING: {
    label: 'Staging',
    className: 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30 hover:bg-neon-yellow/20',
    dotClassName: 'bg-neon-yellow',
  },
  PRODUCTION: {
    label: 'Production',
    className: 'bg-neon-green/10 text-neon-green border-neon-green/30 hover:bg-neon-green/20',
    dotClassName: 'bg-neon-green pulse-green',
  },
  ARCHIVED: {
    label: 'Archived',
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
    dotClassName: 'bg-muted-foreground',
  },

  // Deployment Status
  DEPLOYING: {
    label: 'Deploying',
    className: 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30 hover:bg-neon-cyan/20',
    dotClassName: 'bg-neon-cyan pulse-cyan',
  },
  STOPPED: {
    label: 'Stopped',
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
    dotClassName: 'bg-muted-foreground',
  },

  // Alert Severity
  P1: {
    label: 'Critical',
    className: 'bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/20',
    dotClassName: 'bg-destructive pulse-cyan',
  },
  P2: {
    label: 'High',
    className: 'bg-neon-orange/10 text-neon-orange border-neon-orange/30 hover:bg-neon-orange/20',
    dotClassName: 'bg-neon-orange',
  },
  P3: {
    label: 'Medium',
    className: 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30 hover:bg-neon-yellow/20',
    dotClassName: 'bg-neon-yellow',
  },
  P4: {
    label: 'Low',
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
    dotClassName: 'bg-muted-foreground',
  },

  // Drift Status
  LOW: {
    label: 'Low',
    className: 'bg-neon-green/10 text-neon-green border-neon-green/30 hover:bg-neon-green/20',
    dotClassName: 'bg-neon-green',
  },
  MEDIUM: {
    label: 'Medium',
    className: 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30 hover:bg-neon-yellow/20',
    dotClassName: 'bg-neon-yellow',
  },
  HIGH: {
    label: 'High',
    className: 'bg-neon-orange/10 text-neon-orange border-neon-orange/30 hover:bg-neon-orange/20',
    dotClassName: 'bg-neon-orange',
  },
  CRITICAL: {
    label: 'Critical',
    className: 'bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/20',
    dotClassName: 'bg-destructive',
  },
};

export function StatusBadge({ status, className, showDot = true, size = 'default' }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge
      variant="outline"
      className={cn(
        config.className,
        size === 'sm' && 'text-[10px] px-1.5 py-0',
        className
      )}
    >
      {showDot && (
        <span className={cn('h-1.5 w-1.5 rounded-full mr-1.5', config.dotClassName)} />
      )}
      {config.label}
    </Badge>
  );
}
