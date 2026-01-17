'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  GitBranch,
  Rocket,
  Download,
  MoreHorizontal,
  Clock,
  User,
  ArrowRight,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { StatusBadge } from '@/components/shared/status-badge';
import { LineChart } from '@/components/charts/line-chart';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import type { ModelVersion, ModelStage, StageTransition } from '@/types';

// Mock model data
const model = {
  id: '1',
  name: 'fraud-detector',
  description: 'XGBoost model for real-time fraud detection in transactions. This model analyzes transaction patterns to identify potentially fraudulent activities in real-time.',
  tags: ['fraud', 'xgboost', 'real-time', 'production'],
  createdAt: '2024-11-15T10:30:00Z',
  updatedAt: '2025-01-17T08:15:00Z',
  createdBy: 'john.doe@company.com',
};

// Mock versions
const versions: ModelVersion[] = [
  {
    id: 'v1',
    modelId: '1',
    tenantId: 't1',
    version: 'v3.2.1',
    stage: 'PRODUCTION' as ModelStage,
    artifactPath: 's3://models/fraud-detector/v3.2.1',
    metrics: { accuracy: 0.947, precision: 0.932, recall: 0.918, f1: 0.925, auc: 0.961 },
    runId: 'run-1',
    description: 'Improved feature engineering and hyperparameter tuning',
    createdAt: '2025-01-17T08:15:00Z',
    createdBy: 'john.doe',
  },
  {
    id: 'v2',
    modelId: '1',
    tenantId: 't1',
    version: 'v3.2.0',
    stage: 'STAGING' as ModelStage,
    artifactPath: 's3://models/fraud-detector/v3.2.0',
    metrics: { accuracy: 0.943, precision: 0.928, recall: 0.912, f1: 0.920, auc: 0.958 },
    runId: 'run-2',
    description: 'Added new transaction velocity features',
    createdAt: '2025-01-10T14:20:00Z',
    createdBy: 'jane.smith',
  },
  {
    id: 'v3',
    modelId: '1',
    tenantId: 't1',
    version: 'v3.1.0',
    stage: 'ARCHIVED' as ModelStage,
    artifactPath: 's3://models/fraud-detector/v3.1.0',
    metrics: { accuracy: 0.938, precision: 0.921, recall: 0.908, f1: 0.914, auc: 0.952 },
    runId: 'run-3',
    description: 'Baseline with updated training data',
    createdAt: '2025-01-02T09:30:00Z',
    createdBy: 'john.doe',
  },
  {
    id: 'v4',
    modelId: '1',
    tenantId: 't1',
    version: 'v3.0.0',
    stage: 'ARCHIVED' as ModelStage,
    artifactPath: 's3://models/fraud-detector/v3.0.0',
    metrics: { accuracy: 0.932, precision: 0.915, recall: 0.901, f1: 0.908, auc: 0.948 },
    runId: 'run-4',
    description: 'Major refactor with XGBoost 2.0',
    createdAt: '2024-12-15T11:00:00Z',
    createdBy: 'john.doe',
  },
];

// Mock stage transitions
const transitions: StageTransition[] = [
  {
    id: 't1',
    modelVersionId: 'v1',
    fromStage: 'STAGING' as ModelStage,
    toStage: 'PRODUCTION' as ModelStage,
    userId: 'u1',
    comment: 'Passed all validation tests, promoting to production',
    createdAt: '2025-01-17T08:15:00Z',
  },
  {
    id: 't2',
    modelVersionId: 'v1',
    fromStage: 'NONE' as ModelStage,
    toStage: 'STAGING' as ModelStage,
    userId: 'u1',
    comment: 'Initial staging deployment for validation',
    createdAt: '2025-01-15T10:00:00Z',
  },
  {
    id: 't3',
    modelVersionId: 'v2',
    fromStage: 'PRODUCTION' as ModelStage,
    toStage: 'STAGING' as ModelStage,
    userId: 'u2',
    comment: 'Rolled back due to latency issues, replaced by v3.2.1',
    createdAt: '2025-01-17T08:00:00Z',
  },
];

// Mock metrics over time
const metricsOverTime = [
  { version: 'v3.0.0', accuracy: 0.932, auc: 0.948 },
  { version: 'v3.1.0', accuracy: 0.938, auc: 0.952 },
  { version: 'v3.2.0', accuracy: 0.943, auc: 0.958 },
  { version: 'v3.2.1', accuracy: 0.947, auc: 0.961 },
];

function getStageColor(stage: ModelStage) {
  switch (stage) {
    case 'PRODUCTION':
      return 'bg-neon-green/10 text-neon-green border-neon-green/30';
    case 'STAGING':
      return 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30';
    case 'ARCHIVED':
      return 'bg-muted text-muted-foreground border-border';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

export default function ModelDetailPage() {
  useParams(); // Hook call required by Next.js for dynamic routes
  const [selectedTab, setSelectedTab] = useState('versions');
  const [isTransitionOpen, setIsTransitionOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null);
  const [transitionStage, setTransitionStage] = useState<ModelStage>('STAGING');
  const [transitionComment, setTransitionComment] = useState('');

  const handleTransition = () => {
    console.log('Transitioning:', selectedVersion?.version, 'to', transitionStage);
    setIsTransitionOpen(false);
    setSelectedVersion(null);
    setTransitionComment('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/models">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-2xl font-bold tracking-tight font-display">
              {model.name}
            </h1>
            <Badge variant="outline" className={cn('ml-2', getStageColor('PRODUCTION'))}>
              Production: v3.2.1
            </Badge>
          </div>
          <p className="text-muted-foreground max-w-2xl ml-11">
            {model.description}
          </p>
          <div className="flex items-center gap-4 ml-11 mt-2">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              {model.createdBy}
            </div>
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              Created {format(new Date(model.createdAt), 'MMM d, yyyy')}
            </div>
            <div className="flex gap-1.5">
              {model.tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="outline"
                  className="text-xs bg-muted/50 border-border"
                >
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button>
            <Rocket className="mr-2 h-4 w-4" />
            Deploy
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono">{versions.length}</div>
            <p className="text-xs text-muted-foreground">Total Versions</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-green">v3.2.1</div>
            <p className="text-xs text-muted-foreground">Production Version</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-yellow">v3.2.0</div>
            <p className="text-xs text-muted-foreground">Staging Version</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-cyan">0.947</div>
            <p className="text-xs text-muted-foreground">Best Accuracy</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="history">Stage History</TabsTrigger>
        </TabsList>

        <TabsContent value="versions" className="mt-6">
          <div className="space-y-4">
            {versions.map((version) => (
              <Card key={version.id} className="glass border-border/50">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="h-12 w-12 rounded-lg bg-muted/50 flex items-center justify-center">
                        <GitBranch className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium">{version.version}</span>
                          <StatusBadge status={version.stage} />
                        </div>
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {version.description}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                          <span>{version.createdBy}</span>
                          <span>{format(new Date(version.createdAt), 'MMM d, yyyy HH:mm')}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="grid grid-cols-3 gap-4 text-right">
                        <div>
                          <p className="text-xs text-muted-foreground">Accuracy</p>
                          <p className="font-mono text-sm text-neon-cyan">
                            {version.metrics.accuracy?.toFixed(3)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">F1</p>
                          <p className="font-mono text-sm">
                            {version.metrics.f1?.toFixed(3)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">AUC</p>
                          <p className="font-mono text-sm">
                            {version.metrics.auc?.toFixed(3)}
                          </p>
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
                          <DropdownMenuItem
                            onClick={() => {
                              setSelectedVersion(version);
                              setIsTransitionOpen(true);
                            }}
                          >
                            <ArrowRight className="mr-2 h-4 w-4" />
                            Transition Stage
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Rocket className="mr-2 h-4 w-4" />
                            Deploy
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Download className="mr-2 h-4 w-4" />
                            Download Artifact
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="mt-6">
          <LineChart
            title="Metrics Over Versions"
            description="Model performance across version releases"
            data={metricsOverTime}
            lines={[
              { dataKey: 'accuracy', name: 'Accuracy', color: '#00f5ff' },
              { dataKey: 'auc', name: 'AUC', color: '#00ff88' },
            ]}
            xAxisKey="version"
            height={350}
            showLegend
          />
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Stage Transition History</CardTitle>
              <CardDescription>
                Track all stage changes for this model
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {transitions.map((transition) => (
                  <div
                    key={transition.id}
                    className="flex items-start gap-4 p-4 rounded-lg bg-muted/30"
                  >
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <ArrowRight className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={transition.fromStage} size="sm" />
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        <StatusBadge status={transition.toStage} size="sm" />
                      </div>
                      <p className="text-sm mt-2">{transition.comment}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {format(new Date(transition.createdAt), 'MMM d, yyyy HH:mm')}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Stage Transition Dialog */}
      <Dialog open={isTransitionOpen} onOpenChange={setIsTransitionOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="font-display">Transition Stage</DialogTitle>
            <DialogDescription>
              Move {selectedVersion?.version} to a different stage.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Current Stage</Label>
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedVersion?.stage || 'NONE'} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>New Stage</Label>
              <Select
                value={transitionStage}
                onValueChange={(value) => setTransitionStage(value as ModelStage)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="NONE">None</SelectItem>
                  <SelectItem value="STAGING">Staging</SelectItem>
                  <SelectItem value="PRODUCTION">Production</SelectItem>
                  <SelectItem value="ARCHIVED">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Comment</Label>
              <Textarea
                placeholder="Reason for this transition..."
                value={transitionComment}
                onChange={(e) => setTransitionComment(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTransitionOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleTransition}>Transition</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
