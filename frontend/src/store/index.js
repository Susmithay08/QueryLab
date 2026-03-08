import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

export const useStore = create(
  persist(
    (set, get) => ({
      groqApiKey: '',
      setGroqApiKey: (k) => set({ groqApiKey: k }),

      databases: [],
      activeDb: 'ecommerce',
      schema: [],
      examples: [],

      sql: 'SELECT * FROM products\nLIMIT 10',
      result: null,
      running: false,
      error: null,

      explanation: null,
      optimization: null,
      aiLoading: false,

      history: [],
      activeTab: 'results',  // results | explain | optimize
      setActiveTab: (tab) => set({ activeTab: tab }),

      uploadCSV: async (file) => {
        const fd = new FormData()
        fd.append('file', file)
        const r = await fetch(`${API}/csv/upload`, { method: 'POST', body: fd })
        if (!r.ok) {
          const err = await r.json()
          throw new Error(err.detail || 'Upload failed')
        }
        const data = await r.json()
        // Refresh databases list and switch to new db
        await get().fetchDatabases()
        get().setDb(data.id)
        return data
      },

      deleteUserDB: async (id) => {
        await fetch(`${API}/csv/${id}`, { method: 'DELETE' })
        await get().fetchDatabases()
        const { activeDb } = get()
        if (activeDb === id) get().setDb('ecommerce')
      },

      fetchDatabases: async () => {
        const r = await fetch(`${API}/databases`)
        const data = await r.json()
        set({ databases: data })
      },

      fetchSchema: async (db) => {
        const r = await fetch(`${API}/databases/${db}/schema`)
        const data = await r.json()
        set({ schema: data })
      },

      fetchExamples: async (db) => {
        const r = await fetch(`${API}/examples/${db}`)
        const data = await r.json()
        set({ examples: data })
      },

      setDb: (db) => {
        set({ activeDb: db, result: null, explanation: null, optimization: null })
        get().fetchSchema(db)
        get().fetchExamples(db)
      },

      setSql: (sql) => set({ sql }),

      runQuery: async () => {
        const { sql, activeDb, groqApiKey } = get()
        set({ running: true, error: null, result: null, explanation: null, optimization: null, activeTab: 'results' })
        try {
          const r = await fetch(`${API}/query/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              sql, database: activeDb,
              groq_api_key: groqApiKey || undefined,
              auto_explain: false,
            }),
          })
          const data = await r.json()
          if (data.error) set({ error: data.error, result: null })
          else set({ result: data, error: null })
          get().fetchHistory()
        } catch (e) {
          set({ error: e.message })
        } finally {
          set({ running: false })
        }
      },

      explainQuery: async () => {
        const { sql, activeDb, groqApiKey } = get()
        set({ aiLoading: true, activeTab: 'explain', explanation: null })
        try {
          const r = await fetch(`${API}/query/explain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, database: activeDb, groq_api_key: groqApiKey || undefined }),
          })
          const data = await r.json()
          set({ explanation: data })
        } catch (e) {
          set({ explanation: { error: e.message } })
        } finally {
          set({ aiLoading: false })
        }
      },

      optimizeQuery: async () => {
        const { sql, activeDb, groqApiKey } = get()
        set({ aiLoading: true, activeTab: 'optimize', optimization: null })
        try {
          const r = await fetch(`${API}/query/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, database: activeDb, groq_api_key: groqApiKey || undefined }),
          })
          const data = await r.json()
          set({ optimization: data })
        } catch (e) {
          set({ optimization: { error: e.message } })
        } finally {
          set({ aiLoading: false })
        }
      },

      fixQuery: async (error) => {
        const { sql, activeDb, groqApiKey } = get()
        set({ aiLoading: true })
        const r = await fetch(`${API}/query/fix`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql, database: activeDb, error, groq_api_key: groqApiKey || undefined }),
        })
        const data = await r.json()
        if (data.fixed_sql) set({ sql: data.fixed_sql })
        set({ aiLoading: false })
        return data
      },

      shareQuery: async () => {
        const { sql, activeDb } = get()
        const r = await fetch(`${API}/query/share`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql, database: activeDb }),
        })
        return await r.json()
      },

      fetchHistory: async () => {
        const { activeDb } = get()
        const r = await fetch(`${API}/history?database=${activeDb}&limit=20`)
        const data = await r.json()
        if (Array.isArray(data)) set({ history: data })
      },

      loadFromHistory: (item) => {
        set({ sql: item.sql, result: null, explanation: null, optimization: null })
      },
    }),
    { name: 'querylab-store', partialState: s => ({ groqApiKey: s.groqApiKey, activeDb: s.activeDb, sql: s.sql }) }
  )
)