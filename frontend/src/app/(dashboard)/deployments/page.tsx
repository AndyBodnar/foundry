'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Plus,
  MoreHorizontal,
  Rocket,
  Eye,
  Trash2,
  Play,
  Pause,
  RotateCcw,
  Activity,
  Clock,
  Zap,
  Server,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/shared/page-header';
import { StatusBadge } from '@/components/shared/status-badge';
import { cn } from '@/lib/utils';
import type { Deployment, DeploymentStatus, TrafficVersion } from '@/types';

// Mock data
const deployments: (Deployment & {
  traffic: TrafficVersion[];
  latencyP99: number;
  requestsPerSec: number;
  errorRate: number;
})[] = [
  {
    id: '1',
    tenantId: 't1',
    name: 'fraud-detector',
    status: 'RUNNING' as DeploymentStatus,
    endpoint: 'https://api.foundry.io/predict/fraud-detector',
    config: {
      replicas: 3,
      minReplicas: 2,
      maxReplicas: 10,
      cpuRequest: '500m',
      memoryRequest: '512Mi',
      cpuLimit: '1000m',
      memoryLimit: '1Gi',
    },
    trafficConfig: { versions: [] },
    healthStatus: {
      status: 'HEALTHY',
      replicas: { ready: 3, total: 3 },
      lastCheck: new Date().toISOString(),
      latencyP50Ms: 25,
      latencyP99Ms: 45,
      errorRate: 0.001,
    },
    createdAt: '2024-12-01T10:00:00Z',
    updatedAt: '2025-01-17T08:00:00Z',
    traffic: [
      { modelVersionId: 'v1', modelName: 'fraud-model', version: 'v3.2.1', weight: 90 },
      { modelVersionId: 'v2', modelName: 'fraud-model', version: 'v3.2.0', weight: 10 },
    ],
    latencyP99: 45,
    requestsPerSec: 2340,
    errorRate: 0.1,
  },
  {
    id: '2',
    tenantId: 't1',
    name: 'churn-predictor',
    status: 'RUNNING' as DeploymentStatus,
    endpoint: 'https://api.foundry.io/predict/churn-predictor',
    config: {
      replicas: 2,
      minReplicas: 1,
      maxReplicas: 5,
      cpuRequest: '250m',
      memoryRequest: '256Mi',
      cpuLimit: '500m',
      memoryLimit: '512Mi',
    },
    trafficConfig: { versions: [] },
    healthStatus: {
      status: 'HEALTHY',
      replicas: { ready: 2, total: 2 },
      lastCheck: new Date().toISOString(),
      latencyP50Ms: 80,
      latencyP99Ms: 128,
      errorRate: 0.002,
    },
    createdAt: '2024-12-15T14:00:00Z',
    updatedAt: '2025-01-16T16:00:00Z',
    traffic: [
      { modelVersionId: 'v1', modelName: 'churn-model', version: 'v2.1.0', weight: 100 },
    ],
    latencyP99: 128,
    requestsPerSec: 890,
    errorRate: 0.2,
  },
  {
    id: '3',
    tenantId: 't1',
    name: 'recommendation-engine',
    status: 'RUNNING' as DeploymentStatus,
    endpoint: 'https://api.foundry.io/predict/recommendation-engine',
    config: {
      replicas: 5,
      minReplicas: 3,
      maxReplicas: 15,
      cpuRequest: '1000m',
      memoryRequest: '1Gi',
      cpuLimit: '2000m',
      memoryLimit: '2Gi',
    },
    trafficConfig: { versions: [] },
    healthStatus: {
      status: 'HEALTHY',
      replicas: { ready: 5, total: 5 },
      lastCheck: new Date().toISOString(),
      latencyP50Ms: 45,
      latencyP99Ms: 67,
      errorRate: 0.0005,
    },
    createdAt: '2024-11-01T09:00:00Z',
    updatedAt: '2025-01-17T11:00:00Z',
    traffic: [
      { modelVersionId: 'v1', modelName: 'rec-model', version: 'v4.0.0', weight: 80 },
      { modelVersionId: 'v2', modelName: 'rec-model', version: 'v4.1.0-beta', weight: 20 },
    ],
    latencyP99: 67,
    requestsPerSec: 5670,
    errorRate: 0.05,
  },
  {
    id: '4',
    tenantId: 't1',
    name: 'sentiment-analyzer',
    status: 'DEPLOYING' as DeploymentStatus,
    config: {
      replicas: 2,
      minReplicas: 1,
      maxReplicas: 4,
      cpuRequest: '500m',
      memoryRequest: '512Mi',
      cpuLimit: '1000m',
      memoryLimit: '1Gi',
    },
    trafficConfig: { versions: [] },
    healthStatus: {
      status: 'DEGRADED',
      replicas: { ready: 1, total: 2 },
      lastCheck: new Date().toISOString(),
    },
    createdAt: '2025-01-17T10:00:00Z',
    updatedAt: '2025-01-17T10:05:00Z',
    traffic: [
      { modelVersionId: 'v1', modelName: 'sentiment-model', version: 'v1.5.0', weight: 100 },
    ],
    latencyP99: 0,
    requestsPerSec: 0,
    errorRate: 0,
  },
];

function TrafficBar({ traffic }: { traffic: TrafficVersion[] }) {
  const colors = ['#00ff88', '#00f5ff', '#ff00ff', '#ffff00'];

  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-muted">
        {traffic.map((t, i) => (
          <div
            key={t.modelVersionId}
            className="transition-all duration-300"
            style={{
              width: `${t.weight}%`,
              backgroundColor: colors[i % colors.length],
            }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        {traffic.map((t, i) => (
          <div key={t.modelVersionId} className="flex items-center gap-1.5 text-xs">
            <div
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: colors[i % colors.length] }}
            />
            <span className="font-mono">{t.version}</span>
            <span className="text-muted-foreground">({t.weight}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function getHealthColor(status: string) {
  switch (status) {
    case 'HEALTHY':
      return 'text-neon-green';
    case 'DEGRADED':
      return 'text-neon-yellow';
    case 'UNHEALTHY':
      return 'text-destructive';
    default:
      return 'text-muted-foreground';
  }
}

export default function DeploymentsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newDeployment, setNewDeployment] = useState({
    name: '',
    modelName: '',
    modelVersion: '',
    replicas: '2',
  });

  const handleCreate = () => {
    console.log('Creating deployment:', newDeployment);
    setIsCreateOpen(false);
    setNewDeployment({ name: '', modelName: '', modelVersion: '', replicas: '2' });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Deployments"
        description="Manage model serving endpoints and traffic routing"
        action={{
          label: 'New Deployment',
          icon: Plus,
          onClick: () => setIsCreateOpen(true),
        }}
      />

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">{deployments.length}</div>
                <p className="text-xs text-muted-foreground">Total Deployments</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-cyan/10">
                <Rocket className="h-5 w-5 text-neon-cyan" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">
                  {deployments.reduce((acc, d) => acc + d.requestsPerSec, 0).toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">Requests/sec</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-green/10">
                <Zap className="h-5 w-5 text-neon-green" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">
                  {Math.round(deployments.reduce((acc, d) => acc + d.latencyP99, 0) / deployments.filter(d => d.latencyP99 > 0).length)}ms
                </div>
                <p className="text-xs text-muted-foreground">Avg P99 Latency</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-purple/10">
                <Clock className="h-5 w-5 text-neon-purple" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">
                  {deployments.reduce((acc, d) => acc + (d.healthStatus?.replicas.ready || 0), 0)}
                </div>
                <p className="text-xs text-muted-foreground">Total Replicas</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-orange/10">
                <Server className="h-5 w-5 text-neon-orange" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deployments Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {deployments.map((deployment) => (
          <Card key={deployment.id} className="glass border-border/50 hover:border-primary/30 transition-all">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-neon-green/10 flex items-center justify-center">
                    <Rocket className="h-5 w-5 text-neon-green" />
                  </div>
                  <div>
                    <CardTitle className="text-base font-medium flex items-center gap-2">
                      <Link href={`/deployments/${deployment.id}`} className="hover:text-primary transition-colors">
                        {deployment.name}
                      </Link>
                      <StatusBadge status={deployment.status} size="sm" />
                    </CardTitle>
                    {deployment.endpoint && (
                      <CardDescription className="text-xs font-mono mt-0.5">
                        {deployment.endpoint}
                      </CardDescription>
                    )}
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href={`/deployments/${deployment.id}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Activity className="mr-2 h-4 w-4" />
                      View Metrics
                    </DropdownMenuItem>
                    {deployment.status === 'RUNNING' ? (
                      <DropdownMenuItem>
                        <Pause className="mr-2 h-4 w-4" />
                        Stop
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem>
                        <Play className="mr-2 h-4 w-4" />
                        Start
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem>
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Rollback
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-destructive focus:text-destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Traffic Split */}
              <div>
                <p className="text-xs text-muted-foreground mb-2">Traffic Split</p>
                <TrafficBar traffic={deployment.traffic} />
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-4 gap-4 pt-2 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground">Requests/s</p>
                  <p className="font-mono text-sm">
                    {deployment.requestsPerSec.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">P99 Latency</p>
                  <p className="font-mono text-sm">
                    {deployment.latencyP99 || '-'}ms
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Error Rate</p>
                  <p className={cn(
                    'font-mono text-sm',
                    deployment.errorRate > 0.5 ? 'text-destructive' : 'text-neon-green'
                  )}>
                    {deployment.errorRate}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Replicas</p>
                  <p className={cn(
                    'font-mono text-sm',
                    getHealthColor(deployment.healthStatus?.status || 'UNKNOWN')
                  )}>
                    {deployment.healthStatus?.replicas.ready || 0}/{deployment.healthStatus?.replicas.total || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Deployment Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-display">Create New Deployment</DialogTitle>
            <DialogDescription>
              Deploy a model version to start serving predictions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Deployment Name</Label>
              <Input
                id="name"
                placeholder="e.g., fraud-detector-prod"
                value={newDeployment.name}
                onChange={(e) =>
                  setNewDeployment({ ...newDeployment, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <Select
                value={newDeployment.modelName}
                onValueChange={(value) =>
                  setNewDeployment({ ...newDeployment, modelName: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fraud-detector">fraud-detector</SelectItem>
                  <SelectItem value="churn-predictor">churn-predictor</SelectItem>
                  <SelectItem value="recommendation-engine">recommendation-engine</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">Version</Label>
              <Select
                value={newDeployment.modelVersion}
                onValueChange={(value) =>
                  setNewDeployment({ ...newDeployment, modelVersion: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a version" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="v3.2.1">v3.2.1 (Production)</SelectItem>
                  <SelectItem value="v3.2.0">v3.2.0 (Staging)</SelectItem>
                  <SelectItem value="v3.1.0">v3.1.0 (Archived)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="replicas">Initial Replicas</Label>
              <Input
                id="replicas"
                type="number"
                min="1"
                max="10"
                value={newDeployment.replicas}
                onChange={(e) =>
                  setNewDeployment({ ...newDeployment, replicas: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate}>Create Deployment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
