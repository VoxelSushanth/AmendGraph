import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, TrendingUp, Clock } from 'lucide-react';
import { impactService, graphService, reviewService } from '@/services/api';
import type { ImpactedNode } from '@/types';

export default function ImpactAnalysis() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['impact', id],
    queryFn: () => impactService.get(id!),
    enabled: !!id,
  });

  const analyzeMutation = useMutation({
    mutationFn: () => impactService.analyze(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['impact', id] });
    },
  });

  if (error) {
    return (
      <div className="container mx-auto p-8">
        <div className="rounded-lg border bg-destructive/10 p-6 text-destructive">
          <h2 className="text-xl font-bold mb-2">Error Loading Analysis</h2>
          <p>{(error as Error).message}</p>
        </div>
      </div>
    );
  }

  if (isLoading || !result) {
    return (
      <div className="container mx-auto p-8 flex items-center justify-center h-[50vh]">
        <div className="text-center">
          <Clock className="animate-spin mx-auto mb-4" size={48} />
          <p className="text-muted-foreground">Loading impact analysis...</p>
        </div>
      </div>
    );
  }

  const getRiskColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-destructive text-destructive-foreground';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-black';
      default: return 'bg-green-500 text-white';
    }
  };

  return (
    <div className="container mx-auto p-8">
      <div className="mb-8">
        <Link to="/" className="text-sm text-primary hover:underline">← Back to Dashboard</Link>
        <h1 className="text-3xl font-bold mt-4">Impact Analysis Results</h1>
        <p className="text-muted-foreground">
          Amendment ID: {result.amendment_id}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4 mb-8">
        <SummaryCard
          title="Total Impacted"
          value={result.total_impacted_nodes.toString()}
          icon={TrendingUp}
        />
        <SummaryCard
          title="Critical"
          value={result.risk_summary.critical?.toString() || '0'}
          icon={AlertCircle}
          color="text-destructive"
        />
        <SummaryCard
          title="High Risk"
          value={result.risk_summary.high?.toString() || '0'}
          icon={AlertCircle}
          color="text-orange-500"
        />
        <SummaryCard
          title="Processing Time"
          value={`${result.processing_time_ms || 0}ms`}
          icon={Clock}
        />
      </div>

      {/* Change Detected */}
      <div className="rounded-lg border bg-card mb-8">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold">Detected Change</h2>
        </div>
        <div className="p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm text-muted-foreground">Change Type</p>
              <p className="font-medium capitalize">{result.semantic_diff.change_type}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Description</p>
              <p className="font-medium">{result.semantic_diff.change_description}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Confidence</p>
              <p className="font-medium">{(result.semantic_diff.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 mb-8">
        {!result.impacted_nodes || result.impacted_nodes.length === 0 ? (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
            className="px-6 py-3 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {analyzeMutation.isPending ? 'Analyzing...' : 'Run Impact Analysis'}
          </motion.button>
        ) : (
          <>
            <Link
              to={`/graph/${id}`}
              className="px-6 py-3 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
            >
              View Dependency Graph
            </Link>
            <Link
              to={`/tasks/${id}`}
              className="px-6 py-3 rounded-md border hover:bg-accent"
            >
              Generate Review Tasks
            </Link>
            <Link
              to={`/audit/${id}`}
              className="px-6 py-3 rounded-md border hover:bg-accent"
            >
              View Audit Trail
            </Link>
          </>
        )}
      </div>

      {/* Impacted Nodes */}
      {result.impacted_nodes && result.impacted_nodes.length > 0 && (
        <div className="rounded-lg border bg-card">
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold">Impacted Assets</h2>
            <p className="text-sm text-muted-foreground">
              Sorted by risk score (highest first)
            </p>
          </div>
          <div className="divide-y max-h-[600px] overflow-auto">
            {result.impacted_nodes.map((node: ImpactedNode, index: number) => (
              <motion.div
                key={node.node_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="p-4 flex items-center justify-between hover:bg-accent/50"
              >
                <div className="flex items-center gap-4">
                  <div className={`px-3 py-1 rounded-full text-xs font-medium ${getRiskColor(node.priority)}`}>
                    {node.priority.toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-medium">{node.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {node.node_type} • Risk Score: {node.risk_score}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{node.estimated_rework_hours} hrs</p>
                  <p className="text-xs text-muted-foreground">Estimated Rework</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {result.recommendations && result.recommendations.length > 0 && (
        <div className="mt-8 rounded-lg border bg-card">
          <div className="p-6 border-b">
            <h2 className="text-xl font-semibold">Validation Recommendations</h2>
          </div>
          <div className="p-6">
            <ul className="space-y-2">
              {result.recommendations.map((rec: string, index: number) => (
                <li key={index} className="flex items-center gap-2">
                  <CheckCircle size={18} className="text-green-500" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ 
  title, 
  value, 
  icon: Icon,
  color = 'text-primary'
}: { 
  title: string; 
  value: string; 
  icon: React.ElementType;
  color?: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center gap-4">
        <Icon size={24} className={color} />
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  );
}
