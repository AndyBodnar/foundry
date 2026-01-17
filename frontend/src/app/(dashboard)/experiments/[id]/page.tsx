'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ColumnDef } from '@tanstack/react-table';
import {
  ArrowLeft,
  Play,
  Download,
  MoreHorizontal,
  Clock,
  User,
  Eye,
  Trash2,
  ArrowUpDown,
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
import { Checkbox } from '@/components/ui/checkbox';
import { StatusBadge } from '@/components/shared/status-badge';
import { DataTable } from '@/components/shared/data-table';
import { LineChart } from '@/components/charts/line-chart';
import { BarChart } from '@/components/charts/bar-chart';
import { format } from 'date-fns';
import type { Run, ExperimentStatus } from '@/types';

// Mock experiment data
const experiment = {
  id: '1',
  name: 'fraud-detection-xgboost',
  description: 'XGBoost model for fraud detection with hyperparameter tuning. This experiment explores various hyperparameter configurations to optimize model performance on the fraud detection task.',
  tags: ['fraud', 'xgboost', 'production'],
  createdAt: '2025-01-15T10:30:00Z',
  updatedAt: '2025-01-17T08:15:00Z',
  createdBy: 'john.doe@company.com',
};

// Mock runs data
const runs: Run[] = [
  {
    id: 'run-1',
    experimentId: '1',
    tenantId: 't1',
    name: 'run-xgb-lr-0.1',
    status: 'COMPLETED' as ExperimentStatus,
    parameters: { learning_rate: 0.1, max_depth: 6, n_estimators: 100 },
    metrics: { accuracy: 0.947, precision: 0.932, recall: 0.918, f1: 0.925 },
    startTime: '2025-01-17T08:00:00Z',
    endTime: '2025-01-17T08:15:00Z',
    duration: 900,
    user: 'john.doe',
  },
  {
    id: 'run-2',
    experimentId: '1',
    tenantId: 't1',
    name: 'run-xgb-lr-0.05',
    status: 'COMPLETED' as ExperimentStatus,
    parameters: { learning_rate: 0.05, max_depth: 8, n_estimators: 150 },
    metrics: { accuracy: 0.941, precision: 0.928, recall: 0.912, f1: 0.920 },
    startTime: '2025-01-16T14:30:00Z',
    endTime: '2025-01-16T15:00:00Z',
    duration: 1800,
    user: 'john.doe',
  },
  {
    id: 'run-3',
    experimentId: '1',
    tenantId: 't1',
    name: 'run-xgb-depth-10',
    status: 'RUNNING' as ExperimentStatus,
    parameters: { learning_rate: 0.1, max_depth: 10, n_estimators: 200 },
    metrics: { accuracy: 0.938 },
    startTime: '2025-01-17T09:00:00Z',
    duration: 0,
    user: 'jane.smith',
  },
  {
    id: 'run-4',
    experimentId: '1',
    tenantId: 't1',
    name: 'run-xgb-small',
    status: 'FAILED' as ExperimentStatus,
    parameters: { learning_rate: 0.2, max_depth: 4, n_estimators: 50 },
    metrics: {},
    startTime: '2025-01-16T10:00:00Z',
    endTime: '2025-01-16T10:05:00Z',
    duration: 300,
    user: 'john.doe',
  },
  {
    id: 'run-5',
    experimentId: '1',
    tenantId: 't1',
    name: 'run-xgb-baseline',
    status: 'COMPLETED' as ExperimentStatus,
    parameters: { learning_rate: 0.1, max_depth: 6, n_estimators: 100 },
    metrics: { accuracy: 0.935, precision: 0.921, recall: 0.908, f1: 0.914 },
    startTime: '2025-01-15T11:00:00Z',
    endTime: '2025-01-15T11:15:00Z',
    duration: 900,
    user: 'john.doe',
  },
];

// Mock metric history for charts
const metricHistory = [
  { step: 1, accuracy: 0.72, precision: 0.68, recall: 0.65 },
  { step: 2, accuracy: 0.78, precision: 0.74, recall: 0.71 },
  { step: 3, accuracy: 0.83, precision: 0.79, recall: 0.76 },
  { step: 4, accuracy: 0.87, precision: 0.84, recall: 0.81 },
  { step: 5, accuracy: 0.90, precision: 0.87, recall: 0.85 },
  { step: 6, accuracy: 0.92, precision: 0.89, recall: 0.87 },
  { step: 7, accuracy: 0.94, precision: 0.91, recall: 0.89 },
  { step: 8, accuracy: 0.945, precision: 0.925, recall: 0.91 },
  { step: 9, accuracy: 0.946, precision: 0.930, recall: 0.915 },
  { step: 10, accuracy: 0.947, precision: 0.932, recall: 0.918 },
];

const parameterComparison = [
  { name: 'run-1', accuracy: 0.947 },
  { name: 'run-2', accuracy: 0.941 },
  { name: 'run-5', accuracy: 0.935 },
];

const columns: ColumnDef<Run>[] = [
  {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
  },
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Run
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <div className="font-medium font-mono text-sm">{row.original.name}</div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },
  {
    accessorKey: 'metrics.accuracy',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Accuracy
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const accuracy = row.original.metrics?.accuracy;
      if (!accuracy) return <span className="text-muted-foreground">-</span>;
      return <span className="font-mono text-neon-green">{accuracy.toFixed(3)}</span>;
    },
  },
  {
    accessorKey: 'metrics.f1',
    header: 'F1 Score',
    cell: ({ row }) => {
      const f1 = row.original.metrics?.f1;
      if (!f1) return <span className="text-muted-foreground">-</span>;
      return <span className="font-mono">{f1.toFixed(3)}</span>;
    },
  },
  {
    accessorKey: 'duration',
    header: 'Duration',
    cell: ({ row }) => {
      const duration = row.original.duration;
      if (!duration) return <span className="text-muted-foreground">-</span>;
      const minutes = Math.floor(duration / 60);
      const seconds = duration % 60;
      return (
        <span className="text-muted-foreground">
          {minutes}m {seconds}s
        </span>
      );
    },
  },
  {
    accessorKey: 'startTime',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Started
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {format(new Date(row.original.startTime), 'MMM d, HH:mm')}
      </span>
    ),
  },
  {
    id: 'actions',
    cell: () => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <Eye className="mr-2 h-4 w-4" />
            View Details
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Download className="mr-2 h-4 w-4" />
            Download Artifacts
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-destructive focus:text-destructive">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];

export default function ExperimentDetailPage() {
  useParams(); // Hook call required by Next.js for dynamic routes
  const [selectedTab, setSelectedTab] = useState('runs');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/experiments">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-2xl font-bold tracking-tight font-display">
              {experiment.name}
            </h1>
          </div>
          <p className="text-muted-foreground max-w-2xl ml-11">
            {experiment.description}
          </p>
          <div className="flex items-center gap-4 ml-11 mt-2">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              {experiment.createdBy}
            </div>
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              {format(new Date(experiment.createdAt), 'MMM d, yyyy')}
            </div>
            <div className="flex gap-1.5">
              {experiment.tags.map((tag) => (
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
            <Play className="mr-2 h-4 w-4" />
            New Run
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono">{runs.length}</div>
            <p className="text-xs text-muted-foreground">Total Runs</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-green">
              {runs.filter((r) => r.status === 'COMPLETED').length}
            </div>
            <p className="text-xs text-muted-foreground">Completed</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-cyan">
              {runs.filter((r) => r.status === 'RUNNING').length}
            </div>
            <p className="text-xs text-muted-foreground">Running</p>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="text-2xl font-bold font-mono text-neon-green">
              0.947
            </div>
            <p className="text-xs text-muted-foreground">Best Accuracy</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="charts">Charts</TabsTrigger>
          <TabsTrigger value="compare">Compare</TabsTrigger>
        </TabsList>

        <TabsContent value="runs" className="mt-6">
          <DataTable
            columns={columns}
            data={runs}
            searchKey="name"
            searchPlaceholder="Search runs..."
          />
        </TabsContent>

        <TabsContent value="charts" className="mt-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <LineChart
              title="Training Metrics"
              description="Metrics over training steps"
              data={metricHistory}
              lines={[
                { dataKey: 'accuracy', name: 'Accuracy', color: '#00f5ff' },
                { dataKey: 'precision', name: 'Precision', color: '#00ff88' },
                { dataKey: 'recall', name: 'Recall', color: '#ff00ff' },
              ]}
              xAxisKey="step"
              height={300}
              showLegend
            />
            <BarChart
              title="Run Comparison"
              description="Accuracy across completed runs"
              data={parameterComparison}
              dataKey="accuracy"
              xAxisKey="name"
              color="#00f5ff"
              height={300}
            />
          </div>
        </TabsContent>

        <TabsContent value="compare" className="mt-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Run Comparison</CardTitle>
              <CardDescription>
                Select runs from the table to compare their parameters and metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {runs
                  .filter((r) => r.status === 'COMPLETED')
                  .slice(0, 3)
                  .map((run) => (
                    <div
                      key={run.id}
                      className="p-4 rounded-lg bg-muted/30 border border-border"
                    >
                      <h4 className="font-mono font-medium mb-3">{run.name}</h4>
                      <div className="space-y-2">
                        <h5 className="text-xs text-muted-foreground uppercase tracking-wider">
                          Parameters
                        </h5>
                        {Object.entries(run.parameters).map(([key, value]) => (
                          <div
                            key={key}
                            className="flex justify-between text-sm"
                          >
                            <span className="text-muted-foreground">{key}</span>
                            <span className="font-mono">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-2 mt-4">
                        <h5 className="text-xs text-muted-foreground uppercase tracking-wider">
                          Metrics
                        </h5>
                        {Object.entries(run.metrics).map(([key, value]) => (
                          <div
                            key={key}
                            className="flex justify-between text-sm"
                          >
                            <span className="text-muted-foreground">{key}</span>
                            <span className="font-mono text-neon-green">
                              {value.toFixed(3)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
