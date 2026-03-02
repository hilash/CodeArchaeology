/* Shared code runner */
var RUNNABLE_SERVER = ['.py','.pyw','.c','.cpp','.cc','.cxx'];
var RUNNABLE_CLIENT = ['.js','.html','.htm'];
var RUNNABLE_EXTS = RUNNABLE_SERVER.concat(RUNNABLE_CLIENT);

function getFileExt(filename) {
    var dot = filename.lastIndexOf('.');
    return dot !== -1 ? filename.substring(dot).toLowerCase() : '';
}

function isRunnable(filename) {
    return RUNNABLE_EXTS.indexOf(getFileExt(filename)) !== -1;
}

function runFile(projectName, filename, code, outputEl, btn, stdin) {
    var ext = getFileExt(filename);
    btn.disabled = true;
    outputEl.style.display = 'block';
    outputEl.className = 'run-output run-running';

    if (RUNNABLE_SERVER.indexOf(ext) !== -1) {
        outputEl.textContent = 'Running...';
        fetch('/run/' + encodeURIComponent(projectName) + '/' + encodeURIComponent(filename), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({stdin: stdin || ''})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            btn.disabled = false;
            if (data.success) {
                outputEl.className = 'run-output';
                outputEl.textContent = data.stdout || '(no output)';
            } else {
                outputEl.className = 'run-output run-error';
                outputEl.textContent = (data.stderr || data.error || 'Unknown error');
            }
        })
        .catch(function(err) {
            btn.disabled = false;
            outputEl.className = 'run-output run-error';
            outputEl.textContent = 'Request failed: ' + err.message;
        });
    } else if (ext === '.js') {
        outputEl.textContent = 'Running JavaScript...';
        var logs = [];
        var iframe = document.createElement('iframe');
        iframe.setAttribute('sandbox', 'allow-scripts');
        iframe.style.display = 'none';
        document.body.appendChild(iframe);

        function onMsg(e) {
            if (e.source === iframe.contentWindow) {
                logs.push(e.data);
            }
        }
        window.addEventListener('message', onMsg);

        var wrappedCode = '(' + function() {
            var _log = [];
            console.log = function() {
                var args = Array.prototype.slice.call(arguments);
                var line = args.map(function(a) {
                    return typeof a === 'object' ? JSON.stringify(a) : String(a);
                }).join(' ');
                _log.push(line);
                parent.postMessage(line, '*');
            };
            console.error = console.warn = console.info = console.log;
            try {
                /* __CODE__ */
            } catch(e) {
                parent.postMessage('Error: ' + e.message, '*');
            }
            parent.postMessage('__DONE__', '*');
        }.toString().replace('/* __CODE__ */', code) + ')()';

        iframe.srcdoc = '<html><body><script>' + wrappedCode + '<\/script></body></html>';

        var timeout = setTimeout(function() {
            window.removeEventListener('message', onMsg);
            document.body.removeChild(iframe);
            btn.disabled = false;
            outputEl.className = 'run-output run-error';
            outputEl.textContent = logs.join('\n') + '\n(timed out after 5s)';
        }, 5000);

        var origOnMsg = onMsg;
        onMsg = function(e) {
            if (e.source !== iframe.contentWindow) return;
            if (e.data === '__DONE__') {
                clearTimeout(timeout);
                window.removeEventListener('message', onMsg);
                document.body.removeChild(iframe);
                btn.disabled = false;
                outputEl.className = 'run-output';
                outputEl.textContent = logs.join('\n') || '(no output)';
                return;
            }
            logs.push(e.data);
        };
        window.removeEventListener('message', origOnMsg);
        window.addEventListener('message', onMsg);
    } else if (ext === '.html' || ext === '.htm') {
        outputEl.textContent = '';
        outputEl.className = 'run-output';
        var iframe = document.createElement('iframe');
        iframe.className = 'run-iframe';
        iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
        iframe.src = '/raw/' + encodeURIComponent(projectName) + '/' + encodeURIComponent(filename);
        outputEl.appendChild(iframe);
        btn.disabled = false;
    }
}

function addRunButton(container, projectName, filename, code) {
    if (!isRunnable(filename)) return;
    var ext = getFileExt(filename);
    var needsStdin = RUNNABLE_SERVER.indexOf(ext) !== -1;
    var controls = document.createElement('div');
    controls.className = 'run-controls';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'run-btn-inline';
    btn.textContent = 'Run';
    controls.appendChild(btn);
    var stdinInput = null;
    if (needsStdin) {
        stdinInput = document.createElement('input');
        stdinInput.type = 'text';
        stdinInput.className = 'stdin-input';
        stdinInput.placeholder = 'stdin (e.g. 5 10 hello)';
        controls.appendChild(stdinInput);
        stdinInput.addEventListener('click', function(e) { e.stopPropagation(); });
        stdinInput.addEventListener('keydown', function(e) {
            e.stopPropagation();
            if (e.key === 'Enter') btn.click();
        });
    }
    var output = document.createElement('pre');
    output.className = 'run-output';
    output.style.display = 'none';
    controls.appendChild(output);
    container.appendChild(controls);
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var stdin = stdinInput ? stdinInput.value : '';
        runFile(projectName, filename, code, output, btn, stdin);
    });
}

/* Keyboard shortcut: Ctrl+Enter to run code */
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        var runBtn = document.getElementById('run-btn');
        if (runBtn && !runBtn.disabled) {
            runBtn.click();
        }
    }
});

/* Persist view mode in localStorage */
document.addEventListener('DOMContentLoaded', function() {
    var viewSelect = document.querySelector('select[name="view"]');
    if (viewSelect) {
        var params = new URLSearchParams(window.location.search);
        var saved = localStorage.getItem('viewMode');
        if (saved && !params.has('view')) {
            params.set('view', saved);
            window.location.search = params.toString();
            return;
        }
        viewSelect.addEventListener('change', function() {
            localStorage.setItem('viewMode', viewSelect.value);
        });
        if (params.has('view')) {
            localStorage.setItem('viewMode', params.get('view'));
        }
    }

    /* Select-all checkbox for table view */
    var selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            var checkboxes = document.querySelectorAll('input[name="selected"]');
            checkboxes.forEach(function(cb) { cb.checked = selectAll.checked; });
        });
    }

    /* Prevent clicks inside detail rows from bubbling to project rows */
    document.querySelectorAll('.detail-row').forEach(function(dr) {
        dr.addEventListener('click', function(e) { e.stopPropagation(); });
    });

    /* Expandable table rows */
    var rows = document.querySelectorAll('.project-row');
    rows.forEach(function(row) {
        if (row.classList.contains('intro-row')) return; // intro has its own toggleIntro() handler
        row.addEventListener('click', function() {
            var detailRow = row.nextElementSibling;
            if (!detailRow || !detailRow.classList.contains('detail-row')) return;

            // If already open, toggle closed
            if (detailRow.style.display !== 'none') {
                detailRow.style.display = 'none';
                row.classList.remove('row-expanded');
                return;
            }

            // Close any other open detail rows (but not the intro)
            document.querySelectorAll('.detail-row:not(.intro-detail)').forEach(function(r) { r.style.display = 'none'; });
            document.querySelectorAll('.project-row:not(.intro-row)').forEach(function(r) { r.classList.remove('row-expanded'); });

            // Open this one
            detailRow.style.display = 'table-row';
            row.classList.add('row-expanded');

            // Load content if not already loaded
            var panel = detailRow.querySelector('.detail-panel');
            if (panel.querySelector('.detail-loading')) {
                var name = row.getAttribute('data-name');
                fetch('/api/project/' + encodeURIComponent(name))
                    .then(function(r) { return r.json(); })
                    .then(function(data) { renderDetailPanel(panel, data); })
                    .catch(function() { panel.innerHTML = '<p style="color:var(--red)">Failed to load project details.</p>'; });
            }
        });
    });
});

function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderDetailPanel(panel, data) {
    var left = '';
    var right = '';

    // -- Left side: description --
    left += '<h3>' + escapeHtml(data.clean_title || data.name) + '</h3>';

    if (data.summary) {
        left += '<p class="detail-summary">' + escapeHtml(data.summary) + '</p>';
    }

    if (data.topics && data.topics.length) {
        left += '<div class="detail-topics">';
        data.topics.forEach(function(t) {
            left += '<span class="tag-sm">' + escapeHtml(t) + '</span> ';
        });
        left += '</div>';
    }

    left += '<div class="detail-meta">';
    if (data.date) left += '<div><strong>Date:</strong> ' + escapeHtml(data.date) + '</div>';
    if (data.sender) left += '<div><strong>From:</strong> ' + escapeHtml(data.sender) + '</div>';
    if (data.subject) left += '<div><strong>Subject:</strong> ' + escapeHtml(data.subject) + '</div>';
    left += '</div>';

    if (data.euler_problems) {
        left += '<div class="detail-euler">';
        left += '<strong>Project Euler:</strong> ' + escapeHtml(data.euler_problems);
        if (data.euler_links && data.euler_links.length) {
            left += '<div class="detail-euler-links">';
            data.euler_links.forEach(function(link) {
                left += '<a href="' + escapeHtml(link) + '" target="_blank">' + escapeHtml(link) + '</a> ';
            });
            left += '</div>';
        }
        left += '</div>';
    } else if (data.explanation) {
        left += '<div class="detail-explanation">' + escapeHtml(data.explanation) + '</div>';
    } else if (data.body) {
        left += '<pre class="detail-body">' + escapeHtml(data.body) + '</pre>';
    }

    left += '<div class="detail-actions">';
    left += '<a href="/project/' + encodeURIComponent(data.name) + '" class="detail-open-btn">Open Full Page</a>';
    left += '</div>';

    // -- Right side: file viewer --
    if (data.files && data.files.length > 0) {
        right += '<div class="detail-file-tabs">';
        data.files.forEach(function(f, i) {
            right += '<button type="button" class="file-tab' + (i === 0 ? ' active' : '') + '" data-idx="' + i + '">' + escapeHtml(f.filename) + '</button>';
        });
        right += '</div>';

        right += '<div class="detail-file-contents">';
        data.files.forEach(function(f, i) {
            right += '<div class="file-content-pane' + (i === 0 ? ' active' : '') + '" data-idx="' + i + '">';
            var imgExts = ['.jpg','.jpeg','.png','.gif','.bmp','.svg','.webp'];
            var fext = f.filename.substring(f.filename.lastIndexOf('.')).toLowerCase();
            if (imgExts.indexOf(fext) !== -1) {
                right += '<div class="detail-image"><img src="/raw/' + encodeURIComponent(data.name) + '/' + encodeURIComponent(f.filename) + '" alt="' + escapeHtml(f.filename) + '"></div>';
            } else if (f.binary) {
                right += '<div class="detail-binary">Binary file</div>';
            } else if (f.content) {
                var langClass = f.language ? ' class="language-' + escapeHtml(f.language.toLowerCase()) + '"' : '';
                right += '<pre class="detail-code"><code' + langClass + '>' + escapeHtml(f.content) + '</code></pre>';
            } else {
                right += '<div class="detail-binary">Empty file</div>';
            }
            right += '</div>';
        });
        right += '</div>';
    } else {
        right += '<div class="detail-binary">No files</div>';
    }

    panel.innerHTML =
        '<div class="detail-left">' + left + '</div>' +
        '<div class="detail-right">' + right + '</div>';

    // Apply syntax highlighting
    panel.querySelectorAll('pre.detail-code code').forEach(function(block) {
        hljs.highlightElement(block);
    });

    // Wire up file tabs
    var tabs = panel.querySelectorAll('.file-tab');
    var panes = panel.querySelectorAll('.file-content-pane');
    tabs.forEach(function(tab) {
        tab.addEventListener('click', function(e) {
            e.stopPropagation();
            tabs.forEach(function(t) { t.classList.remove('active'); });
            panes.forEach(function(p) { p.classList.remove('active'); });
            tab.classList.add('active');
            var idx = tab.getAttribute('data-idx');
            panel.querySelector('.file-content-pane[data-idx="' + idx + '"]').classList.add('active');
        });
    });
}
