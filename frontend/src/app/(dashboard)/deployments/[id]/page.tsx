'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Pause,
  RotateCcw,
  Activity,
  Clock,
  Zap,
  AlertTriangle,
  CheckCircle,
  ExternalLink,
  Copy,
  Sliders,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { StatusBadge } from '@/components/shared/status-badge';
import { AreaChart } from '@/components/charts/area-chart';
import { LineChart } from '@/components/charts/line-chart';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type { TrafficVersion, ABTest, DeploymentStatus } from '@/types';

// Mock deployment data
const deployment = {
  id: '1',
  name: 'fraud-detector',
  status: 'RUNNING',
  endpoint: 'https://api.foundry.io/predict/fraud-detector',
  createdAt: '2024-12-01T10:00:00Z',
  updatedAt: '2025-01-17T08:00:00Z',
  config: {
    replicas: 3,
    minReplicas: 2,
    maxReplicas: 10,
    cpuRequest: '500m',
    memoryRequest: '512Mi',
    cpuLimit: '1000m',
    memoryLimit: '1Gi',
  },
  healthStatus: {
    status: 'HEALTHY',
    replicas: { ready: 3, total: 3 },
    lastCheck: new Date().toISOString(),
    latencyP50Ms: 25,
    latencyP99Ms: 45,
    errorRate: 0.001,
  },
};

const traffic: TrafficVersion[] = [
  { modelVersionId: 'v1', modelName: 'fraud-model', version: 'v3.2.1', weight: 90 },
  { modelVersionId: 'v2', modelName: 'fraud-model', version: 'v3.2.0', weight: 10 },
];

// Mock A/B test
const abTest: ABTest = {
  id: 'ab1',
  deploymentId: '1',
  name: 'v3.2.1 vs v3.2.0',
  status: 'RUNNING',
  controlVersionId: 'v1',
  treatmentVersionId: 'v2',
  trafficSplit: 10,
  primaryMetric: 'conversion_rate',
  startTime: '2025-01-15T10:00:00Z',
  results: {
    controlMetric: 0.0342,
    treatmentMetric: 0.0358,
    uplift: 4.68,
    pValue: 0.12,
    isSignificant: false,
    sampleSize: { control: 45000, treatment: 5000 },
  },
};

// Mock metrics data
const latencyData = [
  { time: '00:00', p50: 22, p99: 42 },
  { time: '04:00', p50: 20, p99: 38 },
  { time: '08:00', p50: 28, p99: 52 },
  { time: '12:00', p50: 32, p99: 58 },
  { time: '16:00', p50: 30, p99: 55 },
  { time: '20:00', p50: 25, p99: 45 },
  { time: 'Now', p50: 25, p99: 45 },
];

const throughputData = [
  { time: '00:00', requests: 1200 },
  { time: '04:00', requests: 800 },
  { time: '08:00', requests: 2400 },
  { time: '12:00', requests: 3200 },
  { time: '16:00', requests: 2800 },
  { time: '20:00', requests: 2100 },
  { time: 'Now', requests: 2340 },
];

export default function DeploymentDetailPage() {
  useParams(); // Hook call required by Next.js for dynamic routes
  const [selectedTab, setSelectedTab] = useState('overview');
  const [isTrafficOpen, setIsTrafficOpen] = useState(false);
  const [trafficWeights, setTrafficWeights] = useState(traffic.map((t) => t.weight));

  const handleUpdateTraffic = () => {
    console.log('Updating traffic:', trafficWeights);
    setIsTrafficOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/deployments">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-2xl font-bold tracking-tight font-display">
              {deployment.name}
            </h1>
            <StatusBadge status={deployment.status as DeploymentStatus} />
          </div>
          <div className="flex items-center gap-4 ml-11">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-mono">{deployment.endpoint}</span>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <Copy className="h-3 w-3" />
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <ExternalLink className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsTrafficOpen(true)}>
            <Sliders className="mr-2 h-4 w-4" />
            Configure Traffic
          </Button>
          <Button variant="outline">
            <RotateCcw className="mr-2 h-4 w-4" />
            Rollback
          </Button>
          <Button variant="destructive">
            <Pause className="mr-2 h-4 w-4" />
            Stop
          </Button>
        </div>
      </div>

      {/* Health Status Banner */}
      <Card className={cn(
        'border-l-4',
        deployment.healthStatus.status === 'HEALTHY' ? 'border-l-neon-green' : 'border-l-neon-yellow'
      )}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn(
                'p-2 rounded-lg',
                deployment.healthStatus.status === 'HEALTHY' ? 'bg-neon-green/10 text-neon-green' : 'bg-neon-yellow/10 text-neon-yellow'
              )}>
                {deployment.healthStatus.status === 'HEALTHY' ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <AlertTriangle className="h-5 w-5" />
                )}
              </div>
              <div>
                <p className="font-medium">
                  {deployment.healthStatus.status === 'HEALTHY' ? 'All systems operational' : 'Degraded performance'}
                </p>
                <p className="text-sm text-muted-foreground">
                  Last health check: {format(new Date(deployment.healthStatus.lastCheck), 'MMM d, HH:mm:ss')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Replicas</p>
                <p className="font-mono text-lg text-neon-green">
                  {deployment.healthStatus.replicas.ready}/{deployment.healthStatus.replicas.total}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Error Rate</p>
                <p className="font-mono text-lg text-neon-green">
                  {(deployment.healthStatus.errorRate * 100).toFixed(2)}%
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">P99 Latency</p>
                <p className="font-mono text-lg">
                  {deployment.healthStatus.latencyP99Ms}ms
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Traffic Split Visualization */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Traffic Distribution</CardTitle>
          <CardDescription>Current model version traffic allocation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Visual bar */}
            <div className="relative h-12 rounded-lg overflow-hidden flex">
              {traffic.map((t, i) => (
                <div
                  key={t.modelVersionId}
                  className="flex items-center justify-center transition-all duration-500"
                  style={{
                    width: `${t.weight}%`,
                    backgroundColor: i === 0 ? '#00ff88' : '#00f5ff',
                  }}
                >
                  <span className="text-black font-mono font-medium text-sm">
                    {t.weight}%
                  </span>
                </div>
              ))}
            </div>
            {/* Legend */}
            <div className="flex justify-center gap-8">
              {traffic.map((t, i) => (
                <div key={t.modelVersionId} className="flex items-center gap-2">
                  <div
                    className="h-3 w-3 rounded"
                    style={{ backgroundColor: i === 0 ? '#00ff88' : '#00f5ff' }}
                  />
                  <span className="font-mono text-sm">{t.version}</span>
                  <Badge variant="outline" className="text-xs">
                    {t.weight}%
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="ab-tests">A/B Tests</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <AreaChart
              title="Request Throughput"
              description="Requests per second over last 24 hours"
              data={throughputData}
              dataKey="requests"
              xAxisKey="time"
              color="#00f5ff"
              height={280}
            />
            <LineChart
              title="Latency Distribution"
              description="P50 and P99 latency over last 24 hours"
              data={latencyData}
              lines={[
                { dataKey: 'p50', name: 'P50', color: '#00ff88' },
                { dataKey: 'p99', name: 'P99', color: '#ff00ff' },
              ]}
              xAxisKey="time"
              height={280}
              showLegend
            />
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="mt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="glass border-border/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold font-mono">2,340</div>
                    <p className="text-xs text-muted-foreground">Requests/sec</p>
                  </div>
                  <Zap className="h-5 w-5 text-neon-cyan" />
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold font-mono">25ms</div>
                    <p className="text-xs text-muted-foreground">P50 Latency</p>
                  </div>
                  <Clock className="h-5 w-5 text-neon-green" />
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold font-mono">45ms</div>
                    <p className="text-xs text-muted-foreground">P99 Latency</p>
                  </div>
                  <Clock className="h-5 w-5 text-neon-purple" />
                </div>
              </CardContent>
            </Card>
            <Card className="glass border-border/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold font-mono text-neon-green">0.1%</div>
                    <p className="text-xs text-muted-foreground">Error Rate</p>
                  </div>
                  <Activity className="h-5 w-5 text-neon-orange" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="ab-tests" className="mt-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{abTest.name}</CardTitle>
                  <CardDescription>
                    Started {format(new Date(abTest.startTime), 'MMM d, yyyy')}
                  </CardDescription>
                </div>
                <StatusBadge status={abTest.status === 'CANCELLED' ? 'CANCELLED' : abTest.status} />
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Control */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium">Control (v3.2.1)</span>
                    <Badge variant="outline">90% Traffic</Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Conversion Rate</span>
                      <span className="font-mono">{(abTest.results!.controlMetric * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Sample Size</span>
                      <span className="font-mono">{abTest.results!.sampleSize.control.toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Treatment */}
                <div className="p-4 rounded-lg bg-muted/30 border border-neon-cyan/30">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium">Treatment (v3.2.0)</span>
                    <Badge variant="outline" className="border-neon-cyan/30 text-neon-cyan">10% Traffic</Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Conversion Rate</span>
                      <span className="font-mono text-neon-green">{(abTest.results!.treatmentMetric * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Sample Size</span>
                      <span className="font-mono">{abTest.results!.sampleSize.treatment.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Results Summary */}
              <div className="p-4 rounded-lg bg-neon-cyan/5 border border-neon-cyan/20">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Uplift</p>
                    <p className="text-2xl font-bold font-mono text-neon-cyan">
                      +{abTest.results!.uplift.toFixed(2)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">p-value</p>
                    <p className="text-2xl font-bold font-mono">
                      {abTest.results!.pValue.toFixed(3)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Significance</p>
                    <Badge variant={abTest.results!.isSignificant ? 'default' : 'secondary'}>
                      {abTest.results!.isSignificant ? 'Significant' : 'Not yet significant'}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline">End Test</Button>
                <Button>Promote Treatment to 100%</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="mt-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Resource Configuration</CardTitle>
              <CardDescription>Compute resources and scaling settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">Scaling</h4>
                  <div className="grid gap-2">
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">Current Replicas</span>
                      <span className="font-mono">{deployment.config.replicas}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">Min Replicas</span>
                      <span className="font-mono">{deployment.config.minReplicas}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">Max Replicas</span>
                      <span className="font-mono">{deployment.config.maxReplicas}</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">Resources</h4>
                  <div className="grid gap-2">
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">CPU Request</span>
                      <span className="font-mono">{deployment.config.cpuRequest}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">CPU Limit</span>
                      <span className="font-mono">{deployment.config.cpuLimit}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">Memory Request</span>
                      <span className="font-mono">{deployment.config.memoryRequest}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-border">
                      <span className="text-sm text-muted-foreground">Memory Limit</span>
                      <span className="font-mono">{deployment.config.memoryLimit}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Traffic Configuration Dialog */}
      <Dialog open={isTrafficOpen} onOpenChange={setIsTrafficOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-display">Configure Traffic Split</DialogTitle>
            <DialogDescription>
              Adjust the traffic distribution between model versions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {traffic.map((t, i) => (
              <div key={t.modelVersionId} className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="font-mono">{t.version}</Label>
                  <span className="font-mono text-lg">{trafficWeights[i]}%</span>
                </div>
                <Slider
                  value={[trafficWeights[i]]}
                  onValueChange={([value]) => {
                    const newWeights = [...trafficWeights];
                    const diff = value - newWeights[i];
                    newWeights[i] = value;
                    // Adjust other weights proportionally
                    const otherIndex = i === 0 ? 1 : 0;
                    newWeights[otherIndex] = Math.max(0, Math.min(100, newWeights[otherIndex] - diff));
                    setTrafficWeights(newWeights);
                  }}
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTrafficOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateTraffic}>Apply Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
