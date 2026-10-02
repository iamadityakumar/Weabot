import React, { useState, useEffect } from 'react';
import { 
  X, 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw, 
  Check, 
  Search, 
  ShieldCheck, 
  Sliders, 
  FileCode, 
  AlertTriangle,
  Sparkles
} from 'lucide-react';
import { getSOPs, createOrUpdateSOP, deleteSOP, reloadSOPs } from '../api';

export default function SOPManagementModal({ isOpen, onClose, onSOPsUpdated }) {
  const [sops, setSops] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [editingSop, setEditingSop] = useState(null); // null if not editing/creating
  const [isCreating, setIsCreating] = useState(false);
  const [notice, setNotice] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    id: '',
    title: '',
    category: '',
    severity: 'moderate',
    applies_to: '',
    conditions: '',
    advice: '',
  });

  const fetchSOPList = async () => {
    try {
      setLoading(true);
      const res = await getSOPs();
      setSops(res.sops || []);
    } catch (err) {
      setNotice({ type: 'error', text: `Failed to load SOPs: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSOPList();
    }
  }, [isOpen]);

  const handleOpenCreate = () => {
    const nextNum = sops.length + 1;
    const nextId = `SOP-${String(nextNum).padStart(3, '0')}`;
    setFormData({
      id: nextId,
      title: '',
      category: 'Weather Safety',
      severity: 'moderate',
      applies_to: 'cycling, running, hiking, outdoor_work',
      conditions: JSON.stringify({ wind_speed_10m: ">= 30", wind_gusts_10m: ">= 45" }, null, 2),
      advice: '',
    });
    setIsCreating(true);
    setEditingSop(null);
  };

  const handleOpenEdit = (sop) => {
    setFormData({
      id: sop.id,
      title: sop.title || '',
      category: sop.category || 'Weather Safety',
      severity: sop.severity || 'moderate',
      applies_to: Array.isArray(sop.applies_to) ? sop.applies_to.join(', ') : '',
      conditions: JSON.stringify(sop.conditions || {}, null, 2),
      advice: sop.advice || '',
    });
    setEditingSop(sop);
    setIsCreating(false);
  };

  const handleSaveSOP = async (e) => {
    e.preventDefault();
    if (!formData.id.trim() || !formData.title.trim()) {
      alert('SOP ID and Title are required.');
      return;
    }

    let parsedConditions = {};
    try {
      parsedConditions = JSON.parse(formData.conditions);
    } catch (err) {
      alert('Conditions must be valid JSON: ' + err.message);
      return;
    }

    const payload = {
      id: formData.id.trim(),
      title: formData.title.trim(),
      category: formData.category.trim(),
      severity: formData.severity.trim().toLowerCase(),
      applies_to: formData.applies_to.split(',').map((s) => s.trim()).filter(Boolean),
      conditions: parsedConditions,
      advice: formData.advice.trim(),
    };

    try {
      setLoading(true);
      await createOrUpdateSOP(payload);
      setNotice({ type: 'success', text: `Saved and reloaded ${payload.id} successfully!` });
      setTimeout(() => setNotice(null), 3000);
      setEditingSop(null);
      setIsCreating(false);
      await fetchSOPList();
      if (onSOPsUpdated) onSOPsUpdated();
    } catch (err) {
      setNotice({ type: 'error', text: `Save failed: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSOP = async (sopId) => {
    if (!confirm(`Are you sure you want to delete ${sopId}?`)) return;
    try {
      setLoading(true);
      await deleteSOP(sopId);
      setNotice({ type: 'success', text: `Deleted ${sopId} successfully.` });
      setTimeout(() => setNotice(null), 3000);
      await fetchSOPList();
      if (onSOPsUpdated) onSOPsUpdated();
    } catch (err) {
      setNotice({ type: 'error', text: `Delete failed: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleManualReload = async () => {
    try {
      setLoading(true);
      const res = await reloadSOPs();
      setNotice({ type: 'success', text: `Hot-reloaded ${res.count} SOPs from disk.` });
      setTimeout(() => setNotice(null), 3000);
      await fetchSOPList();
      if (onSOPsUpdated) onSOPsUpdated();
    } catch (err) {
      setNotice({ type: 'error', text: `Reload failed: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Filter SOPs
  const filteredSops = sops.filter((s) => {
    const matchSearch =
      s.id.toLowerCase().includes(search.toLowerCase()) ||
      s.title.toLowerCase().includes(search.toLowerCase()) ||
      (s.category && s.category.toLowerCase().includes(search.toLowerCase()));
    const matchSeverity =
      selectedSeverity === 'all' || s.severity.toLowerCase() === selectedSeverity;
    return matchSearch && matchSeverity;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/40 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-4xl w-full h-[90vh] shadow-2xl border border-gray-200 flex flex-col overflow-hidden relative">
        {/* Top Header */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-100 flex items-center justify-center text-purple-700 shadow-2xs">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-gray-900 font-display">
                SOP Policy Studio & Settings
              </h2>
              <p className="text-xs text-gray-500">
                View, create, and edit deterministic Standard Operating Procedure rules
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleManualReload}
              disabled={loading}
              title="Hot Reload all SOPs from disk"
              className="px-3 py-1.5 rounded-xl border border-gray-200 hover:bg-gray-50 text-xs font-medium text-gray-700 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Hot Reload</span>
            </button>

            <button
              onClick={handleOpenCreate}
              className="px-3.5 py-1.5 rounded-xl bg-[#18181b] hover:bg-black text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>New SOP</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors ml-2 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Notification Toast */}
        {notice && (
          <div
            className={`px-5 py-2.5 text-xs font-medium flex items-center justify-between animate-fadeIn ${
              notice.type === 'error'
                ? 'bg-rose-50 text-rose-700 border-b border-rose-200'
                : 'bg-emerald-50 text-emerald-700 border-b border-emerald-200'
            }`}
          >
            <span>{notice.text}</span>
            <button onClick={() => setNotice(null)} className="text-current opacity-70 hover:opacity-100">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main List Section */}
          <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-100">
            {/* Search and Filters */}
            <div className="p-3.5 border-b border-gray-100 flex items-center gap-2 bg-[#faf9fe]">
              <div className="flex-1 flex items-center bg-white border border-gray-200 rounded-xl px-2.5 py-1.5 text-xs">
                <Search className="w-3.5 h-3.5 text-gray-400 mr-2 shrink-0" />
                <input
                  type="text"
                  placeholder="Search SOP by ID, title, or hazard category..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent border-none outline-none w-full text-xs text-gray-800 placeholder-gray-400"
                />
              </div>

              {/* Severity filter */}
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="bg-white border border-gray-200 rounded-xl px-2.5 py-1.5 text-xs text-gray-700 outline-none cursor-pointer"
              >
                <option value="all">All Severities</option>
                <option value="high">High Severity</option>
                <option value="moderate">Moderate Severity</option>
                <option value="low">Low Severity</option>
              </select>
            </div>

            {/* SOP Cards Grid / List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {filteredSops.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-xs">
                  No SOPs matched your query.
                </div>
              ) : (
                filteredSops.map((sop) => {
                  const isHigh = sop.severity?.toLowerCase() === 'high';
                  const isMod = sop.severity?.toLowerCase() === 'moderate';
                  return (
                    <div
                      key={sop.id}
                      className="p-4 bg-white hover:bg-[#fbfafc] border border-gray-200/90 rounded-2xl shadow-2xs transition-all flex flex-col justify-between group"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-xs text-purple-700 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200">
                            {sop.id}
                          </span>
                          <span
                            className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md border ${
                              isHigh
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : isMod
                                ? 'bg-purple-50 text-purple-700 border-purple-200'
                                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            }`}
                          >
                            {sop.severity}
                          </span>
                          <span className="text-[11px] text-gray-400 font-medium">
                            {sop.category}
                          </span>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleOpenEdit(sop)}
                            className="p-1.5 text-gray-500 hover:text-purple-700 hover:bg-purple-50 rounded-lg transition-colors cursor-pointer"
                            title="Edit SOP"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteSOP(sop.id)}
                            className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                            title="Delete SOP"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <h4 className="font-semibold text-sm text-gray-900 mb-1">
                        {sop.title}
                      </h4>

                      <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed mb-2 font-normal">
                        {sop.advice}
                      </p>

                      <div className="pt-2 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                        <div className="flex items-center gap-1 text-gray-400">
                          <span>Applies to:</span>
                          <span className="text-gray-700 font-medium">
                            {Array.isArray(sop.applies_to) ? sop.applies_to.join(', ') : 'All activities'}
                          </span>
                        </div>
                        <div className="text-[10px] font-mono text-purple-600 bg-purple-50/60 px-2 py-0.5 rounded-md">
                          {Object.keys(sop.conditions || {}).length} Condition Thresholds
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Form Side-Drawer (Create or Edit) */}
          {(isCreating || editingSop) && (
            <div className="w-[360px] sm:w-[420px] bg-[#faf9fc] border-l border-gray-200 p-5 flex flex-col justify-between overflow-y-auto animate-fadeIn shrink-0">
              <form onSubmit={handleSaveSOP} className="space-y-3.5">
                <div className="flex items-center justify-between pb-2 border-b border-gray-200">
                  <h3 className="font-bold text-sm text-gray-900 font-display">
                    {isCreating ? 'Create New Safety SOP' : `Edit ${editingSop?.id}`}
                  </h3>
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setEditingSop(null);
                    }}
                    className="p-1 text-gray-400 hover:text-gray-700 rounded-md"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* SOP ID */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                    SOP ID
                  </label>
                  <input
                    type="text"
                    value={formData.id}
                    onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                    placeholder="e.g. SOP-013"
                    disabled={!isCreating}
                    className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs font-mono outline-none focus:border-purple-400"
                    required
                  />
                </div>

                {/* Title */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                    Policy Title
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="e.g. High Wind Cycling Hazard"
                    className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs outline-none focus:border-purple-400"
                    required
                  />
                </div>

                {/* Category & Severity */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                      Category
                    </label>
                    <input
                      type="text"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      placeholder="e.g. Wind Hazard"
                      className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs outline-none focus:border-purple-400"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                      Severity
                    </label>
                    <select
                      value={formData.severity}
                      onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                      className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs outline-none focus:border-purple-400 cursor-pointer"
                    >
                      <option value="high">High</option>
                      <option value="moderate">Moderate</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>

                {/* Applies To */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                    Applies To Activities (Comma-separated)
                  </label>
                  <input
                    type="text"
                    value={formData.applies_to}
                    onChange={(e) => setFormData({ ...formData, applies_to: e.target.value })}
                    placeholder="cycling, running, hiking, drone"
                    className="w-full px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs outline-none focus:border-purple-400"
                  />
                </div>

                {/* Conditions JSON */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1 flex items-center justify-between">
                    <span>Conditions (JSON format)</span>
                    <span className="text-[10px] text-gray-400 lowercase font-normal">e.g. {`{"wind_speed_10m": ">= 30"}`}</span>
                  </label>
                  <textarea
                    rows={4}
                    value={formData.conditions}
                    onChange={(e) => setFormData({ ...formData, conditions: e.target.value })}
                    className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-mono outline-none focus:border-purple-400 resize-none leading-relaxed"
                    required
                  />
                </div>

                {/* Advice Textarea */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 uppercase mb-1">
                    Guardian Advice & Action Items
                  </label>
                  <textarea
                    rows={4}
                    value={formData.advice}
                    onChange={(e) => setFormData({ ...formData, advice: e.target.value })}
                    placeholder="Clear guidance and recommended safety precautions to display..."
                    className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs outline-none focus:border-purple-400 resize-none leading-relaxed"
                    required
                  />
                </div>

                <div className="pt-2 flex items-center gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 py-2 bg-[#18181b] hover:bg-black text-white text-xs font-semibold rounded-xl transition-all shadow-md active:scale-98 cursor-pointer"
                  >
                    Save & Hot-Deploy
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setEditingSop(null);
                    }}
                    className="px-4 py-2 border border-gray-200 hover:bg-gray-100 rounded-xl text-xs text-gray-600 cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
