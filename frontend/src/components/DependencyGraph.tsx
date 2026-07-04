import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { api } from '../services/api';
import { Loader2, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';

interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    risk_score: number;
    priority: string;
    reason: string;
    confidence: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
  }>;
}

const getRiskColor = (riskScore: number): string => {
  if (riskScore >= 90) return '#dc2626'; // Red - Critical
  if (riskScore >= 70) return '#ea580c'; // Orange - High
  if (riskScore >= 40) return '#eab308'; // Yellow - Medium
  return '#16a34a'; // Green - Low/No impact
};

const getPriorityBadge = (priority: string) => {
  const variants: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
    Critical: 'destructive',
    High: 'default',
    Medium: 'secondary',
    Low: 'outline',
  };
  return variants[priority] || 'outline';
};

const DependencyGraph: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, setEdgesOnConnect] = useEdgesState([]);

  const { data: graphData, isLoading, error, refetch } = useQuery<GraphData>({
    queryKey: ['graph', id],
    queryFn: () => api.getGraph(id!),
    enabled: !!id,
  });

  // Transform backend data to React Flow format
  const flowNodes: Node[] = useMemo(() => {
    if (!graphData?.nodes) return [];

    // Simple layout algorithm - arrange nodes in levels
    const nodeLevels: Record<string, number> = {
      Endpoint: 0,
      Visit: 1,
      Population: 1,
      SDTM: 2,
      ADaM: 3,
      TLF: 4,
      Table: 4,
      Figure: 4,
      ValidationRule: 5,
      DefineXML: 5,
      ReviewTask: 6,
    };

    const levelCounts: Record<number, number> = {};

    return graphData.nodes.map((node, index) => {
      const level = nodeLevels[node.type] || 0;
      const levelIndex = levelCounts[level] || 0;
      levelCounts[level] = levelIndex + 1;

      const riskColor = getRiskColor(node.risk_score);

      return {
        id: node.id,
        type: 'default',
        position: {
          x: levelIndex * 250,
          y: level * 150,
        },
        data: {
          label: (
            <div className="p-3 min-w-[200px]">
              <div className="font-semibold text-sm mb-1">{node.label}</div>
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={getPriorityBadge(node.priority)} className="text-xs">
                  {node.priority}
                </Badge>
                <span className="text-xs text-muted-foreground">{node.type}</span>
              </div>
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Risk:</span>
                  <span className="font-medium" style={{ color: riskColor }}>
                    {node.risk_score}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Confidence:</span>
                  <span>{node.confidence}%</span>
                </div>
              </div>
              {node.reason && (
                <div className="text-xs text-muted-foreground mt-2 pt-2 border-t">
                  {node.reason}
                </div>
              )}
            </div>
          ),
          style: {
            border: `2px solid ${riskColor}`,
            borderRadius: '8px',
            background: 'hsl(var(--card))',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          },
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });
  }, [graphData]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!graphData?.edges) return [];

    return graphData.edges.map((edge, index) => ({
      id: `e-${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.relationship,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#71717a',
      },
      style: {
        stroke: '#71717a',
        strokeWidth: 2,
      },
      labelStyle: {
        fill: '#71717a',
        fontSize: 12,
      },
    }));
  }, [graphData]);

  // Update nodes and edges when data changes
  React.useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  React.useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    console.log('Clicked node:', node);
    // Could expand downstream dependencies here
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading dependency graph...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-destructive">
            <p className="font-medium">Failed to load graph</p>
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

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Dependency Graph</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Visual representation of downstream dependencies and impact propagation
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[600px] border rounded-lg bg-muted/20">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onNodeClick={onNodeClick}
            fitView
            attributionPosition="bottom-right"
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: false,
            }}
          >
            <Controls />
            <Background color="#888" gap={16} />
          </ReactFlow>
        </div>

        {/* Legend */}
        <div className="mt-4 p-4 bg-muted/50 rounded-lg">
          <h4 className="text-sm font-medium mb-2">Risk Level Legend</h4>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-[#dc2626]" />
              <span className="text-sm">Critical (90-100)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-[#ea580c]" />
              <span className="text-sm">High (70-89)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-[#eab308]" />
              <span className="text-sm">Medium (40-69)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-[#16a34a]" />
              <span className="text-sm">Low (0-39)</span>
            </div>
          </div>
        </div>

        {/* Statistics */}
        {graphData && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{graphData.nodes.length}</div>
                <div className="text-sm text-muted-foreground">Total Nodes</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">{graphData.edges.length}</div>
                <div className="text-sm text-muted-foreground">Dependencies</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">
                  {graphData.nodes.filter((n) => n.risk_score >= 70).length}
                </div>
                <div className="text-sm text-muted-foreground">High/Critical Risk</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">
                  {new Set(graphData.nodes.map((n) => n.type)).size}
                </div>
                <div className="text-sm text-muted-foreground">Node Types</div>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DependencyGraph;
