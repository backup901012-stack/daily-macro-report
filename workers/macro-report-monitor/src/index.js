// 宏觀日報監控 Worker
// 功能：記錄發送狀態 + 提供查詢端點（純監控，不觸發發信）
// 發信唯一路徑：數據收集完成 → workflow_run → daily-send.yml

export default {
  // Cron Trigger：僅記錄檢查結果，不觸發任何 dispatch
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(checkStatus(env));
  },

  // HTTP 入口
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/check') {
      const result = await checkStatus(env);
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
      service: '宏觀日報監控（純監控，不觸發發信）',
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
  return day === 0 || day === 6;
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

// 純檢查（不觸發任何動作）— 僅供 cron 和 /check 端點使用
async function checkStatus(env) {
  const today = getTaipeiDate();

  if (isWeekend()) {
    return { date: today, action: 'skip', reason: '週末不發報告' };
  }

  const result = await env.DB.prepare(
    'SELECT COUNT(*) as cnt FROM send_log WHERE report_date = ? AND status = ?'
  ).bind(today, 'success').first();

  const sent = (result?.cnt || 0) > 0;

  if (sent) {
    return { date: today, action: 'none', reason: '今天已發送', count: result.cnt };
  }

  // 僅回報未發送狀態，不自動觸發 dispatch
  return { date: today, action: 'warning', reason: '今天尚未發送，請手動檢查 workflow' };
}
