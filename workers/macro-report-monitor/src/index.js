// 宏觀日報監控 Worker
// 功能：每天 07:45 (台北) 檢查是否已發送報告，沒有則觸發 GitHub Actions 補發

export default {
  // Cron Trigger 入口
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(checkAndAlert(env));
  },

  // HTTP 入口（手動測試用）
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/check') {
      const result = await checkAndAlert(env);
      return new Response(JSON.stringify(result, null, 2), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url.pathname === '/status') {
      const result = await getStatus(env);
      return new Response(JSON.stringify(result, null, 2), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // POST /record — workflow 發完信後呼叫此端點記錄
    if (url.pathname === '/record' && request.method === 'POST') {
      const authKey = request.headers.get('X-API-Key');
      if (authKey !== env.RECORD_KEY) {
        return new Response(JSON.stringify({ error: '未授權' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      const data = await request.json();
      const result = await recordSend(env, data);
      return new Response(JSON.stringify(result, null, 2), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      service: '宏觀日報監控',
      endpoints: ['GET /check', 'GET /status', 'POST /record'],
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
};

// 取得台北時間今天的日期
function getTaipeiDate() {
  const now = new Date();
  const taipei = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  const y = taipei.getFullYear();
  const m = String(taipei.getMonth() + 1).padStart(2, '0');
  const d = String(taipei.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

// 檢查是否為週末（台北時間）
function isWeekend() {
  const now = new Date();
  const taipei = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  const day = taipei.getDay();
  return day === 0 || day === 6; // 週日=0, 週六=6
}

// 查詢今天的發送記錄
async function getStatus(env) {
  const today = getTaipeiDate();

  const result = await env.DB.prepare(
    'SELECT * FROM send_log WHERE report_date = ? ORDER BY sent_at DESC'
  ).bind(today).all();

  return {
    date: today,
    sent: result.results.length > 0,
    count: result.results.length,
    records: result.results,
  };
}

// 記錄發送結果
async function recordSend(env, data) {
  const { date, recipients, pdf_size } = data;
  if (!date || !recipients || !Array.isArray(recipients)) {
    return { error: '缺少必要欄位: date, recipients[]' };
  }

  let recorded = 0;
  for (const r of recipients) {
    try {
      await env.DB.prepare(
        'INSERT OR REPLACE INTO send_log (report_date, recipient, status, sent_at, pdf_size) VALUES (?, ?, ?, datetime("now"), ?)'
      ).bind(date, r, 'success', pdf_size || 0).run();
      recorded++;
    } catch (e) {
      console.error(`記錄失敗 ${r}: ${e.message}`);
    }
  }

  return { date, recorded, total: recipients.length };
}

// 主���查邏輯
async function checkAndAlert(env) {
  const today = getTaipeiDate();

  // 週末不檢查
  if (isWeekend()) {
    return { date: today, action: 'skip', reason: '週末不發報告' };
  }

  // 查 D1 是否有今天的發送記錄
  const result = await env.DB.prepare(
    'SELECT COUNT(*) as cnt FROM send_log WHERE report_date = ? AND status = ?'
  ).bind(today, 'success').first();

  const sent = (result?.cnt || 0) > 0;

  if (sent) {
    return { date: today, action: 'none', reason: '今天已發送', count: result.cnt };
  }

  // 沒有發送記錄 → 觸發 GitHub Actions 補發
  const ghToken = env.GH_TOKEN;
  if (!ghToken) {
    console.error('GH_TOKEN 未設定，無法觸發補發');
    return { date: today, action: 'error', reason: 'GH_TOKEN 未設定' };
  }

  try {
    const resp = await fetch(
      'https://api.github.com/repos/backup901012-stack/daily-macro-report/actions/workflows/daily-send.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${ghToken}`,
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'macro-report-monitor',
        },
        body: JSON.stringify({ ref: 'master' }),
      }
    );

    if (resp.status === 204) {
      // 記錄觸發補發到 D1
      await env.DB.prepare(
        'INSERT INTO send_log (report_date, recipient, status, sent_at, error) VALUES (?, ?, ?, datetime("now"), ?)'
      ).bind(today, 'monitor-trigger', 'triggered', '07:45 未偵測到發送記錄，已觸發補發').run();

      return { date: today, action: 'triggered', reason: '已觸發 GitHub Actions 補發' };
    } else {
      const body = await resp.text();
      return { date: today, action: 'error', reason: `GitHub API 回應 ${resp.status}: ${body.slice(0, 200)}` };
    }
  } catch (err) {
    return { date: today, action: 'error', reason: err.message };
  }
}
