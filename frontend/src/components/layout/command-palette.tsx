'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  LayoutDashboard,
  FlaskConical,
  Box,
  Database,
  Rocket,
  Activity,
  Settings,
  Plus,
  AlertTriangle,
} from 'lucide-react';

const pages = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, keywords: ['home', 'overview'] },
  { name: 'Experiments', href: '/experiments', icon: FlaskConical, keywords: ['runs', 'training'] },
  { name: 'Models', href: '/models', icon: Box, keywords: ['registry', 'versions'] },
  { name: 'Features', href: '/features', icon: Database, keywords: ['store', 'data'] },
  { name: 'Deployments', href: '/deployments', icon: Rocket, keywords: ['serving', 'inference'] },
  { name: 'Monitoring', href: '/monitoring', icon: Activity, keywords: ['drift', 'alerts'] },
  { name: 'Settings', href: '/settings', icon: Settings, keywords: ['config', 'team'] },
];

const quickActions = [
  { name: 'Create Experiment', action: 'new-experiment', icon: Plus, keywords: ['add'] },
  { name: 'Register Model', action: 'new-model', icon: Plus, keywords: ['add'] },
  { name: 'New Deployment', action: 'new-deployment', icon: Rocket, keywords: ['deploy', 'add'] },
  { name: 'View Active Alerts', action: 'alerts', icon: AlertTriangle, keywords: ['warnings'] },
];

// Mock recent items
const recentItems = [
  { name: 'fraud-detection-v3', type: 'Model', href: '/models/fraud-detection', icon: Box },
  { name: 'xgboost-tuning', type: 'Experiment', href: '/experiments/xgboost-tuning', icon: FlaskConical },
  { name: 'churn-predictor', type: 'Deployment', href: '/deployments/churn-predictor', icon: Rocket },
];

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, setCommandPaletteOpen } = useAppStore();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  const handleSelect = (value: string) => {
    setCommandPaletteOpen(false);

    // Check if it's a page navigation
    const page = pages.find((p) => p.href === value);
    if (page) {
      router.push(page.href);
      return;
    }

    // Check recent items
    const recent = recentItems.find((r) => r.href === value);
    if (recent) {
      router.push(recent.href);
      return;
    }

    // Handle quick actions
    switch (value) {
      case 'new-experiment':
        router.push('/experiments?new=true');
        break;
      case 'new-model':
        router.push('/models?new=true');
        break;
      case 'new-deployment':
        router.push('/deployments?new=true');
        break;
      case 'alerts':
        router.push('/monitoring?tab=alerts');
        break;
    }
  };

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <Command className="rounded-lg border-0 bg-popover">
        <CommandInput placeholder="Search pages, models, experiments..." className="border-0" />
        <CommandList className="max-h-[400px]">
          <CommandEmpty>No results found.</CommandEmpty>

          {/* Recent */}
          <CommandGroup heading="Recent">
            {recentItems.map((item) => (
              <CommandItem
                key={item.href}
                value={item.href}
                onSelect={handleSelect}
                className="gap-3"
              >
                <item.icon className="h-4 w-4 text-muted-foreground" />
                <span>{item.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">{item.type}</span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          {/* Quick Actions */}
          <CommandGroup heading="Quick Actions">
            {quickActions.map((action) => (
              <CommandItem
                key={action.action}
                value={action.action}
                onSelect={handleSelect}
                className="gap-3"
              >
                <action.icon className="h-4 w-4 text-primary" />
                <span>{action.name}</span>
              </CommandItem>
            ))}
          </CommandGroup>

          <CommandSeparator />

          {/* Pages */}
          <CommandGroup heading="Pages">
            {pages.map((page) => (
              <CommandItem
                key={page.href}
                value={page.href}
                onSelect={handleSelect}
                className="gap-3"
              >
                <page.icon className="h-4 w-4 text-muted-foreground" />
                <span>{page.name}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
