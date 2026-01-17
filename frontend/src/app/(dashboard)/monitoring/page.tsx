'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Activity,
  TrendingUp,
  TrendingDown,
  Bell,
  CheckCircle,
  Clock,
  RefreshCw,
  Eye,
  Settings,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/shared/page-header';
import { StatusBadge } from '@/components/shared/status-badge';
import { LineChart } from '@/components/charts/line-chart';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Alert, DriftStatus, AlertSeverity } from '@/types';

// Data placeholders - connect to API for real data
const alerts: Alert[] = [];
const driftData: { time: string; fraud_detector: number; churn_predictor: number; recommendation: number }[] = [];
const featureDrift: { name: string; score: number; status: DriftStatus }[] = [];
const performanceData: { time: string; accuracy: number; precision: number; recall: number }[] = [];

function getSeverityColor(severity: AlertSeverity) {
  switch (severity) {
    case 'P1':
      return 'bg-destructive/10 text-destructive border-destructive/30';
    case 'P2':
      return 'bg-neon-orange/10 text-neon-orange border-neon-orange/30';
    case 'P3':
      return 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30';
    case 'P4':
      return 'bg-muted text-muted-foreground border-border';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

function getDriftColor(status: DriftStatus) {
  switch (status) {
    case 'CRITICAL':
      return 'bg-destructive';
    case 'HIGH':
      return 'bg-neon-orange';
    case 'MEDIUM':
      return 'bg-neon-yellow';
    case 'LOW':
      return 'bg-neon-green';
    default:
      return 'bg-muted-foreground';
  }
}

export default function MonitoringPage() {
  const [selectedTab, setSelectedTab] = useState('alerts');
  const [selectedDeployment, setSelectedDeployment] = useState('all');

  const activeAlerts = alerts.filter((a) => a.status === 'ACTIVE').length;
  const acknowledgedAlerts = alerts.filter((a) => a.status === 'ACKNOWLEDGED').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitoring"
        description="Track model performance, drift, and system health"
      >
        <Select value={selectedDeployment} onValueChange={setSelectedDeployment}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Select deployment" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Deployments</SelectItem>
            <SelectItem value="fraud-detector">fraud-detector</SelectItem>
            <SelectItem value="churn-predictor">churn-predictor</SelectItem>
            <SelectItem value="recommendation-engine">recommendation-engine</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </PageHeader>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass border-border/50 border-l-4 border-l-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">{activeAlerts}</div>
                <p className="text-xs text-muted-foreground">Active Alerts</p>
              </div>
              <div className="p-3 rounded-lg bg-destructive/10">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">{acknowledgedAlerts}</div>
                <p className="text-xs text-muted-foreground">Acknowledged</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-yellow/10">
                <Bell className="h-5 w-5 text-neon-yellow" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono text-neon-orange">0.18</div>
                <p className="text-xs text-muted-foreground">Max Drift Score</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-orange/10">
                <TrendingUp className="h-5 w-5 text-neon-orange" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono text-neon-green">93.2%</div>
                <p className="text-xs text-muted-foreground">Model Accuracy</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-green/10">
                <Activity className="h-5 w-5 text-neon-green" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="alerts" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            Alerts
            {activeAlerts > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 px-1.5">
                {activeAlerts}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="drift">
            <TrendingUp className="mr-2 h-4 w-4" />
            Data Drift
          </TabsTrigger>
          <TabsTrigger value="performance">
            <Activity className="mr-2 h-4 w-4" />
            Performance
          </TabsTrigger>
        </TabsList>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="mt-6">
          <div className="space-y-4">
            {alerts.map((alert) => (
              <Card
                key={alert.id}
                className={cn(
                  'glass border-border/50',
                  alert.status === 'ACTIVE' && 'border-l-4',
                  alert.status === 'ACTIVE' && alert.severity === 'P1' && 'border-l-destructive',
                  alert.status === 'ACTIVE' && alert.severity === 'P2' && 'border-l-neon-orange',
                  alert.status === 'ACTIVE' && alert.severity === 'P3' && 'border-l-neon-yellow'
                )}
              >
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div
                        className={cn(
                          'p-2 rounded-lg',
                          alert.status === 'RESOLVED'
                            ? 'bg-neon-green/10 text-neon-green'
                            : getSeverityColor(alert.severity)
                        )}
                      >
                        {alert.status === 'RESOLVED' ? (
                          <CheckCircle className="h-5 w-5" />
                        ) : (
                          <AlertTriangle className="h-5 w-5" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{alert.title}</h4>
                          <StatusBadge status={alert.severity} size="sm" showDot={false} />
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-xs',
                              alert.status === 'ACTIVE' && 'border-destructive/30 text-destructive',
                              alert.status === 'ACKNOWLEDGED' && 'border-neon-yellow/30 text-neon-yellow',
                              alert.status === 'RESOLVED' && 'border-neon-green/30 text-neon-green'
                            )}
                          >
                            {alert.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {alert.message}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Triggered {format(new Date(alert.triggeredAt), 'MMM d, HH:mm')}
                          </span>
                          {alert.acknowledgedBy && (
                            <span>Acknowledged by {alert.acknowledgedBy}</span>
                          )}
                          {alert.resolvedAt && (
                            <span>Resolved {format(new Date(alert.resolvedAt), 'MMM d, HH:mm')}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {alert.status === 'ACTIVE' && (
                        <>
                          <Button variant="outline" size="sm">
                            Acknowledge
                          </Button>
                          <Button size="sm">Resolve</Button>
                        </>
                      )}
                      {alert.status === 'ACKNOWLEDGED' && (
                        <Button size="sm">Resolve</Button>
                      )}
                      <Button variant="ghost" size="icon">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Drift Tab */}
        <TabsContent value="drift" className="mt-6 space-y-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <LineChart
              title="Drift Score Over Time"
              description="PSI scores across deployments"
              data={driftData}
              lines={[
                { dataKey: 'fraud_detector', name: 'fraud-detector', color: '#00f5ff' },
                { dataKey: 'churn_predictor', name: 'churn-predictor', color: '#ff00ff' },
                { dataKey: 'recommendation', name: 'recommendation-engine', color: '#00ff88' },
              ]}
              xAxisKey="time"
              height={300}
              showLegend
            />

            <Card className="glass border-border/50">
              <CardHeader>
                <CardTitle className="text-base font-medium">Feature Drift Heatmap</CardTitle>
                <CardDescription>Current drift scores by feature</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {featureDrift.map((feature) => (
                    <div key={feature.name} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-mono">{feature.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{feature.score.toFixed(2)}</span>
                          <StatusBadge status={feature.status} size="sm" />
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all', getDriftColor(feature.status))}
                          style={{ width: `${Math.min(feature.score * 200, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Drift thresholds */}
          <Card className="glass border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-medium">Drift Thresholds</CardTitle>
                  <CardDescription>Configure alerting thresholds for drift detection</CardDescription>
                </div>
                <Button variant="outline" size="sm">
                  <Settings className="mr-2 h-4 w-4" />
                  Configure
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div className="p-3 rounded-lg bg-muted/30">
                  <p className="text-xs text-muted-foreground mb-1">None</p>
                  <p className="font-mono">&lt; 0.10</p>
                </div>
                <div className="p-3 rounded-lg bg-neon-green/10">
                  <p className="text-xs text-muted-foreground mb-1">Low</p>
                  <p className="font-mono text-neon-green">0.10 - 0.15</p>
                </div>
                <div className="p-3 rounded-lg bg-neon-yellow/10">
                  <p className="text-xs text-muted-foreground mb-1">Medium</p>
                  <p className="font-mono text-neon-yellow">0.15 - 0.25</p>
                </div>
                <div className="p-3 rounded-lg bg-destructive/10">
                  <p className="text-xs text-muted-foreground mb-1">High / Critical</p>
                  <p className="font-mono text-destructive">&gt; 0.25</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="mt-6 space-y-6">
          <LineChart
            title="Model Performance Metrics"
            description="Accuracy, precision, and recall over time"
            data={performanceData}
            lines={[
              { dataKey: 'accuracy', name: 'Accuracy', color: '#00f5ff' },
              { dataKey: 'precision', name: 'Precision', color: '#00ff88' },
              { dataKey: 'recall', name: 'Recall', color: '#ff00ff' },
            ]}
            xAxisKey="time"
            height={350}
            showLegend
          />

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="glass border-border/50">
              <CardHeader>
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-destructive" />
                  Performance Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <p className="text-3xl font-bold font-mono text-destructive">-1.3%</p>
                  <p className="text-sm text-muted-foreground mt-1">Accuracy change (7 days)</p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-border/50">
              <CardHeader>
                <CardTitle className="text-base font-medium">Baseline Comparison</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Current</span>
                    <span className="font-mono">93.2%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Baseline</span>
                    <span className="font-mono">94.5%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Threshold</span>
                    <span className="font-mono text-neon-yellow">90.0%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-border/50">
              <CardHeader>
                <CardTitle className="text-base font-medium">Retraining Recommendation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <Badge className="bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30 text-base px-4 py-2">
                    Recommended
                  </Badge>
                  <p className="text-sm text-muted-foreground mt-3">
                    Performance degradation and drift suggest retraining
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
