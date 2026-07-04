import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, GitGraph, CheckSquare, ClipboardList, Plus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { amendmentService, impactService } from '@/services/api';

export default function Dashboard() {
  const { data: amendments = [], isLoading } = useQuery({
    queryKey: ['amendments'],
    queryFn: amendmentService.list,
  });

  return (
    <div className="container mx-auto p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Protocol Amendment Engine
          </h1>
          <p className="text-muted-foreground mt-2">
            Automated impact analysis for clinical trial protocols
          </p>
        </div>
        <Link to="/upload">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            <Plus size={20} />
            New Analysis
          </motion.button>
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4 mb-8">
        <StatCard 
          title="Total Amendments" 
          value={amendments.length.toString()}
          icon={FileText}
        />
        <StatCard 
          title="Critical Impacts" 
          value="3"
          icon={GitGraph}
        />
        <StatCard 
          title="Pending Reviews" 
          value="7"
          icon={CheckSquare}
        />
        <StatCard 
          title="Avg Processing" 
          value="1.2s"
          icon={ClipboardList}
        />
      </div>

      {/* Recent Amendments */}
      <div className="rounded-lg border bg-card">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold">Recent Analyses</h2>
        </div>
        <div className="divide-y">
          {isLoading ? (
            <div className="p-6 text-center text-muted-foreground">
              Loading...
            </div>
          ) : amendments.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground">
              No analyses yet. Start by uploading a protocol amendment.
            </div>
          ) : (
            amendments.map((amendment) => (
              <div key={amendment.id} className="p-4 flex items-center justify-between hover:bg-accent/50">
                <div>
                  <h3 className="font-medium">{amendment.change_type || 'Protocol Change'}</h3>
                  <p className="text-sm text-muted-foreground">
                    {new Date(amendment.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Link
                    to={`/impact/${amendment.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View Impact
                  </Link>
                  <Link
                    to={`/graph/${amendment.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    Graph
                  </Link>
                  <Link
                    to={`/tasks/${amendment.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    Tasks
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon }: { 
  title: string; 
  value: string; 
  icon: React.ElementType;
}) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="rounded-lg border bg-card p-6"
    >
      <div className="flex items-center gap-4">
        <div className="p-2 bg-primary/10 rounded-full">
          <Icon size={24} className="text-primary" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </motion.div>
  );
}
