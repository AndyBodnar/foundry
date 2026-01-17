"""Initial database schema.

Revision ID: 0001
Revises:
Create Date: 2025-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extension for UUID generation
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ========================================================================
    # Tenants & Users
    # ========================================================================

    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('status', sa.String(50), server_default='ACTIVE'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('quotas', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_superuser', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'tenant_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), server_default='VIEWER'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user'),
    )

    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('hashed_key', sa.String(255), nullable=False, unique=True),
        sa.Column('prefix', sa.String(20), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # ========================================================================
    # Experiments
    # ========================================================================

    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_experiment_name'),
    )
    op.create_index('ix_experiments_tenant_id', 'experiments', ['tenant_id'])
    op.create_index('ix_experiments_tenant_name', 'experiments', ['tenant_id', 'name'])

    op.create_table(
        'runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), server_default='PENDING'),
        sa.Column('parameters', postgresql.JSONB, server_default='{}'),
        sa.Column('metrics', postgresql.JSONB, server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('git_commit', sa.String(40), nullable=True),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_runs_experiment_id', 'runs', ['experiment_id'])
    op.create_index('ix_runs_experiment_status', 'runs', ['experiment_id', 'status'])
    op.create_index('ix_runs_tenant_id', 'runs', ['tenant_id'])

    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('path', sa.Text, nullable=False),
        sa.Column('size_bytes', sa.Integer, nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('artifact_metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_artifacts_run_id', 'artifacts', ['run_id'])

    op.create_table(
        'metric_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('step', sa.Integer, server_default='0'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_metric_history_run_id', 'metric_history', ['run_id'])
    op.create_index('ix_metric_history_run_key', 'metric_history', ['run_id', 'key'])

    # ========================================================================
    # Model Registry
    # ========================================================================

    op.create_table(
        'registered_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_model_name'),
    )
    op.create_index('ix_registered_models_name', 'registered_models', ['name'])

    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('registered_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('stage', sa.String(50), server_default='NONE'),
        sa.Column('artifact_path', sa.Text, nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metrics', postgresql.JSONB, server_default='{}'),
        sa.Column('signature', postgresql.JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('model_id', 'version', name='uq_model_version'),
    )
    op.create_index('ix_model_versions_model_id', 'model_versions', ['model_id'])
    op.create_index('ix_model_versions_model_stage', 'model_versions', ['model_id', 'stage'])

    op.create_table(
        'stage_transitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_stage', sa.String(50), nullable=False),
        sa.Column('to_stage', sa.String(50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_stage_transitions_model_version_id', 'stage_transitions', ['model_version_id'])

    # ========================================================================
    # Deployments
    # ========================================================================

    op.create_table(
        'deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), server_default='PENDING'),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('traffic_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('endpoint_url', sa.Text, nullable=True),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('replicas', sa.Integer, server_default='1'),
        sa.Column('min_replicas', sa.Integer, server_default='1'),
        sa.Column('max_replicas', sa.Integer, server_default='10'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_deployment_name'),
    )
    op.create_index('ix_deployments_name', 'deployments', ['name'])
    op.create_index('ix_deployments_status', 'deployments', ['status'])

    op.create_table(
        'ab_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deployments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='RUNNING'),
        sa.Column('control_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('treatment_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('control_traffic_percent', sa.Integer, server_default='50'),
        sa.Column('treatment_traffic_percent', sa.Integer, server_default='50'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('winner_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metrics', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_ab_tests_deployment_id', 'ab_tests', ['deployment_id'])

    # ========================================================================
    # Monitoring
    # ========================================================================

    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deployments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metric', sa.String(255), nullable=False),
        sa.Column('condition', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Float, nullable=False),
        sa.Column('severity', sa.String(50), server_default='WARNING'),
        sa.Column('notification_channels', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('cooldown_minutes', sa.Integer, server_default='15'),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_alert_rules_deployment_id', 'alert_rules', ['deployment_id'])

    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deployments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('threshold_value', sa.Float, nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('acknowledged', sa.Boolean, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_alerts_rule_id', 'alerts', ['rule_id'])

    # ========================================================================
    # Pipelines
    # ========================================================================

    op.create_table(
        'pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('dag_definition', postgresql.JSONB, nullable=False),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_pipeline_name'),
    )
    op.create_index('ix_pipelines_name', 'pipelines', ['name'])

    op.create_table(
        'pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), server_default='PENDING'),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parameters', postgresql.JSONB, server_default='{}'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pipeline_runs_pipeline_id', 'pipeline_runs', ['pipeline_id'])
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])

    op.create_table(
        'pipeline_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('pipeline_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='PENDING'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('logs', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_pipeline_tasks_pipeline_run_id', 'pipeline_tasks', ['pipeline_run_id'])

    # ========================================================================
    # Feature Store
    # ========================================================================

    op.create_table(
        'feature_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('entities', postgresql.ARRAY(sa.String), nullable=False),
        sa.Column('features', postgresql.JSONB, nullable=False),
        sa.Column('source_config', postgresql.JSONB, nullable=False),
        sa.Column('ttl_seconds', sa.Integer, nullable=True),
        sa.Column('online_enabled', sa.Boolean, server_default='true'),
        sa.Column('offline_enabled', sa.Boolean, server_default='true'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_feature_view_name'),
    )
    op.create_index('ix_feature_views_name', 'feature_views', ['name'])

    # ========================================================================
    # Audit Log
    # ========================================================================

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSONB, server_default='{}'),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_audit_logs_tenant_timestamp', 'audit_logs', ['tenant_id', 'timestamp'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('feature_views')
    op.drop_table('pipeline_tasks')
    op.drop_table('pipeline_runs')
    op.drop_table('pipelines')
    op.drop_table('alerts')
    op.drop_table('alert_rules')
    op.drop_table('ab_tests')
    op.drop_table('deployments')
    op.drop_table('stage_transitions')
    op.drop_table('model_versions')
    op.drop_table('registered_models')
    op.drop_table('metric_history')
    op.drop_table('artifacts')
    op.drop_table('runs')
    op.drop_table('experiments')
    op.drop_table('api_keys')
    op.drop_table('tenant_memberships')
    op.drop_table('users')
    op.drop_table('tenants')
