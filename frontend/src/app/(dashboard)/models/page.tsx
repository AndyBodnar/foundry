'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ColumnDef } from '@tanstack/react-table';
import {
  Plus,
  MoreHorizontal,
  Box,
  Eye,
  Trash2,
  ArrowUpDown,
  GitBranch,
  Rocket,
  History,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { PageHeader } from '@/components/shared/page-header';
import { DataTable } from '@/components/shared/data-table';
import { format } from 'date-fns';
import type { RegisteredModel } from '@/types';

// Data placeholder - connect to API for real data
const models: RegisteredModel[] = [];

const columns: ColumnDef<RegisteredModel>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Model
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <Link
        href={`/models/${row.original.id}`}
        className="flex items-center gap-3 group"
      >
        <div className="h-10 w-10 rounded-lg bg-neon-purple/10 flex items-center justify-center group-hover:bg-neon-purple/20 transition-colors">
          <Box className="h-5 w-5 text-neon-purple" />
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
    accessorKey: 'latestVersion',
    header: 'Latest Version',
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-muted-foreground" />
        <span className="font-mono">{row.original.latestVersion}</span>
      </div>
    ),
  },
  {
    accessorKey: 'versionsCount',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-4"
      >
        Versions
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => (
      <span className="font-mono">{row.original.versionsCount}</span>
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
        {format(new Date(row.original.updatedAt), 'MMM d, yyyy')}
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
            <Link href={`/models/${row.original.id}`}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Rocket className="mr-2 h-4 w-4" />
            Deploy
          </DropdownMenuItem>
          <DropdownMenuItem>
            <History className="mr-2 h-4 w-4" />
            Version History
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

export default function ModelsPage() {
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [newModel, setNewModel] = useState({
    name: '',
    description: '',
    tags: '',
  });

  const handleRegister = () => {
    console.log('Registering model:', newModel);
    setIsRegisterOpen(false);
    setNewModel({ name: '', description: '', tags: '' });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Registry"
        description="Manage and version your ML models"
        action={{
          label: 'Register Model',
          icon: Plus,
          onClick: () => setIsRegisterOpen(true),
        }}
      />

      <DataTable
        columns={columns}
        data={models}
        searchKey="name"
        searchPlaceholder="Search models..."
      />

      {/* Register Model Dialog */}
      <Dialog open={isRegisterOpen} onOpenChange={setIsRegisterOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-display">Register New Model</DialogTitle>
            <DialogDescription>
              Register a new model to start tracking versions and deployments.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Model Name</Label>
              <Input
                id="name"
                placeholder="e.g., fraud-detector"
                value={newModel.name}
                onChange={(e) =>
                  setNewModel({ ...newModel, name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the model and its use case..."
                value={newModel.description}
                onChange={(e) =>
                  setNewModel({ ...newModel, description: e.target.value })
                }
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                placeholder="e.g., fraud, xgboost, production"
                value={newModel.tags}
                onChange={(e) =>
                  setNewModel({ ...newModel, tags: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRegisterOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRegister}>Register Model</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
