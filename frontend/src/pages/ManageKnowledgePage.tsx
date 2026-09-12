import { useState, useEffect } from 'react'
import { fetchApi } from '@/shared/api/client'
import { useRole } from '@/shared/lib/roles'
import { StatusBadge, type StatusValue } from '@/shared/ui/StatusBadge'
import {
  Database,
  Search,
  Edit3,
  Trash2,
  Eye,
  Loader2,
  RefreshCw,
  X,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'
import { PageShell } from './ConsolePage'

interface KnowledgeItem {
  id: string
  submitted_by: str
  submitter_role: str
  raw_content: str
  status: string
  created_at: string
}

export function ManageKnowledgePage() {
  const { role } = useRole()
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Modals state
  const [viewingItem, setViewingItem] = useState<KnowledgeItem | null>(null)
  const [editingItem, setEditingItem] = useState<KnowledgeItem | null>(null)
  const [editContent, setEditContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const loadItems = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchApi<{ items: KnowledgeItem[]; count: number }>('/api/v1/knowledge/manage', {
        role,
      })
      setItems(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load knowledge base items')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (role !== 'guest') {
      loadItems()
    }
  }, [role])

  if (role === 'guest') {
    return (
      <PageShell icon={Database} title="Manage Knowledge" label="KNOWLEDGE BASE MAINTENANCE">
        <div className="panel p-8 text-center space-y-3">
          <StatusBadge status="failed" size="sm" />
          <h2 className="text-base font-semibold text-text-primary">Guest Role Access Restricted</h2>
          <p className="text-text-secondary text-sm max-w-md mx-auto">
            Guests cannot manage or edit knowledge items. Switch to <strong className="text-sky">Crew</strong> or <strong className="text-amber">Captain</strong> role.
          </p>
        </div>
      </PageShell>
    )
  }

  const handleEditClick = (item: KnowledgeItem) => {
    setEditingItem(item)
    setEditContent(item.raw_content)
  }

  const handleSaveEdit = async () => {
    if (!editingItem || !editContent.trim()) return
    setIsSaving(true)
    setNotification(null)

    try {
      await fetchApi(`/api/v1/knowledge/manage/${editingItem.id}`, {
        method: 'PUT',
        role,
        body: JSON.stringify({ raw_content: editContent.trim() }),
      })

      setNotification({ type: 'success', message: 'Knowledge item updated and re-indexed successfully!' })
      setEditingItem(null)
      loadItems()
    } catch (err) {
      setNotification({ type: 'error', message: err instanceof Error ? err.message : 'Update failed' })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (role !== 'captain') {
      alert('Only Captain role can delete knowledge items.')
      return
    }
    if (!confirm('Are you sure you want to delete this knowledge item? It will be removed from vector embeddings.')) {
      return
    }

    setDeletingId(id)
    setNotification(null)

    try {
      await fetchApi(`/api/v1/knowledge/manage/${id}`, {
        method: 'DELETE',
        role,
      })

      setNotification({ type: 'success', message: 'Knowledge item deleted successfully.' })
      setItems((prev) => prev.filter((item) => item.id !== id))
    } catch (err) {
      setNotification({ type: 'error', message: err instanceof Error ? err.message : 'Delete failed' })
    } finally {
      setDeletingId(null)
    }
  }

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.raw_content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.submitted_by.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <PageShell icon={Database} title="Manage Knowledge Base" label="KNOWLEDGE BASE CRUD MAINTENANCE">
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Notification Toast */}
        {notification && (
          <div
            className={`p-3.5 rounded-sm border flex items-center justify-between text-sm ${
              notification.type === 'success'
                ? 'bg-emerald/10 border-emerald/30 text-emerald'
                : 'bg-rose/10 border-rose/30 text-rose'
            }`}
          >
            <div className="flex items-center gap-2">
              {notification.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
              <span>{notification.message}</span>
            </div>
            <button onClick={() => setNotification(null)} className="p-1 hover:opacity-70">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Toolbar: Search, Filter, Refresh */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-base-800 p-4 border border-border rounded-sm">
          <div className="flex items-center gap-2 w-full sm:w-auto flex-1 max-w-md">
            <Search className="h-4 w-4 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge text, submitter..."
              className="w-full bg-base-900 border border-border rounded-sm px-3 py-1.5 text-xs text-text-primary focus:border-amber outline-none"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-base-900 border border-border rounded-sm px-2.5 py-1.5 text-xs text-text-primary outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="approved">Approved / Indexed</option>
              <option value="pending">Pending Review</option>
              <option value="rejected">Rejected</option>
            </select>

            <button
              onClick={loadItems}
              disabled={isLoading}
              className="p-2 text-text-secondary hover:text-amber bg-base-900 border border-border rounded-sm transition-colors"
              title="Refresh List"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Knowledge Items Table / List */}
        {isLoading ? (
          <div className="p-12 text-center text-text-muted flex flex-col items-center gap-2">
            <Loader2 className="h-6 w-6 animate-spin text-amber" />
            <span className="text-xs font-mono">Loading knowledge base records...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose/10 border border-rose/30 text-rose text-sm rounded-sm">
            {error}
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center bg-base-800 border border-dashed border-border-subtle rounded-sm text-text-muted space-y-2">
            <Database className="h-8 w-8 mx-auto text-text-muted" />
            <p className="text-sm font-medium">No knowledge base records found</p>
            <p className="text-xs text-text-secondary">Try adjusting your search query or submit new knowledge.</p>
          </div>
        ) : (
          <div className="bg-base-800 border border-border rounded-sm overflow-hidden">
            <div className="divide-y divide-border-subtle">
              {filteredItems.map((item) => (
                <div key={item.id} className="p-4 hover:bg-base-700/40 transition-colors space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={item.status as StatusValue} size="sm" />
                        <span className="mono text-[10px] text-text-muted">ID: {item.id}</span>
                        <span className="mono text-[10px] text-text-secondary">
                          by <strong className="text-text-primary">{item.submitted_by}</strong> ({item.submitter_role})
                        </span>
                      </div>
                      <p className="text-xs text-text-primary font-mono line-clamp-2 leading-relaxed">
                        {item.raw_content}
                      </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button
                        onClick={() => setViewingItem(item)}
                        className="p-1.5 text-text-secondary hover:text-sky bg-base-900 border border-border rounded-sm transition-colors"
                        title="View Full Content"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>

                      <button
                        onClick={() => handleEditClick(item)}
                        className="p-1.5 text-text-secondary hover:text-amber bg-base-900 border border-border rounded-sm transition-colors"
                        title="Edit Content"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>

                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id || role !== 'captain'}
                        className="p-1.5 text-text-secondary hover:text-rose bg-base-900 border border-border rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title={role === 'captain' ? 'Delete Knowledge Record' : 'Captain role required to delete'}
                      >
                        {deletingId === item.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-text-muted mono">
                    <span>Created: {new Date(item.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* View Modal */}
        {viewingItem && (
          <div className="fixed inset-0 bg-base-900/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-base-800 border border-border rounded-sm max-w-2xl w-full p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                  Knowledge Item Content
                </h3>
                <button onClick={() => setViewingItem(null)} className="p-1 text-text-muted hover:text-text-primary">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <StatusBadge status={viewingItem.status as StatusValue} />
                  <span className="mono text-text-muted">ID: {viewingItem.id}</span>
                </div>
                <div className="p-4 bg-base-900 border border-border rounded-sm text-text-primary whitespace-pre-wrap font-mono max-h-96 overflow-y-auto leading-relaxed">
                  {viewingItem.raw_content}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setViewingItem(null)}
                  className="px-4 py-1.5 bg-base-700 hover:bg-base-600 text-text-primary text-xs font-semibold rounded-sm transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit Modal */}
        {editingItem && (
          <div className="fixed inset-0 bg-base-900/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-base-800 border border-border rounded-sm max-w-2xl w-full p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                  Edit Knowledge Item
                </h3>
                <button onClick={() => setEditingItem(null)} className="p-1 text-text-muted hover:text-text-primary">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-2">
                <label className="label-caps block">Raw Knowledge Text</label>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-52 bg-base-900 border border-border rounded-sm p-3 text-xs font-mono text-text-primary focus:border-amber outline-none resize-y"
                  disabled={isSaving}
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setEditingItem(null)}
                  disabled={isSaving}
                  className="px-4 py-1.5 bg-base-700 hover:bg-base-600 text-text-primary text-xs font-semibold rounded-sm transition-colors"
                >
                  Cancel
                </button>

                <button
                  onClick={handleSaveEdit}
                  disabled={isSaving || !editContent.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-amber hover:bg-amber-light text-base-900 text-xs font-bold rounded-sm transition-colors disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Save & Re-Index Vector Store
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}
