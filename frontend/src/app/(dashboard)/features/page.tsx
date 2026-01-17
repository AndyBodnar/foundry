'use client';

import { useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import {
  Plus,
  MoreHorizontal,
  Database,
  Eye,
  Trash2,
  ArrowUpDown,
  Play,
  Clock,
  Layers,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/shared/page-header';
import { DataTable } from '@/components/shared/data-table';
import { AreaChart } from '@/components/charts/area-chart';
import { format, formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { FeatureView, MaterializationJob } from '@/types';

// Mock feature views
const featureViews: FeatureView[] = [
  {
    id: '1',
    tenantId: 't1',
    name: 'user_features',
    description: 'Core user features including demographics and behavior metrics',
    features: [
      { name: 'user_age', dtype: 'INT64', description: 'User age in years' },
      { name: 'account_age_days', dtype: 'INT64', description: 'Days since account creation' },
      { name: 'total_transactions', dtype: 'INT64', description: 'Lifetime transaction count' },
      { name: 'avg_transaction_amount', dtype: 'FLOAT64', description: 'Average transaction value' },
      { name: 'is_verified', dtype: 'BOOL', description: 'Email verification status' },
    ],
    entities: ['user_id'],
    source: { type: 'BATCH', config: { table: 'users', refresh: '1h' } },
    ttlSeconds: 86400,
    createdAt: '2024-12-01T10:00:00Z',
    updatedAt: '2025-01-17T08:00:00Z',
  },
  {
    id: '2',
    tenantId: 't1',
    name: 'transaction_features',
    description: 'Real-time transaction features for fraud detection',
    features: [
      { name: 'transaction_amount', dtype: 'FLOAT64' },
      { name: 'merchant_category', dtype: 'STRING' },
      { name: 'device_type', dtype: 'STRING' },
      { name: 'time_since_last_transaction', dtype: 'INT64' },
      { name: 'transactions_last_hour', dtype: 'INT64' },
      { name: 'unique_merchants_today', dtype: 'INT64' },
    ],
    entities: ['user_id', 'transaction_id'],
    source: { type: 'STREAM', config: { topic: 'transactions' } },
    ttlSeconds: 3600,
    createdAt: '2024-11-15T14:00:00Z',
    updatedAt: '2025-01-17T10:30:00Z',
  },
  {
    id: '3',
    tenantId: 't1',
    name: 'product_features',
    description: 'Product catalog features for recommendations',
    features: [
      { name: 'category', dtype: 'STRING' },
      { name: 'price', dtype: 'FLOAT64' },
      { name: 'rating', dtype: 'FLOAT64' },
      { name: 'review_count', dtype: 'INT64' },
      { name: 'stock_level', dtype: 'INT64' },
    ],
    entities: ['product_id'],
    source: { type: 'BATCH', config: { table: 'products', refresh: '6h' } },
    ttlSeconds: 21600,
    createdAt: '2024-10-20T09:00:00Z',
    updatedAt: '2025-01-16T16:00:00Z',
  },
];

// Mock materialization jobs
const materializationJobs: MaterializationJob[] = [
  {
    id: 'j1',
    featureViewId: '1',
    status: 'COMPLETED',
    startTime: '2025-01-17T08:00:00Z',
    endTime: '2025-01-17T08:05:00Z',
    recordsProcessed: 1250000,
  },
  {
    id: 'j2',
    featureViewId: '2',
    status: 'RUNNING',
    startTime: '2025-01-17T10:00:00Z',
    recordsProcessed: 450000,
  },
  {
    id: 'j3',
    featureViewId: '1',
    status: 'COMPLETED',
    startTime: '2025-01-17T07:00:00Z',
    endTime: '2025-01-17T07:04:00Z',
    recordsProcessed: 1248000,
  },
  {
    id: 'j4',
    featureViewId: '3',
    status: 'FAILED',
    startTime: '2025-01-17T06:00:00Z',
    endTime: '2025-01-17T06:02:00Z',
    errorMessage: 'Connection timeout to source database',
  },
];

// Mock freshness data
const freshnessData = [
  { time: '00:00', user_features: 98, transaction_features: 99, product_features: 95 },
  { time: '04:00', user_features: 97, transaction_features: 99, product_features: 94 },
  { time: '08:00', user_features: 99, transaction_features: 99, product_features: 96 },
  { time: '12:00', user_features: 98, transaction_features: 99, product_features: 95 },
  { time: '16:00', user_features: 97, transaction_features: 99, product_features: 94 },
  { time: '20:00', user_features: 96, transaction_features: 99, product_features: 93 },
  { time: 'Now', user_features: 99, transaction_features: 99, product_features: 97 },
];

const columns: ColumnDef<FeatureView>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Feature View
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-neon-cyan/10 flex items-center justify-center">
          <Database className="h-5 w-5 text-neon-cyan" />
        </div>
        <div>
          <p className="font-medium font-mono">{row.original.name}</p>
          <p className="text-xs text-muted-foreground max-w-[300px] truncate">
            {row.original.description}
          </p>
        </div>
      </div>
    ),
  },
  {
    accessorKey: 'source.type',
    header: 'Source',
    cell: ({ row }) => (
      <Badge
        variant="outline"
        className={cn(
          'font-mono text-xs',
          row.original.source.type === 'STREAM'
            ? 'border-neon-cyan/30 text-neon-cyan'
            : 'border-border'
        )}
      >
        {row.original.source.type}
      </Badge>
    ),
  },
  {
    accessorKey: 'features',
    header: 'Features',
    cell: ({ row }) => (
      <span className="font-mono">{row.original.features.length}</span>
    ),
  },
  {
    accessorKey: 'entities',
    header: 'Entities',
    cell: ({ row }) => (
      <div className="flex gap-1">
        {row.original.entities.map((entity) => (
          <Badge key={entity} variant="secondary" className="font-mono text-xs">
            {entity}
          </Badge>
        ))}
      </div>
    ),
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
        {formatDistanceToNow(new Date(row.original.updatedAt), { addSuffix: true })}
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
            <Play className="mr-2 h-4 w-4" />
            Materialize Now
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Layers className="mr-2 h-4 w-4" />
            View Statistics
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

function getJobStatusIcon(status: string) {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle className="h-4 w-4 text-neon-green" />;
    case 'RUNNING':
      return <Loader2 className="h-4 w-4 text-neon-cyan animate-spin" />;
    case 'FAILED':
      return <XCircle className="h-4 w-4 text-destructive" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

export default function FeaturesPage() {
  const [selectedTab, setSelectedTab] = useState('views');
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feature Store"
        description="Manage feature definitions and materialization"
        action={{
          label: 'New Feature View',
          icon: Plus,
          onClick: () => setIsCreateOpen(true),
        }}
      />

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">{featureViews.length}</div>
                <p className="text-xs text-muted-foreground">Feature Views</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-cyan/10">
                <Database className="h-5 w-5 text-neon-cyan" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">
                  {featureViews.reduce((acc, fv) => acc + fv.features.length, 0)}
                </div>
                <p className="text-xs text-muted-foreground">Total Features</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-purple/10">
                <Layers className="h-5 w-5 text-neon-purple" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono text-neon-green">98.5%</div>
                <p className="text-xs text-muted-foreground">Avg Freshness</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-green/10">
                <RefreshCw className="h-5 w-5 text-neon-green" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass border-border/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold font-mono">
                  {materializationJobs.filter((j) => j.status === 'RUNNING').length}
                </div>
                <p className="text-xs text-muted-foreground">Running Jobs</p>
              </div>
              <div className="p-3 rounded-lg bg-neon-orange/10">
                <Play className="h-5 w-5 text-neon-orange" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="views">Feature Views</TabsTrigger>
          <TabsTrigger value="jobs">Materialization Jobs</TabsTrigger>
          <TabsTrigger value="freshness">Freshness</TabsTrigger>
        </TabsList>

        <TabsContent value="views" className="mt-6">
          <DataTable
            columns={columns}
            data={featureViews}
            searchKey="name"
            searchPlaceholder="Search feature views..."
          />
        </TabsContent>

        <TabsContent value="jobs" className="mt-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle className="text-base font-medium">Recent Materialization Jobs</CardTitle>
              <CardDescription>View and manage feature materialization history</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {materializationJobs.map((job) => {
                  const featureView = featureViews.find((fv) => fv.id === job.featureViewId);
                  return (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-4 rounded-lg bg-muted/30"
                    >
                      <div className="flex items-center gap-4">
                        {getJobStatusIcon(job.status)}
                        <div>
                          <p className="font-mono font-medium">{featureView?.name}</p>
                          <p className="text-xs text-muted-foreground">
                            Started {format(new Date(job.startTime), 'MMM d, HH:mm')}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        {job.recordsProcessed !== undefined && (
                          <div className="text-right">
                            <p className="font-mono text-sm">
                              {job.recordsProcessed.toLocaleString()}
                            </p>
                            <p className="text-xs text-muted-foreground">records</p>
                          </div>
                        )}
                        {job.endTime && (
                          <div className="text-right">
                            <p className="font-mono text-sm">
                              {Math.round(
                                (new Date(job.endTime).getTime() -
                                  new Date(job.startTime).getTime()) /
                                  1000
                              )}s
                            </p>
                            <p className="text-xs text-muted-foreground">duration</p>
                          </div>
                        )}
                        <Badge
                          variant="outline"
                          className={cn(
                            'font-mono text-xs',
                            job.status === 'COMPLETED' && 'border-neon-green/30 text-neon-green',
                            job.status === 'RUNNING' && 'border-neon-cyan/30 text-neon-cyan',
                            job.status === 'FAILED' && 'border-destructive/30 text-destructive'
                          )}
                        >
                          {job.status}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="freshness" className="mt-6">
          <AreaChart
            title="Feature Freshness"
            description="Percentage of up-to-date features over time"
            data={freshnessData}
            dataKey="user_features"
            xAxisKey="time"
            color="#00ff88"
            height={350}
          />
        </TabsContent>
      </Tabs>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-display">Create Feature View</DialogTitle>
            <DialogDescription>
              Define a new feature view to serve features for your models.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input placeholder="e.g., user_transaction_features" />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea placeholder="Describe the feature view..." rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Source Type</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Select source type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BATCH">Batch</SelectItem>
                  <SelectItem value="STREAM">Stream</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Entities (comma-separated)</Label>
              <Input placeholder="e.g., user_id, product_id" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setIsCreateOpen(false)}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
