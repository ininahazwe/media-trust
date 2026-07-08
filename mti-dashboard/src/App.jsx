import React, { useState, useEffect } from 'react';

const API_URL = 'https://index-media.mfwa.org';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function ScoreBar({ value, max = 100 }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
      <div style={{ width: '100%', height: 8, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #6366f1, #8b5cf6)', borderRadius: 4, transition: 'width 0.6s ease' }} />
      </div>
  );
}

const MEDAL = [
  { background: '#fcd34d', color: '#92400e' },
  { background: '#d1d5db', color: '#374151' },
  { background: '#fed7aa', color: '#b45309' },
  { background: '#e0e7ff', color: '#4f46e5' },
  { background: '#f3f4f6', color: '#6b7280' },
];

const MEDIA_TYPES = ['All Media', 'Radio', 'TV', 'Online', 'Print'];

const DIM_LABELS = {
  accuracy: 'Accuracy',
  verification: 'Verification',
  independence: 'Independence',
  fair_balanced: 'Fairness',
  public_interest: 'Public Interest',
  corrections: 'Corrections',
};

const REGION_LABELS = {
  greater_accra: 'Greater Accra',
  ashanti: 'Ashanti',
  eastern: 'Eastern',
  western: 'Western',
  northern: 'Northern',
  central: 'Central',
  volta: 'Volta',
  upper_east: 'Upper East',
  upper_west: 'Upper West',
  bono: 'Bono',
};

const ALIGN_LABELS = {
  npp: 'NPP',
  ndc: 'NDC',
  independent: 'Independent',
  none: 'No clear bias',
};

const ALIGN_COLORS = {
  npp: '#fee2e2',
  ndc: '#dbeafe',
  independent: '#dcfce7',
  none: '#e9d5ff',
};

// ─── Styles ───────────────────────────────────────────────────────────────────

const S = {
  root: { fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: '#f8f7f5', color: '#1a1a1a', minHeight: '100vh' },
  wrap: { maxWidth: 1200, margin: '0 auto', padding: '32px 24px' },
  header: { marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 },
  h1: { margin: 0, fontSize: 28, fontWeight: 600 },
  sub: { margin: '4px 0 0', color: '#999', fontSize: 13 },
  filterGroup: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  btn: (active) => ({
    padding: '8px 16px', border: `1px solid ${active ? '#6366f1' : '#ddd'}`,
    background: active ? '#6366f1' : 'white', color: active ? 'white' : '#1a1a1a',
    borderRadius: 6, fontSize: 13, cursor: 'pointer', transition: 'all 0.2s',
  }),
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 32 },
  metricCard: { background: 'white', padding: 20, borderRadius: 12, border: '1px solid #e0e0e0' },
  metricLabel: { fontSize: 12, color: '#999', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 },
  metricValue: (small) => ({ fontSize: small ? 20 : 32, fontWeight: 600, color: '#6366f1', marginBottom: 4 }),
  metricSub: (positive) => ({ fontSize: 12, color: positive ? '#10b981' : '#666' }),
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, marginBottom: 24 },
  card: { background: 'white', padding: 24, borderRadius: 12, border: '1px solid #e0e0e0' },
  cardTitle: { margin: '0 0 4px', fontSize: 16, fontWeight: 600 },
  cardSub: { margin: '0 0 16px', fontSize: 12, color: '#999' },
  barRow: { display: 'flex', alignItems: 'center', marginBottom: 14 },
  barLabel: { width: 110, fontSize: 12, fontWeight: 500, color: '#666', flexShrink: 0 },
  barValue: { width: 40, textAlign: 'right', fontSize: 13, fontWeight: 600 },
  rankRow: { display: 'flex', alignItems: 'center', marginBottom: 14 },
  rankNum: (i) => ({ width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 13, marginRight: 12, flexShrink: 0, ...(MEDAL[i] || MEDAL[4]) }),
  rankInfo: { flex: 1 },
  rankName: { fontSize: 14, fontWeight: 500, marginBottom: 2 },
  rankScore: { fontSize: 12, color: '#999' },
  rankBar: { width: 70, marginLeft: 'auto', textAlign: 'right' },
  rankValue: { fontSize: 13, fontWeight: 600, color: '#6366f1', marginTop: 2 },
  tag: { display: 'inline-block', padding: '4px 10px', background: '#eef2ff', color: '#4f46e5', borderRadius: 4, fontSize: 11, fontWeight: 500 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: 12, borderBottom: '1px solid #e0e0e0', background: '#f8f7f5', fontWeight: 600, color: '#666' },
  td: { padding: 12, borderBottom: '1px solid #e0e0e0' },
  sparkWrap: { height: 100, display: 'flex', alignItems: 'flex-end', gap: 3 },
  sparkBar: (h) => ({ flex: 1, height: `${h}%`, background: '#6366f1', borderRadius: '2px 2px 0 0', opacity: 0.75 }),
  noData: { color: '#aaa', fontSize: 13, textAlign: 'center', padding: '24px 0' },
};

// ─── Loading / Error ──────────────────────────────────────────────────────────

function Loading() {
  return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#f8f7f5' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 48, height: 48, border: '3px solid #e0e0e0', borderTop: '3px solid #6366f1', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 16px' }} />
          <p style={{ color: '#666', margin: 0 }}>Loading dashboard…</p>
          <p style={{ color: '#aaa', fontSize: 12, marginTop: 6 }}>Syncing with Kobo Toolkit</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
  );
}

// ─── Blocks ───────────────────────────────────────────────────────────────────

function TopRankings({ outlets }) {
  const top5 = outlets.slice(0, 5);
  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Top 5 Most Trusted Media</p>
        <p style={S.cardSub}>by Media Trust Index (0–100)</p>
        {top5.length === 0 && <p style={S.noData}>No data</p>}
        {top5.map((o, i) => (
            <div key={i} style={S.rankRow}>
              <div style={S.rankNum(i)}>{i + 1}</div>
              <div style={S.rankInfo}>
                <div style={S.rankName}>{o.name}</div>
                <div style={S.rankScore}>{o.type || 'Media'} • {o.responses_count ?? '—'} responses</div>
              </div>
              <div style={S.rankBar}>
                <ScoreBar value={o.mti_score || o.score || 0} />
                <div style={S.rankValue}>{(o.mti_score || o.score || 0).toFixed(1)}</div>
              </div>
            </div>
        ))}
      </div>
  );
}

function DimensionBars({ dimensions }) {
  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Trust Dimensions</p>
        <p style={S.cardSub}>Average scores across all media</p>
        {Object.entries(DIM_LABELS).map(([key, label]) => {
          const val = Math.round(dimensions[key] || 0);
          return (
              <div key={key} style={S.barRow}>
                <div style={S.barLabel}>{label}</div>
                <div style={{ flex: 1, margin: '0 12px' }}><ScoreBar value={val} /></div>
                <div style={S.barValue}>{val}%</div>
              </div>
          );
        })}
      </div>
  );
}

function PlatformBars({ platforms }) {
  const items = [
    { label: 'Radio',       key: 'radio' },
    { label: 'TV',          key: 'tv' },
    { label: 'Online News', key: 'online' },
    { label: 'Social Media',key: 'social' },
    { label: 'WhatsApp',    key: 'whatsapp' },
    { label: 'YouTube',     key: 'youtube' },
    { label: 'Print',       key: 'print' },
    { label: 'Podcast',     key: 'podcast' },
  ].filter(({ key }) => (platforms[key] || 0) > 0);

  const maxVal = Math.max(...items.map(({ key }) => platforms[key] || 0), 1);

  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Usage by Platform</p>
        <p style={S.cardSub}>Respondents using each platform (last 7 days)</p>
        {items.length === 0 && <p style={S.noData}>No platform data yet</p>}
        {items.map(({ label, key }) => {
          const count = platforms[key] || 0;
          const pct = Math.round((count / maxVal) * 100);
          return (
              <div key={key} style={S.barRow}>
                <div style={S.barLabel}>{label}</div>
                <div style={{ flex: 1, margin: '0 12px' }}><ScoreBar value={pct} /></div>
                <div style={S.barValue}>{count}</div>
              </div>
          );
        })}
      </div>
  );
}

function RegionBars({ trustByRegion }) {
  const entries = Object.entries(trustByRegion)
      .map(([k, v]) => ({ region: REGION_LABELS[k] || k, avg: v }))
      .sort((a, b) => b.avg - a.avg);

  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Trust by Region</p>
        <p style={S.cardSub}>Average MTI across Ghana</p>
        {entries.length === 0 && <p style={S.noData}>No regional data yet</p>}
        {entries.map(({ region, avg }) => (
            <div key={region} style={S.barRow}>
              <div style={{ ...S.barLabel, width: 120 }}>{region}</div>
              <div style={{ flex: 1, margin: '0 12px' }}><ScoreBar value={avg} /></div>
              <div style={S.barValue}>{avg}</div>
            </div>
        ))}
      </div>
  );
}

function PoliticalBias({ politicalAlignment }) {
  const outlets = Object.entries(politicalAlignment);
  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Perceived Political Bias</p>
        <p style={S.cardSub}>% perceiving alignment by outlet</p>
        {outlets.length === 0 && <p style={S.noData}>No data yet</p>}
        {outlets.map(([outlet, counts]) => {
          const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
          const segments = Object.entries(counts).map(([align, n]) => ({
            align,
            pct: Math.round((n / total) * 100),
            color: ALIGN_COLORS[align] || '#f0f0f0',
            label: ALIGN_LABELS[align] || align,
          }));
          return (
              <div key={outlet} style={{ marginBottom: 16 }}>
                <p style={{ margin: '0 0 6px', fontSize: 12, fontWeight: 500 }}>{outlet}</p>
                <div style={{ display: 'flex', gap: 3, marginBottom: 4 }}>
                  {segments.map(({ align, pct, color }) => (
                      <div key={align} style={{ flex: pct, height: 8, background: color, borderRadius: 2, minWidth: 4 }} />
                  ))}
                </div>
                <p style={{ margin: 0, fontSize: 11, color: '#999' }}>
                  {segments.map(s => `${s.pct}% ${s.label}`).join(' • ')}
                </p>
              </div>
          );
        })}
      </div>
  );
}

const AGE_LABELS = {
  '15_24': '15–24',
  '25_34': '25–34',
  '35_44': '35–44',
  '45_54': '45–54',
  '55_64': '55–64',
  '65_plus': '65+',
};

function DemoBar({ data, title, labelMap }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  return (
      <div style={{ marginBottom: 20 }}>
        <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: '#444' }}>{title}</p>
        {entries.map(([key, count]) => {
          const pct = Math.round((count / total) * 100);
          const label = labelMap?.[key] || key.replace(/_/g, ' ');
          return (
              <div key={key} style={S.barRow}>
                <div style={{ ...S.barLabel, width: 100, textTransform: 'capitalize' }}>{label}</div>
                <div style={{ flex: 1, margin: '0 12px' }}><ScoreBar value={pct} /></div>
                <div style={S.barValue}>{pct}%</div>
              </div>
          );
        })}
      </div>
  );
}

function Demographics({ demographics }) {
  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Respondent Profile</p>
        <p style={S.cardSub}>Demographics of survey participants</p>
        <DemoBar data={demographics.sex || {}} title="Gender" />
        <DemoBar data={demographics.age_group || demographics.age || {}} title="Age Group" labelMap={AGE_LABELS} />
        <DemoBar data={demographics.education || {}} title="Education" />
        <DemoBar data={demographics.residence || {}} title="Residence" />
        <DemoBar data={demographics.internet_access || {}} title="Internet Access" />
        {Object.keys(demographics.smartphone || {}).length > 0 && (
            <DemoBar data={demographics.smartphone} title="Smartphone Access" />
        )}
      </div>
  );
}

function PartisanshipDetail({ analytics }) {
  if (!analytics?.partisanship) return null;
  const { gov_influence, owner_influence, political_pressure } = analytics.partisanship;
  const items = [
    { label: 'Gov. Influence',     value: gov_influence },
    { label: 'Owner Influence',    value: owner_influence },
    { label: 'Political Pressure', value: political_pressure },
  ].filter(({ value }) => value != null);

  if (items.length === 0) return null;

  return (
      <div style={S.card}>
        <p style={S.cardTitle}>Editorial Independence</p>
        <p style={S.cardSub}>Average perceived pressure on media (0–100, lower = more independent)</p>
        {items.map(({ label, value }) => (
            <div key={label} style={S.barRow}>
              <div style={{ ...S.barLabel, width: 140 }}>{label}</div>
              <div style={{ flex: 1, margin: '0 12px' }}>
                <div style={{ width: '100%', height: 8, background: '#f0f0f0', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${value}%`, height: '100%', background: 'linear-gradient(90deg, #10b981, #ef4444)', borderRadius: 4 }} />
                </div>
              </div>
              <div style={S.barValue}>{Math.round(value)}</div>
            </div>
        ))}
      </div>
  );
}
function SparklineTrend({ total }) {
  const heights = [60, 65, 68, 72, 75, 78, 83, 88];
  return (
      <div style={S.card}>
        <p style={S.cardTitle}>MTI Trend</p>
        <p style={S.cardSub}>Score evolution over submissions</p>
        <div style={S.sparkWrap}>
          {heights.map((h, i) => <div key={i} style={S.sparkBar(h)} />)}
        </div>
        <p style={{ margin: '12px 0 0', textAlign: 'center', fontSize: 12, color: '#666' }}>
          {total > 0 ? `${total} total submissions` : 'Awaiting submissions'}
        </p>
      </div>
  );
}

function OutletsTable({ outlets }) {
  return (
      <div style={{ ...S.card, marginTop: 0 }}>
        <p style={S.cardTitle}>All Outlets</p>
        <p style={S.cardSub}>Complete ranking by MTI Score</p>
        <div style={{ overflowX: 'auto' }}>
          <table style={S.table}>
            <thead>
            <tr>
              <th style={S.th}>#</th>
              <th style={S.th}>Outlet</th>
              <th style={S.th}>Type</th>
              <th style={S.th}>Region</th>
              <th style={S.th}>MTI Score</th>
              <th style={S.th}>Responses</th>
              <th style={S.th}>Bias</th>
              <th style={S.th}>Score</th>
            </tr>
            </thead>
            <tbody>
            {outlets.map((o, i) => {
              const score = o.mti_score || o.score || 0;
              const topAlign = o.political_alignment
                  ? Object.entries(o.political_alignment).sort((a, b) => b[1] - a[1])[0]
                  : null;
              return (
                  <tr key={i} style={{ background: i % 2 === 0 ? 'white' : '#fafafa' }}>
                    <td style={{ ...S.td, color: '#999' }}>{i + 1}</td>
                    <td style={{ ...S.td, fontWeight: 500 }}>{o.name}</td>
                    <td style={S.td}><span style={S.tag}>{o.type || 'Media'}</span></td>
                    <td style={{ ...S.td, color: '#666', textTransform: 'capitalize' }}>{(o.region || '—').replace(/_/g, ' ')}</td>
                    <td style={{ ...S.td, fontWeight: 700, color: '#6366f1', fontSize: 15 }}>{score.toFixed(1)}</td>
                    <td style={{ ...S.td, color: '#666' }}>{o.responses_count ?? '—'}</td>
                    <td style={S.td}>
                      {topAlign
                          ? <span style={{ ...S.tag, background: ALIGN_COLORS[topAlign[0]] || '#f0f0f0', color: '#444' }}>{ALIGN_LABELS[topAlign[0]] || topAlign[0]}</span>
                          : <span style={{ color: '#ccc' }}>—</span>
                      }
                    </td>
                    <td style={{ ...S.td, minWidth: 100 }}><ScoreBar value={score} /></td>
                  </tr>
              );
            })}
            </tbody>
          </table>
        </div>
      </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function MTIDashboard() {
  const [filter, setFilter] = useState('All Media');
  const [dash, setDash] = useState(null);
  const [outlets, setOutlets] = useState([]);
  const [dimensions, setDimensions] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);

        // 1. Sync Kobo
        const syncRes = await fetch(`${API_URL}/api/dashboard/sync-kobo`, { method: 'POST' });
        const syncData = await syncRes.json();
        setLastSync(syncData.last_sync);

        // 2. Parallel fetch
        const [dashRes, dimRes, outRes, anaRes] = await Promise.all([
          fetch(`${API_URL}/api/dashboard/`),
          fetch(`${API_URL}/api/dashboard/dimensions`),
          fetch(`${API_URL}/api/dashboard/outlets-details`),
          fetch(`${API_URL}/api/dashboard/analytics`),
        ]);

        const [dashData, dimData, outData, anaData] = await Promise.all([
          dashRes.json(), dimRes.json(), outRes.json(), anaRes.json(),
        ]);

        setDash(dashData);
        setDimensions(dimData);
        setOutlets(outData.outlets || outData.top_outlets || []);
        setAnalytics(anaData);
        setError(null);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    load();
    const iv = setInterval(load, 60000);
    return () => clearInterval(iv);
  }, []);

  if (loading) return <Loading />;
  if (error) return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: '#ef4444', fontWeight: 600 }}>Failed to load dashboard</p>
          <p style={{ color: '#666', fontSize: 13 }}>{error}</p>
        </div>
      </div>
  );
  if (!dash) return null;

  const filtered = filter === 'All Media'
      ? outlets
      : outlets.filter(o => (o.type || '').toLowerCase() === filter.toLowerCase());

  const best = filtered[0];

  return (
      <div style={S.root}>
        <div style={S.wrap}>

          {/* Header */}
          <div style={S.header}>
            <div>
              <h1 style={S.h1}>Media Trust Index</h1>
              <p style={S.sub}>Ghana Survey Round 1 • {dash.total_responses || 0} responses</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
              <div style={S.filterGroup}>
                {MEDIA_TYPES.map(t => (
                    <button key={t} style={S.btn(filter === t)} onClick={() => setFilter(t)}>{t}</button>
                ))}
              </div>
              {lastSync && (
                  <span style={{ fontSize: 11, color: '#aaa' }}>
                Last sync: {new Date(lastSync).toLocaleTimeString()}
              </span>
              )}
            </div>
          </div>

          {/* Metrics */}
          <div style={S.metricGrid}>
            <div style={S.metricCard}>
              <div style={S.metricLabel}>Average MTI Score</div>
              <div style={S.metricValue(false)}>{(dash.average_mti || 0).toFixed(1)}</div>
              <div style={S.metricSub(true)}>Based on {dash.total_responses || 0} responses</div>
            </div>
            <div style={S.metricCard}>
              <div style={S.metricLabel}>Most Trusted Outlet</div>
              <div style={S.metricValue(true)}>{best?.name || '—'}</div>
              <div style={S.metricSub(false)}>MTI: {(best?.mti_score || best?.score || 0).toFixed(1)}</div>
            </div>
            <div style={S.metricCard}>
              <div style={S.metricLabel}>Respondents</div>
              <div style={S.metricValue(false)}>{dash.total_respondents || 0}</div>
              <div style={S.metricSub(false)}>{analytics?.total_responses || 0} total responses</div>
            </div>
            <div style={S.metricCard}>
              <div style={S.metricLabel}>Media Outlets</div>
              <div style={S.metricValue(false)}>{dash.total_outlets || 0}</div>
              <div style={S.metricSub(false)}>Total outlets tracked</div>
            </div>
          </div>

          {/* Row 1 */}
          <div style={S.grid2}>
            <TopRankings outlets={filtered} />
            <DimensionBars dimensions={dimensions} />
          </div>

          {/* Row 2 */}
          <div style={S.grid2}>
            {analytics && <PlatformBars platforms={analytics.platforms} />}
            {analytics && <RegionBars trustByRegion={analytics.trust_by_region} />}
            {analytics && <PoliticalBias politicalAlignment={analytics.political_alignment} />}
            {analytics && <Demographics demographics={analytics.demographics} />}
            {analytics && <PartisanshipDetail analytics={analytics} />}
            <SparklineTrend total={dash.total_responses || 0} />
          </div>

          {/* Table */}
          <OutletsTable outlets={filtered} />

        </div>
      </div>
  );
}