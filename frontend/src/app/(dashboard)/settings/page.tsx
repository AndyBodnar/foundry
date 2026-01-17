'use client';

import { useState } from 'react';
import {
  Users,
  Key,
  Bell,
  Building,
  Plus,
  MoreHorizontal,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Mail,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PageHeader } from '@/components/shared/page-header';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

// Mock data
const tenant = {
  id: 't1',
  name: 'Acme Corp',
  slug: 'acme-corp',
  plan: 'Enterprise',
  status: 'ACTIVE',
  createdAt: '2024-06-15T10:00:00Z',
  quotas: {
    maxExperiments: 100,
    maxModels: 50,
    maxDeployments: 20,
    maxStorageGB: 500,
  },
  usage: {
    experiments: 47,
    models: 23,
    deployments: 8,
    storageGB: 156,
  },
};

const teamMembers = [
  {
    id: 'u1',
    name: 'John Doe',
    email: 'john.doe@acme.com',
    role: 'ADMIN',
    avatarUrl: null,
    lastActive: '2025-01-17T10:30:00Z',
    status: 'ACTIVE',
  },
  {
    id: 'u2',
    name: 'Jane Smith',
    email: 'jane.smith@acme.com',
    role: 'ML_ENGINEER',
    avatarUrl: null,
    lastActive: '2025-01-17T09:15:00Z',
    status: 'ACTIVE',
  },
  {
    id: 'u3',
    name: 'Bob Wilson',
    email: 'bob.wilson@acme.com',
    role: 'DATA_SCIENTIST',
    avatarUrl: null,
    lastActive: '2025-01-16T14:00:00Z',
    status: 'ACTIVE',
  },
  {
    id: 'u4',
    name: 'Alice Chen',
    email: 'alice.chen@acme.com',
    role: 'VIEWER',
    avatarUrl: null,
    lastActive: '2025-01-15T11:30:00Z',
    status: 'INVITED',
  },
];

const apiKeys = [
  {
    id: 'k1',
    name: 'Production API Key',
    prefix: 'fnd_prod_',
    lastUsed: '2025-01-17T10:25:00Z',
    createdAt: '2024-12-01T09:00:00Z',
    scopes: ['experiments:read', 'models:read', 'deployments:*'],
  },
  {
    id: 'k2',
    name: 'CI/CD Pipeline',
    prefix: 'fnd_cicd_',
    lastUsed: '2025-01-17T08:00:00Z',
    createdAt: '2025-01-05T14:30:00Z',
    scopes: ['experiments:*', 'models:*'],
  },
  {
    id: 'k3',
    name: 'Monitoring Service',
    prefix: 'fnd_mon_',
    lastUsed: '2025-01-17T10:30:00Z',
    createdAt: '2025-01-10T11:00:00Z',
    scopes: ['monitoring:read'],
  },
];

function getRoleColor(role: string) {
  switch (role) {
    case 'ADMIN':
      return 'bg-destructive/10 text-destructive border-destructive/30';
    case 'ML_ENGINEER':
      return 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30';
    case 'DATA_SCIENTIST':
      return 'bg-neon-purple/10 text-neon-purple border-neon-purple/30';
    case 'VIEWER':
      return 'bg-muted text-muted-foreground border-border';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

function getRoleLabel(role: string) {
  switch (role) {
    case 'ADMIN':
      return 'Admin';
    case 'ML_ENGINEER':
      return 'ML Engineer';
    case 'DATA_SCIENTIST':
      return 'Data Scientist';
    case 'VIEWER':
      return 'Viewer';
    default:
      return role;
  }
}

export default function SettingsPage() {
  const [selectedTab, setSelectedTab] = useState('organization');
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [isKeyOpen, setIsKeyOpen] = useState(false);
  const [showKey, setShowKey] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('DATA_SCIENTIST');

  const handleInvite = () => {
    console.log('Inviting:', inviteEmail, inviteRole);
    setIsInviteOpen(false);
    setInviteEmail('');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage your organization, team, and integrations"
      />

      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="organization">
            <Building className="mr-2 h-4 w-4" />
            Organization
          </TabsTrigger>
          <TabsTrigger value="team">
            <Users className="mr-2 h-4 w-4" />
            Team
          </TabsTrigger>
          <TabsTrigger value="api-keys">
            <Key className="mr-2 h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        {/* Organization Tab */}
        <TabsContent value="organization" className="mt-6 space-y-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Organization Details</CardTitle>
              <CardDescription>Manage your organization settings and billing</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Organization Name</Label>
                  <Input value={tenant.name} />
                </div>
                <div className="space-y-2">
                  <Label>Slug</Label>
                  <Input value={tenant.slug} disabled />
                </div>
              </div>
              <div className="flex justify-between items-center pt-4 border-t border-border">
                <div>
                  <p className="text-sm font-medium">Current Plan</p>
                  <p className="text-xs text-muted-foreground">
                    Created {format(new Date(tenant.createdAt), 'MMM d, yyyy')}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className="bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30">
                    {tenant.plan}
                  </Badge>
                  <Button variant="outline" size="sm">
                    Upgrade Plan
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Usage & Quotas */}
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Usage & Quotas</CardTitle>
              <CardDescription>Monitor your resource usage against plan limits</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                {Object.entries(tenant.quotas).map(([key, max]) => {
                  const used = tenant.usage[key.replace('max', '').toLowerCase() as keyof typeof tenant.usage] || 0;
                  const percentage = Math.round((used / max) * 100);
                  const label = key.replace('max', '').replace(/([A-Z])/g, ' $1').trim();

                  return (
                    <div key={key} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="capitalize">{label}</span>
                        <span className="font-mono">
                          {used} / {max}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all',
                            percentage > 90 ? 'bg-destructive' : percentage > 70 ? 'bg-neon-yellow' : 'bg-neon-cyan'
                          )}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team" className="mt-6 space-y-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Team Members</CardTitle>
                  <CardDescription>Manage who has access to your organization</CardDescription>
                </div>
                <Button onClick={() => setIsInviteOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Invite Member
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {teamMembers.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-muted/30"
                  >
                    <div className="flex items-center gap-4">
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={member.avatarUrl || undefined} />
                        <AvatarFallback className="bg-primary/20 text-primary">
                          {member.name.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{member.name}</p>
                          {member.status === 'INVITED' && (
                            <Badge variant="outline" className="text-xs">
                              Invited
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{member.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <Badge variant="outline" className={cn('text-xs', getRoleColor(member.role))}>
                          {getRoleLabel(member.role)}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">
                          Last active {format(new Date(member.lastActive), 'MMM d, HH:mm')}
                        </p>
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
                          <DropdownMenuItem>Change Role</DropdownMenuItem>
                          <DropdownMenuItem>Resend Invite</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive">
                            Remove Member
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="mt-6 space-y-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>API Keys</CardTitle>
                  <CardDescription>Manage API keys for programmatic access</CardDescription>
                </div>
                <Button onClick={() => setIsKeyOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Key
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {apiKeys.map((key) => (
                  <div
                    key={key.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-muted/30"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-neon-cyan/10 flex items-center justify-center">
                        <Key className="h-5 w-5 text-neon-cyan" />
                      </div>
                      <div>
                        <p className="font-medium">{key.name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <code className="text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">
                            {key.prefix}••••••••
                          </code>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5"
                            onClick={() => setShowKey(showKey === key.id ? null : key.id)}
                          >
                            {showKey === key.id ? (
                              <EyeOff className="h-3 w-3" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                          </Button>
                          <Button variant="ghost" size="icon" className="h-5 w-5">
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="flex flex-wrap gap-1 justify-end max-w-[200px]">
                          {key.scopes.slice(0, 2).map((scope) => (
                            <Badge key={scope} variant="secondary" className="text-[10px] font-mono">
                              {scope}
                            </Badge>
                          ))}
                          {key.scopes.length > 2 && (
                            <Badge variant="secondary" className="text-[10px]">
                              +{key.scopes.length - 2}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Last used {format(new Date(key.lastUsed), 'MMM d, HH:mm')}
                        </p>
                      </div>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="mt-6 space-y-6">
          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>Configure how you receive alerts and updates</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-muted-foreground">
                      Receive email alerts for critical issues
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="font-medium">Slack Integration</p>
                    <p className="text-sm text-muted-foreground">
                      Send alerts to your Slack workspace
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="font-medium">PagerDuty Integration</p>
                    <p className="text-sm text-muted-foreground">
                      Trigger PagerDuty incidents for P1 alerts
                    </p>
                  </div>
                  <Switch />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="font-medium">Weekly Digest</p>
                    <p className="text-sm text-muted-foreground">
                      Receive a weekly summary of activity
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-border/50">
            <CardHeader>
              <CardTitle>Alert Rules</CardTitle>
              <CardDescription>Configure which events trigger notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { label: 'Model accuracy drops below threshold', enabled: true },
                { label: 'Data drift detected', enabled: true },
                { label: 'Deployment health degraded', enabled: true },
                { label: 'High latency detected', enabled: true },
                { label: 'Experiment completed', enabled: false },
                { label: 'New model version registered', enabled: false },
              ].map((rule) => (
                <div key={rule.label} className="flex items-center justify-between py-2">
                  <span className="text-sm">{rule.label}</span>
                  <Switch defaultChecked={rule.enabled} />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Invite Member Dialog */}
      <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="font-display">Invite Team Member</DialogTitle>
            <DialogDescription>
              Send an invitation to join your organization.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Email Address</Label>
              <Input
                type="email"
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="VIEWER">Viewer</SelectItem>
                  <SelectItem value="DATA_SCIENTIST">Data Scientist</SelectItem>
                  <SelectItem value="ML_ENGINEER">ML Engineer</SelectItem>
                  <SelectItem value="ADMIN">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsInviteOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInvite}>
              <Mail className="mr-2 h-4 w-4" />
              Send Invite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create API Key Dialog */}
      <Dialog open={isKeyOpen} onOpenChange={setIsKeyOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="font-display">Create API Key</DialogTitle>
            <DialogDescription>
              Generate a new API key for programmatic access.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Key Name</Label>
              <Input placeholder="e.g., Production API Key" />
            </div>
            <div className="space-y-2">
              <Label>Expiration</Label>
              <Select defaultValue="never">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 days</SelectItem>
                  <SelectItem value="90">90 days</SelectItem>
                  <SelectItem value="365">1 year</SelectItem>
                  <SelectItem value="never">Never</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsKeyOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setIsKeyOpen(false)}>Create Key</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
