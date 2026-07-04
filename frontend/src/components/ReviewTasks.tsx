import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { Loader2, CheckCircle2, Clock, AlertCircle, RefreshCw, UserCheck } from 'lucide-react';

interface ReviewTask {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  action_required: string;
  owner: string;
  priority: string;
  status: 'pending' | 'in_progress' | 'completed';
  estimated_hours: number;
  due_date?: string;
  created_at: string;
}

interface ReviewPlanResponse {
  tasks: ReviewTask[];
  total_estimated_hours: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

const getPriorityBadge = (priority: string) => {
  const variants: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
    Critical: 'destructive',
    High: 'default',
    Medium: 'secondary',
    Low: 'outline',
  };
  return variants[priority] || 'outline';
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case 'in_progress':
      return <Clock className="h-4 w-4 text-blue-600" />;
    default:
      return <AlertCircle className="h-4 w-4 text-yellow-600" />;
  }
};

const ReviewTasks: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: reviewData, isLoading, error, refetch } = useQuery<ReviewPlanResponse>({
    queryKey: ['review-plan', id],
    queryFn: () => api.generateReviewPlan(id!),
    enabled: !!id,
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: string }) =>
      api.updateTaskStatus(taskId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-plan', id] });
    },
  });

  const handleStatusChange = (taskId: string, newStatus: string) => {
    updateTaskMutation.mutate({ taskId, status: newStatus });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading review tasks...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-destructive">
            <p className="font-medium">Failed to load review tasks</p>
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

  if (!reviewData || reviewData.tasks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Review Tasks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            <UserCheck className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No review tasks generated yet.</p>
            <p className="text-sm">Generate a review plan to see actionable tasks.</p>
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
            <CardTitle>Review Tasks</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Actionable tasks for addressing amendment impacts
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{reviewData.tasks.length}</div>
              <div className="text-sm text-muted-foreground">Total Tasks</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-red-600">{reviewData.critical_count}</div>
              <div className="text-sm text-muted-foreground">Critical</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-orange-600">{reviewData.high_count}</div>
              <div className="text-sm text-muted-foreground">High</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-yellow-600">{reviewData.medium_count}</div>
              <div className="text-sm text-muted-foreground">Medium</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-green-600">{reviewData.low_count}</div>
              <div className="text-sm text-muted-foreground">Low</div>
            </CardContent>
          </Card>
        </div>

        {/* Total Estimated Hours */}
        <div className="mb-6 p-4 bg-primary/10 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Total Estimated Rework Time</span>
            <span className="text-2xl font-bold text-primary">
              {reviewData.total_estimated_hours} hours
            </span>
          </div>
        </div>

        {/* Tasks Table */}
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Asset</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Action Required</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Est. Hours</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reviewData.tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>{getStatusIcon(task.status)}</TableCell>
                  <TableCell className="font-medium">{task.asset_name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{task.asset_type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">{task.action_required}</TableCell>
                  <TableCell>{task.owner}</TableCell>
                  <TableCell>
                    <Badge variant={getPriorityBadge(task.priority)}>{task.priority}</Badge>
                  </TableCell>
                  <TableCell>{task.estimated_hours}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {task.status !== 'completed' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleStatusChange(task.id, 'in_progress')}
                          disabled={updateTaskMutation.isPending}
                        >
                          Start
                        </Button>
                      )}
                      {task.status !== 'completed' && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleStatusChange(task.id, 'completed')}
                          disabled={updateTaskMutation.isPending}
                        >
                          Complete
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Recommendations */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
            Recommended Validation Steps
          </h4>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>• Run SDTM validation on affected datasets</li>
            <li>• Run ADaM validation on derived datasets</li>
            <li>• Execute Define XML validation</li>
            <li>• Perform TLF QC checks</li>
            <li>• Consider running Pinnacle21 validation suite</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};

export default ReviewTasks;
