'use client';

import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/app-store';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { CommandPalette } from './command-palette';
import { Toaster } from '@/components/ui/sonner';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { sidebarCollapsed } = useAppStore();

  return (
    <div className="min-h-screen bg-background bg-grid">
      <Sidebar />
      <Header />
      <CommandPalette />

      <main
        className={cn(
          'min-h-screen pt-16 transition-all duration-300',
          sidebarCollapsed ? 'pl-[72px]' : 'pl-64'
        )}
      >
        <div className="container mx-auto p-6">
          {children}
        </div>
      </main>

      <Toaster />
    </div>
  );
}
