const { useEffect, useState, useRef } = React;

function api(path, opts={}) {
  return fetch(path, opts).then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json().catch(() => ({}));
  });
}

function Sidebar({ jobs, onUpload }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const onDrop = async (e) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files?.[0]; if (!file) return;
    await onUpload(file);
  };
  const onSelectFile = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    await onUpload(file); e.target.value = '';
  };

  return (
    React.createElement('div', { className: 'left' },
      React.createElement('h3', null, 'Queue & Upload'),
      React.createElement('div', {
        className: 'drop',
        onDragOver: (e) => { e.preventDefault(); setDragOver(true); },
        onDragLeave: () => setDragOver(false),
        onDrop,
        style: { background: dragOver ? '#f7f7ff' : 'transparent' }
      },
        React.createElement('p', null, 'Drag & drop a .blend here, or'),
        React.createElement('button', { onClick: () => inputRef.current?.click() }, 'Choose file')
      ),
      React.createElement('input', { type: 'file', accept: '.blend', style: { display: 'none' }, ref: inputRef, onChange: onSelectFile }),
      React.createElement('h4', null, 'Jobs'),
      React.createElement('select', { className: 'jobs', size: 12 },
        jobs.map(j => React.createElement('option', { key: j.id }, `#${j.id} · ${j.status} · ${j.name}`))
      ),
      React.createElement('p', { className: 'muted' }, 'Newest first. Auto-refreshing.')
    )
  );
}

function FolderView() {
  const [folders, setFolders] = useState([]);
  const refresh = async () => { const d = await api('/api/folders'); setFolders(d.folders || []); };
  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, []);
  return (
    React.createElement('div', { className: 'right' },
      React.createElement('h3', null, 'Renders'),
      folders.length === 0 && React.createElement('p', { className: 'muted' }, 'No folders yet. Upload a .blend to start.'),
      folders.map(f =>
        React.createElement('div', { key: f.folder, className: 'folder' },
          React.createElement('div', { className: 'row' },
            React.createElement('strong', null, f.folder),
            React.createElement('span', { className: 'muted' }, `${f.files.length} file(s)`)
          ),
          React.createElement('div', null,
            f.files.map(file =>
              React.createElement('div', { key: file, className: 'file' },
                React.createElement('a', { href: `/api/download/${encodeURIComponent(f.folder)}/${encodeURIComponent(file)}` }, file)
              )
            )
          )
        )
      )
    )
  );
}

function App() {
  const [jobs, setJobs] = useState([]);
  const upload = async (file) => {
    if (!file.name.endsWith('.blend')) { alert('Please upload a .blend file'); return; }
    const fd = new FormData(); fd.append('file', file);
    await api('/api/upload', { method: 'POST', body: fd });
  };
  const refreshJobs = async () => { const d = await api('/api/jobs'); setJobs(d.jobs || []); };
  useEffect(() => { refreshJobs(); const t = setInterval(refreshJobs, 2000); return () => clearInterval(t); }, []);
  return React.createElement('div', { className: 'wrap' },
    React.createElement(Sidebar, { jobs, onUpload: upload }),
    React.createElement(FolderView, null)
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));