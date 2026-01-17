'use client';

import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/app-store';
import {
  Bell,
  Search,
  HelpCircle,
  ChevronDown,
  AlertTriangle,
  CheckCircle,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';

// Breadcrumb titles
const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/experiments': 'Experiments',
  '/models': 'Model Registry',
  '/features': 'Feature Store',
  '/deployments': 'Deployments',
  '/monitoring': 'Monitoring',
  '/settings': 'Settings',
};

// Mock notifications
const notifications = [
  {
    id: '1',
    type: 'alert' as const,
    title: 'High latency detected',
    message: 'Deployment "fraud-detector" experiencing p99 > 500ms',
    time: '5 min ago',
    unread: true,
  },
  {
    id: '2',
    type: 'success' as const,
    title: 'Model deployed successfully',
    message: 'fraud-model-v3 is now live in production',
    time: '1 hour ago',
    unread: true,
  },
  {
    id: '3',
    type: 'info' as const,
    title: 'Experiment completed',
    message: 'xgboost-tuning completed with 94.5% accuracy',
    time: '2 hours ago',
    unread: false,
  },
];

function getNotificationIcon(type: 'alert' | 'success' | 'info') {
  switch (type) {
    case 'alert':
      return <AlertTriangle className="h-4 w-4 text-destructive" />;
    case 'success':
      return <CheckCircle className="h-4 w-4 text-neon-green" />;
    case 'info':
      return <Info className="h-4 w-4 text-primary" />;
  }
}

export function Header() {
  const pathname = usePathname();
  const { sidebarCollapsed, tenant, setCommandPaletteOpen } = useAppStore();

  // Get page title
  const getPageTitle = () => {
    const exactMatch = pageTitles[pathname];
    if (exactMatch) return exactMatch;

    // Check for nested routes
    for (const [path, title] of Object.entries(pageTitles)) {
      if (pathname.startsWith(path) && path !== '/') {
        return title;
      }
    }
    return 'Dashboard';
  };

  const unreadCount = notifications.filter((n) => n.unread).length;

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-16 border-b border-border bg-background/80 backdrop-blur-xl',
        'transition-all duration-300',
        sidebarCollapsed ? 'left-[72px]' : 'left-64'
      )}
    >
      <div className="flex h-full items-center justify-between px-6">
        {/* Left side - Breadcrumb */}
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-lg font-semibold">{getPageTitle()}</h1>
            {tenant && (
              <p className="text-xs text-muted-foreground">
                {tenant.name}
              </p>
            )}
          </div>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 text-muted-foreground hover:text-foreground"
            onClick={() => setCommandPaletteOpen(true)}
          >
            <Search className="h-5 w-5" />
          </Button>

          {/* Help */}
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 text-muted-foreground hover:text-foreground"
          >
            <HelpCircle className="h-5 w-5" />
          </Button>

          {/* Notifications */}
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-9 w-9 text-muted-foreground hover:text-foreground relative"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-white">
                    {unreadCount}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80 p-0">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <h4 className="text-sm font-semibold">Notifications</h4>
                <Button variant="ghost" size="sm" className="h-auto py-1 px-2 text-xs">
                  Mark all read
                </Button>
              </div>
              <ScrollArea className="h-[300px]">
                <div className="divide-y divide-border">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={cn(
                        'flex gap-3 px-4 py-3 hover:bg-muted/50 transition-colors cursor-pointer',
                        notification.unread && 'bg-primary/5'
                      )}
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{notification.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {notification.message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {notification.time}
                        </p>
                      </div>
                      {notification.unread && (
                        <div className="flex-shrink-0">
                          <div className="h-2 w-2 rounded-full bg-primary" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
              <div className="border-t border-border px-4 py-2">
                <Button variant="ghost" size="sm" className="w-full">
                  View all notifications
                </Button>
              </div>
            </PopoverContent>
          </Popover>

          {/* Environment Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <div className="h-2 w-2 rounded-full bg-neon-green" />
                Production
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Environment</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <div className="h-2 w-2 rounded-full bg-neon-green mr-2" />
                Production
              </DropdownMenuItem>
              <DropdownMenuItem>
                <div className="h-2 w-2 rounded-full bg-neon-yellow mr-2" />
                Staging
              </DropdownMenuItem>
              <DropdownMenuItem>
                <div className="h-2 w-2 rounded-full bg-neon-cyan mr-2" />
                Development
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
