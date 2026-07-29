document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadPreferences();
  loadJobs();
  loadLogs();
  setInterval(loadLogs, 10000);
});

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    
    document.getElementById('statFound').innerText = data.total_scraped_today || 0;
    document.getElementById('statAlerted').innerText = data.listings_alerted_today || 0;
    document.getElementById('statApplied').innerText = data.total_applied || 0;
    document.getElementById('statAvgScore').innerText = `${data.avg_fit_score || 0}%`;

    const discordStatusText = document.getElementById('discordStatusText');
    const discordDot = document.getElementById('discordDot');

    if (data.discord_connected) {
      discordStatusText.innerText = 'Discord Connected';
      discordDot.className = 'dot online';
    } else {
      discordStatusText.innerText = 'Discord Standby';
      discordDot.className = 'dot offline';
    }
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

async function loadPreferences() {
  try {
    const res = await fetch('/api/preferences');
    const data = await res.json();
    
    document.getElementById('prefRoles').value = (data.target_roles || []).join(', ');
    document.getElementById('prefWorkTypes').value = (data.work_type_priority || []).join(', ');
    document.getElementById('prefLocations').value = (data.locations || []).join(', ');
    document.getElementById('prefMinStipend').value = data.min_stipend || 0;
    document.getElementById('stipendVal').innerText = data.min_stipend || 0;
  } catch (err) {
    console.error('Failed to load preferences:', err);
  }
}

async function handleSavePreferences(e) {
  e.preventDefault();
  const body = {
    target_roles: document.getElementById('prefRoles').value.split(',').map(s => s.trim()).filter(Boolean),
    work_type_priority: document.getElementById('prefWorkTypes').value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
    locations: document.getElementById('prefLocations').value.split(',').map(s => s.trim()).filter(Boolean),
    min_stipend: parseFloat(document.getElementById('prefMinStipend').value),
    skills_to_match: ["Python", "FastAPI", "Machine Learning", "AI", "SQL"]
  };

  try {
    await fetch('/api/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    alert('Search preferences updated!');
    loadJobs();
  } catch (err) {
    alert('Failed to save preferences: ' + err);
  }
}

async function loadJobs() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    const container = document.getElementById('feedContainer');
    document.getElementById('feedCount').innerText = `Showing ${jobs.length} listings`;

    if (!jobs || jobs.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem;">No qualifying internship listings found yet. Click <strong>Run Now</strong> to scrape!</p>';
      return;
    }

    container.innerHTML = jobs.map(j => {
      const isApplied = j.status === 'applied';
      const scoreClass = j.fit_score >= 80 ? '' : 'medium';
      const workClass = (j.work_type || 'remote').toLowerCase();
      const logoLetter = (j.company || 'C').charAt(0).toUpperCase();

      const matchBullets = (j.match_reasons || [])
        .map(r => `<li>${r}</li>`)
        .join('');

      return `
        <div class="job-card">
          <div class="company-logo">${logoLetter}</div>
          <div class="job-details">
            <h3>${j.title}</h3>
            <div class="company-name">${j.company} &bull; ${j.location} &bull; <strong>${j.stipend}</strong></div>
            <div class="meta-tags">
              <span class="tag ${workClass}">${(j.work_type || 'Remote').toUpperCase()}</span>
              <span class="tag">${j.platform}</span>
            </div>
            <ul class="match-reasons">${matchBullets || '<li>Matches target profile</li>'}</ul>
            <div class="actions-row">
              ${isApplied 
                ? '<button class="btn-sm btn-applied" disabled>✓ Applied</button>' 
                : `<button class="btn-sm btn-mark" onclick="markApplied('${j.id}')">Mark Applied</button>`
              }
              <a href="${j.url}" target="_blank" class="btn-sm btn-open">Open Listing ↗</a>
            </div>
          </div>
          <div class="score-circle ${scoreClass}">
            <span>${j.fit_score}%</span>
            <span style="font-size: 0.6rem; color: var(--text-muted);">MATCH</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load jobs:', err);
  }
}

async function markApplied(jobId) {
  try {
    await fetch(`/api/jobs/${jobId}/apply`, { method: 'POST' });
    loadJobs();
    loadStats();
  } catch (err) {
    console.error('Failed to mark applied:', err);
  }
}

async function loadLogs() {
  try {
    const res = await fetch('/api/logs');
    const logs = await res.json();
    const container = document.getElementById('logsBox');
    container.innerHTML = logs.map(l => `
      <div class="log-entry ${l.level}">[${l.timestamp}] [${l.category.toUpperCase()}] ${l.message}</div>
    `).join('');
  } catch (err) {
    console.error('Failed to load logs:', err);
  }
}

async function triggerRunNow() {
  try {
    await fetch('/api/run-now', { method: 'POST' });
    alert('⚡ Scrape cycle initiated! Check activity logs below.');
    setTimeout(() => { loadJobs(); loadStats(); loadLogs(); }, 5000);
  } catch (err) {
    alert('Failed to trigger run cycle: ' + err);
  }
}
