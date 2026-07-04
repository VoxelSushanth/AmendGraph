export interface NodeType {
  id: string;
  label: string;
  type: string;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  position?: { x: number; y: number };
  metadata?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  directed?: boolean;
  label?: string;
}

export interface DependencyGraph {
  nodes: NodeType[];
  edges: GraphEdge[];
  metadata?: Record<string, unknown>;
}

export interface SemanticDiff {
  endpoints_changed: string[];
  visits_changed?: { old: string; new: string };
  populations_changed: string[];
  variables_changed: string[];
  methods_changed: string[];
  timing_changes?: Record<string, unknown>;
  change_type: string;
  change_description: string;
  confidence: number;
}

export interface ImpactedNode {
  node_id: string;
  node_type: string;
  name: string;
  risk_score: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  confidence: number;
  estimated_rework_hours: number;
  explanation?: string;
}

export interface ImpactAnalysisResult {
  amendment_id: string;
  semantic_diff: SemanticDiff;
  total_impacted_nodes: number;
  risk_summary: Record<string, number>;
  impacted_nodes: ImpactedNode[];
  recommendations: string[];
  generated_at: string;
  processing_time_ms?: number;
}

export interface ReviewTask {
  task_id: string;
  task_name: string;
  owner_role: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  estimated_hours: number;
  dependencies: string[];
  due_date?: string;
  status: string;
  instructions?: string;
}

export interface AuditEntry {
  timestamp: string;
  user_email?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  details?: Record<string, unknown>;
}

export interface Amendment {
  id: string;
  protocol_id?: string;
  old_text: string;
  new_text: string;
  change_type?: string;
  change_description?: string;
  status: string;
  created_at: string;
}
