// Core types for Foundry MLOps Platform

// Status types
export type ExperimentStatus = 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PENDING' | 'CANCELLED';
export type ModelStage = 'NONE' | 'STAGING' | 'PRODUCTION' | 'ARCHIVED';
export type DeploymentStatus = 'PENDING' | 'DEPLOYING' | 'RUNNING' | 'FAILED' | 'STOPPED';
export type AlertSeverity = 'P1' | 'P2' | 'P3' | 'P4';
export type DriftStatus = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

// User & Tenant
export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  role: 'VIEWER' | 'DATA_SCIENTIST' | 'ML_ENGINEER' | 'ADMIN';
  isActive: boolean;
  createdAt: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'INACTIVE';
  settings: Record<string, unknown>;
  quotas: TenantQuotas;
  createdAt: string;
}

export interface TenantQuotas {
  maxExperiments: number;
  maxModels: number;
  maxDeployments: number;
  maxStorageGB: number;
  maxInferenceRequests: number;
}

// Experiments
export interface Experiment {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  tags: string[];
  runsCount: number;
  bestMetric?: number;
  bestMetricName?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Run {
  id: string;
  experimentId: string;
  tenantId: string;
  name?: string;
  status: ExperimentStatus;
  parameters: Record<string, unknown>;
  metrics: Record<string, number>;
  startTime: string;
  endTime?: string;
  duration?: number;
  user?: string;
  tags?: string[];
}

export interface MetricHistory {
  runId: string;
  metricName: string;
  values: { step: number; value: number; timestamp: string }[];
}

export interface Artifact {
  id: string;
  runId: string;
  name: string;
  path: string;
  size: number;
  contentType: string;
  createdAt: string;
}

// Model Registry
export interface RegisteredModel {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  latestVersion?: string;
  versionsCount: number;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ModelVersion {
  id: string;
  modelId: string;
  tenantId: string;
  version: string;
  stage: ModelStage;
  artifactPath: string;
  metrics: Record<string, number>;
  runId?: string;
  description?: string;
  createdAt: string;
  createdBy?: string;
}

export interface StageTransition {
  id: string;
  modelVersionId: string;
  fromStage: ModelStage;
  toStage: ModelStage;
  userId: string;
  comment?: string;
  createdAt: string;
}

// Feature Store
export interface FeatureView {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  features: Feature[];
  entities: string[];
  source: FeatureSource;
  ttlSeconds?: number;
  createdAt: string;
  updatedAt: string;
}

export interface Feature {
  name: string;
  dtype: 'INT64' | 'FLOAT64' | 'STRING' | 'BOOL' | 'TIMESTAMP';
  description?: string;
  tags?: string[];
}

export interface FeatureSource {
  type: 'BATCH' | 'STREAM';
  config: Record<string, unknown>;
}

export interface MaterializationJob {
  id: string;
  featureViewId: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  startTime: string;
  endTime?: string;
  recordsProcessed?: number;
  errorMessage?: string;
}

// Deployments
export interface Deployment {
  id: string;
  tenantId: string;
  name: string;
  status: DeploymentStatus;
  endpoint?: string;
  config: DeploymentConfig;
  trafficConfig: TrafficConfig;
  healthStatus?: HealthStatus;
  createdAt: string;
  updatedAt: string;
}

export interface DeploymentConfig {
  replicas: number;
  minReplicas?: number;
  maxReplicas?: number;
  cpuRequest: string;
  memoryRequest: string;
  cpuLimit: string;
  memoryLimit: string;
  gpuCount?: number;
}

export interface TrafficConfig {
  versions: TrafficVersion[];
}

export interface TrafficVersion {
  modelVersionId: string;
  modelName: string;
  version: string;
  weight: number;
}

export interface HealthStatus {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  replicas: { ready: number; total: number };
  lastCheck: string;
  latencyP50Ms?: number;
  latencyP99Ms?: number;
  errorRate?: number;
}

export interface ABTest {
  id: string;
  deploymentId: string;
  name: string;
  status: 'RUNNING' | 'COMPLETED' | 'CANCELLED';
  controlVersionId: string;
  treatmentVersionId: string;
  trafficSplit: number;
  primaryMetric: string;
  startTime: string;
  endTime?: string;
  results?: ABTestResults;
}

export interface ABTestResults {
  controlMetric: number;
  treatmentMetric: number;
  uplift: number;
  pValue: number;
  isSignificant: boolean;
  sampleSize: { control: number; treatment: number };
}

// Monitoring
export interface DriftScore {
  time: string;
  deploymentId: string;
  featureName: string;
  driftScore: number;
  driftMethod: 'KS' | 'PSI' | 'WASSERSTEIN' | 'CHI_SQUARE';
  status: DriftStatus;
}

export interface Alert {
  id: string;
  tenantId: string;
  deploymentId?: string;
  ruleId: string;
  severity: AlertSeverity;
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
  title: string;
  message: string;
  triggeredAt: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  acknowledgedBy?: string;
}

export interface AlertRule {
  id: string;
  tenantId: string;
  deploymentId?: string;
  name: string;
  metric: string;
  condition: 'GT' | 'GTE' | 'LT' | 'LTE' | 'EQ';
  threshold: number;
  severity: AlertSeverity;
  enabled: boolean;
  channels: string[];
}

export interface PerformanceMetric {
  time: string;
  deploymentId: string;
  latencyP50Ms: number;
  latencyP95Ms: number;
  latencyP99Ms: number;
  throughput: number;
  errorRate: number;
  requestCount: number;
}

// Pipelines
export interface Pipeline {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  schedule?: string;
  status: 'ACTIVE' | 'PAUSED';
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
}

export interface PipelineRun {
  id: string;
  pipelineId: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  startTime: string;
  endTime?: string;
  triggeredBy: 'SCHEDULE' | 'MANUAL' | 'DRIFT' | 'API';
  tasks: PipelineTask[];
}

export interface PipelineTask {
  id: string;
  name: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
  startTime?: string;
  endTime?: string;
  errorMessage?: string;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// Dashboard stats
export interface DashboardStats {
  experimentsCount: number;
  modelsCount: number;
  deploymentsCount: number;
  activeAlerts: number;
  inferenceRequests24h: number;
  avgLatencyMs: number;
  errorRate: number;
  driftWarnings: number;
}

// Activity feed
export interface Activity {
  id: string;
  type: 'EXPERIMENT_CREATED' | 'RUN_COMPLETED' | 'MODEL_REGISTERED' | 'MODEL_DEPLOYED' | 'ALERT_TRIGGERED' | 'DRIFT_DETECTED';
  title: string;
  description: string;
  resourceType: string;
  resourceId: string;
  userId?: string;
  userName?: string;
  createdAt: string;
}
