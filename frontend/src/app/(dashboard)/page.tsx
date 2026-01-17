'use client';

import {
  FlaskConical,
  Box,
  Rocket,
  AlertTriangle,
  Zap,
  Clock,
  Activity,
  ArrowUpRight,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatCard } from '@/components/shared/stat-card';
import { StatusBadge } from '@/components/shared/status-badge';
import { AreaChart } from '@/components/charts/area-chart';
import { DonutChart } from '@/components/charts/donut-chart';
import { cn } from '@/lib/utils';
import Link from 'next/link';

// Data placeholders - connect to API for real data
const stats = {
  experiments: 0,
  experimentsDelta: 0,
  models: 0,
  modelsDelta: 0,
  deployments: 0,
  deploymentsDelta: 0,
  alerts: 0,
  alertsDelta: 0,
};

const inferenceData: { time: string; requests: number }[] = [];

const modelDistribution: { name: string; value: number; color: string }[] = [];

const recentActivity: {
  id: string;
  type: 'MODEL_DEPLOYED' | 'ALERT_TRIGGERED' | 'RUN_COMPLETED' | 'DRIFT_DETECTED' | 'MODEL_REGISTERED';
  title: string;
  description: string;
  time: string;
  status: string;
}[] = [];

const activeDeployments: {
  id: string;
  name: string;
  model: string;
  status: 'RUNNING' | 'STOPPED' | 'FAILED';
  replicas: { ready: number; total: number };
  latencyP99: number;
  requestsPerSec: number;
}[] = [];

function getActivityIcon(type: string) {
  switch (type) {
    case 'MODEL_DEPLOYED':
      return <Rocket className="h-4 w-4" />;
    case 'ALERT_TRIGGERED':
      return <AlertTriangle className="h-4 w-4" />;
    case 'RUN_COMPLETED':
      return <FlaskConical className="h-4 w-4" />;
    case 'DRIFT_DETECTED':
      return <Activity className="h-4 w-4" />;
    case 'MODEL_REGISTERED':
      return <Box className="h-4 w-4" />;
    default:
      return <Zap className="h-4 w-4" />;
  }
}

function getActivityColor(status: string) {
  switch (status) {
    case 'success':
      return 'text-neon-green bg-neon-green/10';
    case 'warning':
      return 'text-neon-orange bg-neon-orange/10';
    case 'error':
      return 'text-destructive bg-destructive/10';
    default:
      return 'text-neon-cyan bg-neon-cyan/10';
  }
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight font-display">
            Welcome back
          </h1>
          <p className="text-muted-foreground mt-1">
            Here&apos;s what&apos;s happening with your ML operations today.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" asChild>
            <Link href="/experiments">
              View Experiments
              <ArrowUpRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild>
            <Link href="/deployments">
              <Rocket className="mr-2 h-4 w-4" />
              Deploy Model
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Experiments"
          value={stats.experiments}
          change={stats.experimentsDelta}
          changeLabel="vs last month"
          icon={FlaskConical}
          iconColor="cyan"
        />
        <StatCard
          title="Registered Models"
          value={stats.models}
          change={stats.modelsDelta}
          changeLabel="vs last month"
          icon={Box}
          iconColor="purple"
        />
        <StatCard
          title="Active Deployments"
          value={stats.deployments}
          change={stats.deploymentsDelta}
          changeLabel="vs last month"
          icon={Rocket}
          iconColor="green"
        />
        <StatCard
          title="Active Alerts"
          value={stats.alerts}
          change={stats.alertsDelta}
          changeLabel="vs last week"
          icon={AlertTriangle}
          iconColor="orange"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <AreaChart
            title="Inference Requests"
            description="Request volume over the last 24 hours"
            data={inferenceData}
            dataKey="requests"
            xAxisKey="time"
            color="#00f5ff"
            height={280}
          />
        </div>
        <DonutChart
          title="Models by Stage"
          description="Distribution across environments"
          data={modelDistribution}
          height={280}
          innerRadius={50}
          outerRadius={70}
          centerValue={23}
          centerLabel="Total Models"
        />
      </div>

      {/* Activity and Deployments */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-medium">Recent Activity</CardTitle>
              <Button variant="ghost" size="sm" className="text-xs" asChild>
                <Link href="/monitoring?tab=activity">
                  View all
                  <ChevronRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  <div
                    className={cn(
                      'p-2 rounded-lg flex-shrink-0',
                      getActivityColor(activity.status)
                    )}
                  >
                    {getActivityIcon(activity.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{activity.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {activity.description}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground flex-shrink-0">
                    <Clock className="h-3 w-3" />
                    {activity.time}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Active Deployments */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-medium">Active Deployments</CardTitle>
              <Button variant="ghost" size="sm" className="text-xs" asChild>
                <Link href="/deployments">
                  View all
                  <ChevronRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3">
              {activeDeployments.map((deployment) => (
                <div
                  key={deployment.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-neon-green/10 flex items-center justify-center">
                      <Rocket className="h-5 w-5 text-neon-green" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{deployment.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {deployment.model}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-mono">
                        {deployment.requestsPerSec.toLocaleString()}
                        <span className="text-xs text-muted-foreground ml-1">req/s</span>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        p99: {deployment.latencyP99}ms
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusBadge status={deployment.status} size="sm" />
                      <span className="text-xs text-muted-foreground">
                        {deployment.replicas.ready}/{deployment.replicas.total} replicas
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Quick Actions</CardTitle>
          <CardDescription>Common tasks to get started</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col items-center gap-2 hover:border-primary/50 hover:bg-primary/5"
              asChild
            >
              <Link href="/experiments?new=true">
                <FlaskConical className="h-5 w-5 text-neon-cyan" />
                <span>New Experiment</span>
              </Link>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col items-center gap-2 hover:border-primary/50 hover:bg-primary/5"
              asChild
            >
              <Link href="/models?new=true">
                <Box className="h-5 w-5 text-neon-purple" />
                <span>Register Model</span>
              </Link>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col items-center gap-2 hover:border-primary/50 hover:bg-primary/5"
              asChild
            >
              <Link href="/deployments?new=true">
                <Rocket className="h-5 w-5 text-neon-green" />
                <span>Create Deployment</span>
              </Link>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col items-center gap-2 hover:border-primary/50 hover:bg-primary/5"
              asChild
            >
              <Link href="/monitoring?tab=alerts">
                <Activity className="h-5 w-5 text-neon-orange" />
                <span>View Alerts</span>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
