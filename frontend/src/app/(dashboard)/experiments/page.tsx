'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ColumnDef } from '@tanstack/react-table';
import {
  Plus,
  MoreHorizontal,
  FlaskConical,
  Play,
  Eye,
  Trash2,
  Copy,
  ArrowUpDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
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
import { Textarea } from '@/components/ui/textarea';
import { PageHeader } from '@/components/shared/page-header';
import { DataTable } from '@/components/shared/data-table';
import { format } from 'date-fns';
import type { Experiment } from '@/types';

// Mock data
const experiments: Experiment[] = [
  {
    id: '1',
    tenantId: 't1',
    name: 'fraud-detection-xgboost',
    description: 'XGBoost model for fraud detection with hyperparameter tuning',
    tags: ['fraud', 'xgboost', 'production'],
    runsCount: 24,
    bestMetric: 0.947,
    bestMetricName: 'accuracy',
    createdAt: '2025-01-15T10:30:00Z',
    updatedAt: '2025-01-17T08:15:00Z',
  },
  {
    id: '2',
    tenantId: 't1',
    name: 'churn-prediction-lstm',
    description: 'LSTM-based model for customer churn prediction',
    tags: ['churn', 'lstm', 'deep-learning'],
    runsCount: 18,
    bestMetric: 0.892,
    bestMetricName: 'f1_score',
    createdAt: '2025-01-10T14:20:00Z',
    updatedAt: '2025-01-16T16:45:00Z',
  },
  {
    id: '3',
    tenantId: 't1',
    name: 'recommendation-engine-v2',
    description: 'Collaborative filtering for product recommendations',
    tags: ['recommendations', 'collaborative-filtering'],
    runsCount: 32,
    bestMetric: 0.156,
    bestMetricName: 'ndcg@10',
    createdAt: '2025-01-05T09:00:00Z',
    updatedAt: '2025-01-17T11:30:00Z',
  },
  {
    id: '4',
    tenantId: 't1',
    name: 'sentiment-analysis-bert',
    description: 'BERT fine-tuning for customer review sentiment analysis',
    tags: ['nlp', 'bert', 'sentiment'],
    runsCount: 12,
    bestMetric: 0.912,
    bestMetricName: 'accuracy',
    createdAt: '2025-01-12T11:15:00Z',
    updatedAt: '2025-01-15T09:20:00Z',
  },
  {
    id: '5',
    tenantId: 't1',
    name: 'demand-forecasting',
    description: 'Time series forecasting for inventory demand',
    tags: ['forecasting', 'time-series', 'prophet'],
    runsCount: 8,
    bestMetric: 0.087,
    bestMetricName: 'mape',
    createdAt: '2025-01-08T16:40:00Z',
    updatedAt: '2025-01-14T13:55:00Z',
  },
  {
    id: '6',
    tenantId: 't1',
    name: 'image-classification-resnet',
    description: 'ResNet50 transfer learning for product image classification',
    tags: ['cv', 'resnet', 'transfer-learning'],
    runsCount: 15,
    bestMetric: 0.968,
    bestMetricName: 'top5_accuracy',
    createdAt: '2025-01-03T08:30:00Z',
    updatedAt: '2025-01-13T17:10:00Z',
  },
];

const columns: ColumnDef<Experiment>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Name
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <Link
        href={`/experiments/${row.original.id}`}
        className="flex items-center gap-3 group"
      >
        <div className="h-9 w-9 rounded-lg bg-neon-cyan/10 flex items-center justify-center group-hover:bg-neon-cyan/20 transition-colors">
          <FlaskConical className="h-4 w-4 text-neon-cyan" />
        </div>
        <div>
          <p className="font-medium group-hover:text-primary transition-colors">
            {row.original.name}
          </p>
          <p className="text-xs text-muted-foreground max-w-[300px] truncate">
            {row.original.description}
          </p>
        </div>
      </Link>
    ),
  },
  {
    accessorKey: 'tags',
    header: 'Tags',
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-1 max-w-[200px]">
        {row.original.tags.slice(0, 2).map((tag) => (
          <Badge
            key={tag}
            variant="outline"
            className="text-xs bg-muted/50 border-border"
          >
            {tag}
          </Badge>
        ))}
        {row.original.tags.length > 2 && (
          <Badge variant="outline" className="text-xs bg-muted/50 border-border">
            +{row.original.tags.length - 2}
          </Badge>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'runsCount',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Runs
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <span className="font-mono">{row.original.runsCount}</span>
    ),
  },
  {
    accessorKey: 'bestMetric',
    header: 'Best Metric',
    cell: ({ row }) => {
      const metric = row.original.bestMetric;
      const metricName = row.original.bestMetricName;
      if (!metric) return <span className="text-muted-foreground">-</span>;
      return (
        <div className="text-right">
          <span className="font-mono text-neon-green">{metric.toFixed(3)}</span>
          {metricName && (
            <p className="text-xs text-muted-foreground">{metricName}</p>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: 'updatedAt',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Last Updated
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {format(new Date(row.original.updatedAt), 'MMM d, yyyy HH:mm')}
      </span>
    ),
  },
  {
    id: 'actions',
    cell: ({ row }) => (
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
            <Link href={`/experiments/${row.original.id}`}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Play className="mr-2 h-4 w-4" />
            Start New Run
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Copy className="mr-2 h-4 w-4" />
            Duplicate
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

export default function ExperimentsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newExperiment, setNewExperiment] = useState({
    name: '',
    description: '',
    tags: '',
  });

  const handleCreate = () => {
    console.log('Creating experiment:', newExperiment);
    setIsCreateOpen(false);
    setNewExperiment({ name: '', description: '', tags: '' });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Experiments"
        description="Track and compare your ML experiments"
        action={{
          label: 'New Experiment',
          icon: Plus,
          onClick: () => setIsCreateOpen(true),
        }}
      />

      <DataTable
        columns={columns}
        data={experiments}
        searchKey="name"
        searchPlaceholder="Search experiments..."
      />

      {/* Create Experiment Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-display">Create New Experiment</DialogTitle>
            <DialogDescription>
              Set up a new experiment to track your ML runs and metrics.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Experiment Name</Label>
              <Input
                id="name"
                placeholder="e.g., fraud-detection-v2"
                value={newExperiment.name}
                onChange={(e) =>
                  setNewExperiment({ ...newExperiment, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the goal of this experiment..."
                value={newExperiment.description}
                onChange={(e) =>
                  setNewExperiment({ ...newExperiment, description: e.target.value })
                }
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                placeholder="e.g., fraud, xgboost, production"
                value={newExperiment.tags}
                onChange={(e) =>
                  setNewExperiment({ ...newExperiment, tags: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate}>Create Experiment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
