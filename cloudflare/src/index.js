/** Private owner-only Telegram command receiver. Informational/read-only: no buy commands. */
import { neon } from '@neondatabase/serverless';

const HELP = [
  'MemeCoin AI Radar Pro — RESEARCH ONLY',
  'All opportunities are blocked until every mandatory security check is verified.',
  '/status — latest scan',
  '/top — last 5 preselected research candidates (NOT buy signals)',
  '/analyze MINT — last saved on-chain diagnostics',
  '/history MINT — observation history (not performance guarantee)',
  '/watchlist — show tracked mints',
  '/add MINT and /remove MINT — edit watchlist',
  '/scan — queue an on-demand request for next scheduled runner',
  '/help — commands'
].join('\n');
const MINT = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const safe = v => String(v ?? '').replace(/[<>]/g, '');

async function send(env, chatId, text) {
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  const response = await fetch(url, {method:'POST',headers:{'content-type':'application/json'},
    body:JSON.stringify({chat_id:chatId,text:text.slice(0,3800),disable_web_page_preview:true})});
  if (!response.ok) throw new Error('Telegram delivery failure');
}

async function handleCommand(env, msg) {
  const chatId = String(msg?.chat?.id ?? '');
  const userId = String(msg?.from?.id ?? '');
  if (userId !== String(env.TELEGRAM_OWNER_ID) || msg?.chat?.type !== 'private') return;
  if (!env.DATABASE_URL) { await send(env,chatId,'Database not configured.'); return; }
  const sql = neon(env.DATABASE_URL);
  const pieces = String(msg.text || '').trim().split(/\s+/);
  const command = pieces[0].toLowerCase().split('@')[0];
  const mint = pieces[1] || '';
  try {
    if (command === '/start' || command === '/help') {
      await send(env,chatId,HELP); return;
    }
    if (command === '/status') {
      const data=await sql`SELECT finished_at,scanned,preselected,selected,status FROM scan_runs ORDER BY finished_at DESC LIMIT 1`;
      if (!data.length){ await send(env,chatId,'No saved scans yet.'); return; }
      const r=data[0];
      await send(env,chatId,`Latest scan: ${safe(r.finished_at)}\nTokens seen: ${r.scanned}\nPreselected: ${r.preselected}\nInspected: ${r.selected}\nStatus: ${safe(r.status)}\nSignals: DISABLED (Security checks incomplete)`);return;
    }
    if (command === '/top') {
      const data=await sql`SELECT mint,scanner,liquidity_usd,security_decision,observed_at FROM observations ORDER BY observed_at DESC LIMIT 5`;
      if(!data.length){await send(env,chatId,'No saved candidates.');return;}
      await send(env,chatId,'Recent candidates — NOT BUY SIGNALS:\n'+data.map(r=>`${safe(r.mint)}\n${safe(r.scanner)} / Liquidity $${safe(r.liquidity_usd)} / ${safe(r.security_decision)}`).join('\n\n'));return;
    }
    if (command === '/analyze') {
      if (!MINT.test(mint)){await send(env,chatId,'Usage: /analyze VALID_SOLANA_MINT');return;}
      const data=await sql`SELECT security_decision,discovery_status,security_unknown_count,pool_status,raw_data,observed_at FROM observations WHERE mint=${mint} ORDER BY observed_at DESC LIMIT 1`;
      if(!data.length){await send(env,chatId,'Not analyzed yet; try /scan or wait for the next cycle.');return;}
      const r=data[0];
      const check=r.raw_data?.security_contract_checks || {};
      await send(env,chatId,`Token: ${mint}\nLast observed: ${safe(r.observed_at)}\nDiscovery: ${safe(r.discovery_status)}\nSecurity: ${safe(r.security_decision)}\nMissing mandatory checks: ${r.security_unknown_count}\nPool: ${safe(r.pool_status)}\nContract: ${safe(JSON.stringify(check))}\nResearch only. No security clearance.`);return;
    }
    if (command === '/history') {
      if (!MINT.test(mint)){await send(env,chatId,'Usage: /history VALID_SOLANA_MINT');return;}
      const data=await sql`SELECT observed_at,discovery_status,security_decision,liquidity_usd FROM observations WHERE mint=${mint} ORDER BY observed_at DESC LIMIT 5`;
      await send(env,chatId,data.length?'Recent observations (not opportunity signals):\n'+data.map(r=>`${safe(r.observed_at)} / Liquidity $${safe(r.liquidity_usd)} / ${safe(r.security_decision)}`).join('\n'):'No history for this mint.');return;
    }
    if (command === '/watchlist') {
      const data=await sql`SELECT mint FROM watchlist ORDER BY added_at DESC LIMIT 30`;
      await send(env,chatId,data.length?'Tracked tokens:\n'+data.map(x=>x.mint).join('\n'):'Watchlist empty.');return;
    }
    if (command === '/add' || command === '/remove') {
      if(!MINT.test(mint)){await send(env,chatId,'A valid Solana mint is required.');return;}
      if(command==='/add') await sql`INSERT INTO watchlist(mint) VALUES (${mint}) ON CONFLICT (mint) DO NOTHING`;
      else await sql`DELETE FROM watchlist WHERE mint=${mint}`;
      await send(env,chatId,command==='/add'?'Added to watchlist (not marked safe).':'Removed from watchlist.');return;
    }
    if(command==='/scan') {
      // Deduplicate frequent requests server-side without launching arbitrary workflows or granting GitHub write access.
      const recent=await sql`SELECT id FROM pending_jobs WHERE kind='scan' AND requested_by=${userId} AND created_at > NOW() - INTERVAL '3 minutes' AND status IN ('queued','processing') LIMIT 1`;
      if(recent.length){await send(env,chatId,'Scan request already queued.');return;}
      const id=crypto.randomUUID();
      await sql`INSERT INTO pending_jobs(id,requested_by,kind,status) VALUES(${id},${userId},'scan','queued')`;
      await send(env,chatId,'Request queued. A scheduled GitHub run must be configured to process it. No immediate scan is guaranteed.');return;
    }
    await send(env,chatId,HELP);
  } catch (_error) {
    // Never echo database or provider error objects (could contain secrets).
    await send(env,chatId,'Operation unavailable. No safety PASS inferred.');
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method==='GET' && url.pathname==='/health') return new Response('ok');
    if (request.method !== 'POST' || url.pathname !== '/webhook') return new Response('not found',{status:404});
    if (!env.TELEGRAM_WEBHOOK_SECRET || !env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_OWNER_ID) return new Response('unconfigured',{status:503});
    if (request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.TELEGRAM_WEBHOOK_SECRET) return new Response('unauthorized',{status:403});
    if ((Number(request.headers.get('content-length') || 0)) > 120000) return new Response('too large',{status:413});
    let update;
    try { update = await request.json(); } catch {return new Response('bad request',{status:400});}
    // Process within Worker lifetime. A stable webhook handles private commands quickly.
    ctx.waitUntil(handleCommand(env, update?.message));
    return new Response('ok');
  }
};
