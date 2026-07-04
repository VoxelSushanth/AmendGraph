import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { amendmentService } from '@/services/api';

export default function AmendmentUpload() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    old_text: '',
    new_text: '',
    change_type: 'endpoint',
    change_description: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Upload amendment
      const amendment = await amendmentService.upload(formData);
      
      // Trigger comparison
      await amendmentService.compare(amendment.id);
      
      toast.success('Amendment uploaded successfully!');
      navigate(`/impact/${amendment.id}`);
    } catch (error) {
      console.error(error);
      toast.error('Failed to process amendment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-lg border bg-card"
      >
        <div className="p-6 border-b">
          <h1 className="text-2xl font-bold">Upload Protocol Amendment</h1>
          <p className="text-muted-foreground mt-1">
            Compare old and new protocol sections to analyze downstream impact
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium mb-2">
                Original Text (Old Version)
              </label>
              <textarea
                value={formData.old_text}
                onChange={(e) => setFormData({ ...formData, old_text: e.target.value })}
                className="w-full h-48 p-3 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Paste the original protocol/SAP section..."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Amended Text (New Version)
              </label>
              <textarea
                value={formData.new_text}
                onChange={(e) => setFormData({ ...formData, new_text: e.target.value })}
                className="w-full h-48 p-3 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Paste the amended protocol/SAP section..."
                required
              />
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium mb-2">
                Change Type
              </label>
              <select
                value={formData.change_type}
                onChange={(e) => setFormData({ ...formData, change_type: e.target.value })}
                className="w-full p-3 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="endpoint">Endpoint Change</option>
                <option value="visit">Visit Timing</option>
                <option value="population">Population Criteria</option>
                <option value="variable">Variable Definition</option>
                <option value="method">Statistical Method</option>
                <option value="schedule">Assessment Schedule</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Description (Optional)
              </label>
              <input
                type="text"
                value={formData.change_description}
                onChange={(e) => setFormData({ ...formData, change_description: e.target.value })}
                className="w-full p-3 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Brief description of the change..."
              />
            </div>
          </div>

          <div className="flex justify-end gap-4 pt-4 border-t">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="px-4 py-2 rounded-md border hover:bg-accent"
            >
              Cancel
            </button>
            <motion.button
              type="submit"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={loading || !formData.old_text || !formData.new_text}
              className="px-6 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Analyze Impact'}
            </motion.button>
          </div>
        </form>
      </motion.div>

      {/* Example Section */}
      <div className="mt-8 rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">Example Input</h2>
        <div className="grid gap-4 md:grid-cols-2 text-sm">
          <div>
            <h3 className="font-medium mb-2">Old Text:</h3>
            <pre className="bg-muted p-3 rounded-md overflow-auto text-xs">
              "The primary endpoint is the change from baseline in HbA1c at Week 12."
            </pre>
          </div>
          <div>
            <h3 className="font-medium mb-2">New Text:</h3>
            <pre className="bg-muted p-3 rounded-md overflow-auto text-xs">
              "The primary endpoint is the change from baseline in HbA1c at Week 24."
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
