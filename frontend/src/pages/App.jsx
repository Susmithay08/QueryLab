import { useEffect, useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import CodeMirror from '@uiw/react-codemirror'
import { sql as sqlLang } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'
import {
  Play, Sparkles, TrendingUp, Share2, History, ChevronRight, Upload, X,
  ChevronDown, Database, Table, Key, AlertCircle, Loader2,
  Copy, Check, KeyRound, Eye, EyeOff, Zap, BookOpen,
  Clock, Hash, TriangleAlert, Lightbulb, Wrench
} from 'lucide-react'
import { useStore } from '../store'
import { formatDistanceToNow } from 'date-fns'

const DB_COLORS = {
  ecommerce: { color: '#4ADE80', label: 'E-Commerce' },
  hr: { color: '#A78BFA', label: 'HR & Employees' },
  movies: { color: '#FB923C', label: 'Movies' },
  sports: { color: '#F472B6', label: 'Sports' },
}

const ISSUE_COLORS = { performance: '#FCD34D', style: '#38BDF8', correctness: '#F87171', security: '#F97316' }

// ── Schema sidebar ────────────────────────────────────────────────────────────
function SchemaPanel({ schema, onTableClick }) {
  const [open, setOpen] = useState({})
  const toggle = (t) => setOpen(s => ({ ...s, [t]: !s[t] }))

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
      {schema.map(tbl => (
        <div key={tbl.table} style={{ marginBottom: 2 }}>
          <button onClick={() => toggle(tbl.table)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 7, padding: '6px 8px',
              borderRadius: 7, transition: 'all 0.12s', background: 'transparent'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg4)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            {open[tbl.table]
              ? <ChevronDown size={11} style={{ color: 'var(--sky)', flexShrink: 0 }} />
              : <ChevronRight size={11} style={{ color: 'var(--text3)', flexShrink: 0 }} />}
            <Table size={11} style={{ color: 'var(--sky)', flexShrink: 0 }} />
            <span style={{
              flex: 1, fontSize: 12, fontWeight: 600, fontFamily: 'var(--mono)',
              textAlign: 'left', color: 'var(--text)'
            }}>{tbl.table}</span>
            <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
              {tbl.row_count}
            </span>
          </button>
          {open[tbl.table] && (
            <div style={{ marginLeft: 20, marginBottom: 4 }}>
              {tbl.columns.map(col => (
                <div key={col.name}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
                    borderRadius: 6, cursor: 'pointer'
                  }}
                  onClick={() => onTableClick(tbl.table, col.name)}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg4)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  {col.pk
                    ? <Key size={9} style={{ color: 'var(--yellow)', flexShrink: 0 }} />
                    : <Hash size={9} style={{ color: 'var(--text3)', flexShrink: 0 }} />}
                  <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: col.pk ? 'var(--yellow)' : 'var(--text2)' }}>
                    {col.name}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>
                    {col.type}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Results table ─────────────────────────────────────────────────────────────
function ResultsTable({ result }) {
  if (!result?.columns?.length) return null
  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <table className="results-table">
        <thead>
          <tr>{result.columns.map(c => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {result.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>
                  {cell === null
                    ? <span className="null-badge">NULL</span>
                    : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── AI Explain panel ──────────────────────────────────────────────────────────
function ExplainPanel({ data, loading }) {
  if (loading) return <AILoading label="Explaining query…" />
  if (!data) return <AIEmpty icon={BookOpen} label="Click Explain to understand this query" />
  if (data.error) return <AIError msg={data.error} />

  const diffColor = { beginner: 'var(--green)', intermediate: 'var(--yellow)', advanced: 'var(--red)' }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{data.summary}</p>
          <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7 }}>{data.explanation}</p>
        </div>
        {data.difficulty && (
          <span className="tag" style={{
            background: `${diffColor[data.difficulty]}18`,
            color: diffColor[data.difficulty], border: `1px solid ${diffColor[data.difficulty]}33`,
            flexShrink: 0
          }}>
            {data.difficulty}
          </span>
        )}
      </div>
      {data.concepts?.length > 0 && (
        <div>
          <p style={{
            fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8
          }}>Concepts used</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {data.concepts.map(c => (
              <span key={c} className="tag"
                style={{ background: 'var(--sky-soft)', color: 'var(--sky)', border: '1px solid rgba(56,189,248,0.2)' }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}

// ── AI Optimize panel ─────────────────────────────────────────────────────────
function OptimizePanel({ data, loading, onApply }) {
  if (loading) return <AILoading label="Analyzing query…" />
  if (!data) return <AIEmpty icon={TrendingUp} label="Click Optimize to improve this query" />
  if (data.error) return <AIError msg={data.error} />

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center',
          justifyContent: 'center',
          background: data.improved ? 'var(--green-soft)' : 'var(--sky-soft)',
          border: `1px solid ${data.improved ? 'rgba(74,222,128,0.2)' : 'rgba(56,189,248,0.2)'}`
        }}>
          {data.improved ? <TrendingUp size={13} style={{ color: 'var(--green)' }} /> :
            <Check size={13} style={{ color: 'var(--sky)' }} />}
        </div>
        <p style={{ fontSize: 13, color: data.improved ? 'var(--green)' : 'var(--sky)', fontWeight: 600 }}>
          {data.improved ? 'Improvements found' : 'Query looks optimal'}
        </p>
      </div>

      {data.explanation && (
        <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7, marginBottom: 16 }}>{data.explanation}</p>
      )}

      {data.issues?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{
            fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8
          }}>Issues</p>
          {data.issues.map((issue, i) => {
            const c = ISSUE_COLORS[issue.type] || 'var(--sky)'
            return (
              <div key={i} style={{
                padding: '10px 14px', borderRadius: 8, marginBottom: 8,
                background: `${c}08`, border: `1px solid ${c}25`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <TriangleAlert size={11} style={{ color: c }} />
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: c,
                    textTransform: 'uppercase', fontFamily: 'var(--mono)'
                  }}>{issue.type}</span>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 3 }}>{issue.description}</p>
                <p style={{ fontSize: 12, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Lightbulb size={10} style={{ color: c }} />{issue.suggestion}
                </p>
              </div>
            )
          })}
        </div>
      )}

      {data.improved && data.optimized_sql && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <p style={{
              fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
              textTransform: 'uppercase', letterSpacing: '0.08em'
            }}>Optimized SQL</p>
            <button onClick={() => onApply(data.optimized_sql)} className="btn-ghost"
              style={{
                fontSize: 10, padding: '3px 10px', color: 'var(--green)',
                borderColor: 'rgba(74,222,128,0.3)'
              }}>
              <Wrench size={10} style={{ display: 'inline', marginRight: 4 }} />Apply
            </button>
          </div>
          <pre style={{
            padding: '12px', borderRadius: 8, background: 'var(--bg3)',
            border: '1px solid var(--border2)', fontSize: 12, fontFamily: 'var(--mono)',
            color: 'var(--text2)', overflow: 'auto', whiteSpace: 'pre-wrap'
          }}>
            {data.optimized_sql}
          </pre>
        </div>
      )}
    </motion.div>
  )
}

function AILoading({ label }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      gap: 10, padding: '48px', color: 'var(--text3)'
    }}>
      <Loader2 size={16} style={{ animation: 'spin 0.8s linear infinite', color: 'var(--sky)' }} />
      <span style={{ fontSize: 13 }}>{label}</span>
    </div>
  )
}

function AIEmpty({ icon: Icon, label }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: 8, padding: '48px', color: 'var(--text3)'
    }}>
      <Icon size={22} style={{ opacity: 0.25 }} />
      <span style={{ fontSize: 12 }}>{label}</span>
    </div>
  )
}

function AIError({ msg }) {
  return (
    <div style={{
      margin: 16, padding: '10px 14px', borderRadius: 8,
      background: 'var(--red-soft)', border: '1px solid rgba(248,113,113,0.2)',
      display: 'flex', gap: 8, alignItems: 'flex-start'
    }}>
      <AlertCircle size={13} style={{ color: 'var(--red)', flexShrink: 0, marginTop: 1 }} />
      <p style={{ fontSize: 12, color: 'var(--red)' }}>{msg}</p>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const store = useStore()
  const {
    groqApiKey, setGroqApiKey,
    databases, activeDb, schema, examples, history,
    sql, result, running, error,
    explanation, optimization, aiLoading,
    activeTab, setActiveTab, fetchDatabases, setDb, setSql,
    runQuery, explainQuery, optimizeQuery, fixQuery, shareQuery, uploadCSV, deleteUserDB,
    fetchHistory, loadFromHistory,
  } = store

  const [showKey, setShowKey] = useState(false)
  const [keyDraft, setKeyDraft] = useState('')
  const [showKeyInput, setShowKeyInput] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showExamples, setShowExamples] = useState(true)
  const [copied, setCopied] = useState(false)
  const [shareSlug, setShareSlug] = useState(null)
  const [fixing, setFixing] = useState(false)
  const [uploading, setUploading] = useState(false)
  const csvRef = useRef(null)

  useEffect(() => {
    fetchDatabases()
    store.fetchSchema(activeDb)
    store.fetchExamples(activeDb)
    fetchHistory()
  }, [])

  const handleKeyDown = useCallback((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      runQuery()
    }
  }, [runQuery])

  const handleShare = async () => {
    const data = await shareQuery()
    setShareSlug(data.slug)
    const url = `${window.location.origin}/shared/${data.slug}`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
  }

  const handleFix = async () => {
    setFixing(true)
    await fixQuery(error)
    setFixing(false)
  }

  const handleCSVUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try { await uploadCSV(file) } catch (err) { alert(err.message) }
    finally { setUploading(false); e.target.value = '' }
  }

  const dbColor = DB_COLORS[activeDb]?.color || 'var(--sky)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>

      {/* ── Top bar ── */}
      <div style={{
        height: 48, borderBottom: '1px solid var(--border2)', background: 'var(--bg2)',
        display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12, flexShrink: 0
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center',
            justifyContent: 'center', background: 'var(--sky-soft)',
            border: '1px solid var(--sky-dim)', boxShadow: '0 0 12px var(--sky-glow)'
          }}>
            <Database size={13} style={{ color: 'var(--sky)' }} />
          </div>
          <span style={{ fontWeight: 800, fontSize: 14, fontFamily: 'var(--mono)', color: 'var(--sky)' }}>
            QueryLab
          </span>
        </div>

        {/* DB selector */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {databases.map(db => {
            const dc = DB_COLORS[db.id]
            const isUser = db.user_upload
            const color = isUser ? '#F472B6' : dc?.color
            const label = isUser ? db.name : (dc?.label || db.name)
            return (
              <div key={db.id} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                <button onClick={() => setDb(db.id)}
                  style={{
                    padding: '4px 12px', borderRadius: isUser ? '20px 0 0 20px' : 20,
                    fontSize: 11, fontWeight: 600, fontFamily: 'var(--mono)', transition: 'all 0.15s',
                    background: activeDb === db.id ? `${color}18` : 'transparent',
                    color: activeDb === db.id ? color : 'var(--text3)',
                    border: `1px solid ${activeDb === db.id ? `${color}40` : 'var(--border2)'}`,
                    borderRight: isUser ? 'none' : undefined
                  }}>
                  {isUser && '📂 '}{label}
                </button>
                {isUser && (
                  <button onClick={() => deleteUserDB(db.id)}
                    style={{
                      padding: '4px 7px', borderRadius: '0 20px 20px 0', fontSize: 10,
                      border: `1px solid ${activeDb === db.id ? `${color}40` : 'var(--border2)'}`,
                      color: 'var(--text3)', transition: 'all 0.12s', lineHeight: 1
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text3)'}>
                    <X size={9} />
                  </button>
                )}
              </div>
            )
          })}
          {/* CSV upload button */}
          <input ref={csvRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleCSVUpload} />
          <button onClick={() => csvRef.current?.click()} disabled={uploading}
            style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600,
              fontFamily: 'var(--mono)', transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 4,
              background: 'transparent', color: 'var(--text3)',
              border: '1px dashed var(--border2)'
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--sky)'; e.currentTarget.style.color = 'var(--sky)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text3)' }}>
            {uploading
              ? <><Loader2 size={10} style={{ animation: 'spin 0.7s linear infinite' }} /> Importing…</>
              : <><Upload size={10} /> Import CSV</>}
          </button>
        </div>

        <div style={{ flex: 1 }} />

        {/* Actions */}
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setShowHistory(s => !s)} className="btn-ghost"
            style={{
              display: 'flex', alignItems: 'center', gap: 5, fontSize: 11,
              background: showHistory ? 'var(--bg4)' : 'transparent'
            }}>
            <History size={11} /> History
          </button>

          <button onClick={handleShare} className="btn-ghost"
            style={{
              display: 'flex', alignItems: 'center', gap: 5, fontSize: 11,
              color: copied ? 'var(--green)' : 'var(--text2)',
              borderColor: copied ? 'rgba(74,222,128,0.3)' : 'var(--border2)'
            }}>
            {copied ? <><Check size={11} /> Link copied!</> : <><Share2 size={11} /> Share</>}
          </button>
        </div>

        {/* API Key */}
        <div style={{ position: 'relative' }}>
          <button onClick={() => setShowKeyInput(s => !s)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '5px 11px',
              borderRadius: 8, fontSize: 11, fontFamily: 'var(--mono)',
              border: '1px solid var(--border2)',
              background: groqApiKey ? 'var(--green-soft)' : 'var(--bg3)',
              color: groqApiKey ? 'var(--green)' : 'var(--text3)', transition: 'all 0.15s'
            }}>
            <KeyRound size={11} />
            {groqApiKey ? '✓ API key' : 'Add key'}
          </button>
          <AnimatePresence>
            {showKeyInput && (
              <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                style={{
                  position: 'absolute', right: 0, top: 'calc(100%+6px)', top: 40, width: 260,
                  background: 'var(--bg2)', border: '1px solid var(--border2)',
                  borderRadius: 10, padding: 14, boxShadow: '0 8px 32px rgba(0,0,0,0.6)', zIndex: 200
                }}>
                <p style={{
                  fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
                  textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8
                }}>Groq API Key</p>
                <div style={{ position: 'relative' }}>
                  <input className="input" type={showKey ? 'text' : 'password'} placeholder="gsk_…"
                    value={keyDraft || groqApiKey} onChange={e => setKeyDraft(e.target.value)}
                    style={{ fontSize: 11, paddingRight: 50 }} />
                  <div style={{ position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)', display: 'flex', gap: 3 }}>
                    <button onClick={() => setShowKey(v => !v)} style={{ color: 'var(--text3)', padding: 2 }}>
                      {showKey ? <EyeOff size={10} /> : <Eye size={10} />}
                    </button>
                    <button onClick={() => { setGroqApiKey(keyDraft || groqApiKey); setKeyDraft(''); setShowKeyInput(false) }}
                      style={{ color: 'var(--sky)', fontWeight: 800, fontSize: 12 }}>✓</button>
                  </div>
                </div>
                <p style={{ fontSize: 10, color: 'var(--text3)', marginTop: 6 }}>
                  Free at <a href="https://console.groq.com" target="_blank" style={{ color: 'var(--sky)' }}>console.groq.com</a>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Schema sidebar ── */}
        <aside style={{
          width: 220, flexShrink: 0, borderRight: '1px solid var(--border2)',
          background: 'var(--bg2)', display: 'flex', flexDirection: 'column', overflow: 'hidden'
        }}>
          <div style={{ padding: '10px 12px 6px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <p style={{
              fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
              textTransform: 'uppercase', letterSpacing: '0.08em'
            }}>
              Schema — {DB_COLORS[activeDb]?.label}
            </p>
          </div>
          <SchemaPanel schema={schema}
            onTableClick={(table, col) => setSql(`SELECT * FROM ${table}\nLIMIT 20`)} />

          {/* Examples */}
          <div style={{ borderTop: '1px solid var(--border)', flexShrink: 0 }}>
            <button onClick={() => setShowExamples(s => !s)}
              style={{
                width: '100%', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
                textTransform: 'uppercase', letterSpacing: '0.08em'
              }}>
              <Zap size={10} style={{ color: 'var(--sky)' }} />
              Examples ({examples.length})
              <ChevronDown size={10} style={{
                marginLeft: 'auto',
                transform: showExamples ? 'rotate(180deg)' : 'none', transition: '0.15s'
              }} />
            </button>
            {showExamples && (
              <div style={{ maxHeight: 180, overflow: 'auto' }}>
                {examples.map((ex, i) => (
                  <button key={i} onClick={() => { setSql(ex.sql) }}
                    style={{
                      width: '100%', textAlign: 'left', padding: '6px 12px',
                      fontSize: 11, color: 'var(--text2)', transition: 'all 0.1s',
                      borderTop: '1px solid var(--border)', display: 'block'
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = 'var(--sky)'}
                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text2)'}>
                    {ex.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* ── Editor + Results ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Editor */}
          <div style={{ flexShrink: 0, borderBottom: '1px solid var(--border2)' }}
            onKeyDown={handleKeyDown}>
            <CodeMirror
              value={sql}
              onChange={setSql}
              extensions={[sqlLang()]}
              theme={oneDark}
              style={{ fontSize: 13 }}
              basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
            />
          </div>

          {/* Toolbar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px',
            borderBottom: '1px solid var(--border)', background: 'var(--bg2)', flexShrink: 0
          }}>
            <button onClick={runQuery} disabled={running} className="btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              {running
                ? <><Loader2 size={12} style={{ animation: 'spin 0.7s linear infinite' }} /> Running…</>
                : <><Play size={12} /> Run  <kbd style={{ fontSize: 9, opacity: 0.6, marginLeft: 2 }}>⌘↵</kbd></>
              }
            </button>

            <button onClick={explainQuery} disabled={aiLoading || !sql.trim()} className="btn-ghost"
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                color: activeTab === 'explain' && aiLoading ? 'var(--sky)' : undefined
              }}>
              {activeTab === 'explain' && aiLoading
                ? <><Loader2 size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> Thinking…</>
                : <><BookOpen size={11} /> Explain</>}
            </button>
            <button onClick={optimizeQuery} disabled={aiLoading || !sql.trim()} className="btn-ghost"
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                color: activeTab === 'optimize' && aiLoading ? 'var(--sky)' : undefined
              }}>
              {activeTab === 'optimize' && aiLoading
                ? <><Loader2 size={11} style={{ animation: 'spin 0.7s linear infinite' }} /> Thinking…</>
                : <><TrendingUp size={11} /> Optimize</>}
            </button>

            {result && !error && (
              <span style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginLeft: 4 }}>
                <span style={{ color: 'var(--green)' }}>✓</span> {result.row_count} rows
                {result.exec_ms && ` · ${result.exec_ms}ms`}
                {result.truncated && ' · truncated'}
              </span>
            )}


          </div>

          {/* Output panel */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <AnimatePresence mode="wait">
              {activeTab === 'results' && (
                <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                  {error ? (
                    <div style={{ padding: 16 }}>
                      <div style={{
                        padding: '12px 16px', borderRadius: 9,
                        background: 'var(--red-soft)', border: '1px solid rgba(248,113,113,0.2)'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
                          <AlertCircle size={13} style={{ color: 'var(--red)' }} />
                          <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--red)' }}>SQL Error</p>
                        </div>
                        <p style={{
                          fontSize: 12, color: 'var(--red)', fontFamily: 'var(--mono)',
                          marginBottom: groqApiKey ? 10 : 0
                        }}>{error}</p>
                        <button onClick={handleFix} disabled={fixing} className="btn-ghost"
                          style={{
                            fontSize: 11, color: 'var(--yellow)', borderColor: 'rgba(252,211,77,0.3)',
                            display: 'flex', alignItems: 'center', gap: 5
                          }}>
                          {fixing
                            ? <><Loader2 size={10} style={{ animation: 'spin 0.7s linear infinite' }} /> Fixing…</>
                            : <><Sparkles size={10} /> AI Fix</>}
                        </button>
                      </div>
                    </div>
                  ) : result ? (
                    <ResultsTable result={result} />
                  ) : (
                    <div style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center',
                      justifyContent: 'center', flex: 1, color: 'var(--text3)', gap: 8
                    }}>
                      <Play size={28} style={{ opacity: 0.15 }} />
                      <p style={{ fontSize: 13 }}>Run a query to see results</p>
                      <p style={{ fontSize: 11 }}>⌘ + Enter to run</p>
                    </div>
                  )}
                </motion.div>
              )}
              {activeTab === 'explain' && (
                <motion.div key="explain" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  style={{ flex: 1, overflow: 'auto' }}>
                  <ExplainPanel data={explanation} loading={aiLoading} />
                </motion.div>
              )}
              {activeTab === 'optimize' && (
                <motion.div key="optimize" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  style={{ flex: 1, overflow: 'auto' }}>
                  <OptimizePanel data={optimization} loading={aiLoading}
                    onApply={(s) => { setSql(s); setActiveTab('results') }} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* ── History drawer ── */}
        <AnimatePresence>
          {showHistory && (
            <motion.aside initial={{ width: 0, opacity: 0 }} animate={{ width: 260, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              style={{
                borderLeft: '1px solid var(--border2)', background: 'var(--bg2)',
                overflow: 'hidden', flexShrink: 0
              }}>
              <div style={{ width: 260, height: '100%', overflow: 'auto' }}>
                <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
                  <p style={{
                    fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)',
                    textTransform: 'uppercase', letterSpacing: '0.08em'
                  }}>
                    Recent Queries
                  </p>
                </div>
                <div style={{ padding: '6px 8px' }}>
                  {history.length === 0 && (
                    <p style={{ fontSize: 12, color: 'var(--text3)', textAlign: 'center', padding: 24 }}>
                      No history yet
                    </p>
                  )}
                  {history.map(h => (
                    <div key={h.id} onClick={() => { loadFromHistory(h); setShowHistory(false) }}
                      style={{
                        padding: '9px 10px', borderRadius: 8, marginBottom: 3, cursor: 'pointer',
                        border: '1px solid transparent', transition: 'all 0.12s'
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.borderColor = 'var(--border2)' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                        {h.had_error
                          ? <AlertCircle size={10} style={{ color: 'var(--red)', flexShrink: 0 }} />
                          : <Check size={10} style={{ color: 'var(--green)', flexShrink: 0 }} />}
                        <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                          {h.row_count != null ? `${h.row_count} rows` : 'error'} · {h.exec_ms}ms
                        </span>
                      </div>
                      <p style={{
                        fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {h.sql.trim().slice(0, 60)}
                      </p>
                      <p style={{ fontSize: 10, color: 'var(--text3)', marginTop: 3 }}>
                        {h.created_at ? formatDistanceToNow(new Date(h.created_at), { addSuffix: true }) : ''}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}