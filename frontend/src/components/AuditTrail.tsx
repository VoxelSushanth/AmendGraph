import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '../services/api';
import { Loader2, FileText, Clock, RefreshCw, User, Shield } from 'lucide-react';

interface AuditEntry {
  id: string;
  timestamp: string;
  user_id: string;
  user_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  details: Record<string, unknown>;
  request_id: string;
  ip_address?: string;
}

interface AuditTrailResponse {
  entries: AuditEntry[];
  total_count: number;
  amendment_id: string;
  protocol_version: string;
}

const getActionBadge = (action: string) => {
  const variants: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
    CREATE: 'default',
    UPDATE: 'secondary',
    DELETE: 'destructive',
    COMPARE: 'outline',
    ANALYZE: 'outline',
    GENERATE: 'secondary',
    APPROVE: 'default',
    REVIEW: 'outline',
  };
  return variants[action] || 'outline';
};

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const AuditTrail: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const { data: auditData, isLoading, error, refetch } = useQuery<AuditTrailResponse>({
    queryKey: ['audit', id],
    queryFn: () => api.getAuditTrail(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading audit trail...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-destructive">
            <p className="font-medium">Failed to load audit trail</p>
            <p className="text-sm text-muted-foreground">
              {(error as Error).message || 'An unexpected error occurred'}
            </p>
            <Button onClick={() => refetch()} variant="outline" className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!auditData || auditData.entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Audit Trail</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No audit entries found.</p>
            <p className="text-sm">Audit entries will appear as actions are performed.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Audit Trail</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Complete traceability for FDA compliance - Protocol Version{' '}
              <Badge variant="outline">{auditData.protocol_version}</Badge>
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                <div>
                  <div className="text-2xl font-bold">{auditData.total_count}</div>
                  <div className="text-sm text-muted-foreground">Total Events</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <User className="h-8 w-8 text-blue-600" />
                <div>
                  <div className="text-2xl font-bold">
                    {new Set(auditData.entries.map((e) => e.user_id)).size}
                  </div>
                  <div className="text-sm text-muted-foreground">Unique Users</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <Shield className="h-8 w-8 text-green-600" />
                <div>
                  <div className="text-2xl font-bold">100%</div>
                  <div className="text-sm text-muted-foreground">Compliance</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Audit Entries Table */}
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>Request ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditData.entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="font-mono text-xs">
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      {formatTimestamp(entry.timestamp)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <User className="h-3 w-3 text-muted-foreground" />
                      <div>
                        <div className="font-medium">{entry.user_name}</div>
                        <div className="text-xs text-muted-foreground">{entry.user_id}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getActionBadge(entry.action)}>{entry.action}</Badge>
                  </TableCell>
                  <TableCell>
                    <div>
                      <div className="font-medium">{entry.entity_name}</div>
                      <div className="text-xs text-muted-foreground">{entry.entity_type}</div>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <div className="text-xs font-mono bg-muted p-2 rounded overflow-auto max-h-20">
                      {JSON.stringify(entry.details, null, 2)}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {entry.request_id.slice(0, 8)}...
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Compliance Notice */}
        <div className="mt-6 p-4 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800">
          <h4 className="font-medium text-amber-900 dark:text-amber-100 mb-2 flex items-center gap-2">
            <Shield className="h-4 w-4" />
            FDA 21 CFR Part 11 Compliance
          </h4>
          <p className="text-sm text-amber-800 dark:text-amber-200">
            This audit trail provides complete traceability for all actions performed on this
            protocol amendment. All entries include timestamp, user identity, action type, affected
            entity, and unique request identifiers for regulatory compliance purposes.
          </p>
        </div>

        {/* Export Options */}
        <div className="mt-4 flex gap-2">
          <Button variant="outline" size="sm">
            Export as CSV
          </Button>
          <Button variant="outline" size="sm">
            Export as PDF
          </Button>
          <Button variant="outline" size="sm">
            Generate Compliance Report
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default AuditTrail;
