// Stage 4: the same support bot, with the model running in the visitor's browser.
// Same system prompt + FAQ as the Lambda version (faq.md), same history limit.
import { CreateMLCEngine } from "https://esm.run/@mlc-ai/web-llm@0.2.89";

const MODEL_OVERRIDE = new URLSearchParams(location.search).get("model"); // for testing
// Llama 3.2 1B: ~705 MB download, ~879 MB VRAM, 4K context
const FALLBACK_URL = "";   // your Stage 1 Lambda function URL; "" = no fallback
const MAX_MESSAGES = 7;    // same trimming rule as the server version
const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);
const report = (stage, detail = "") => {   // used by the automated smoke test only
  if (params.has("autotest"))
    fetch("/log", { method: "POST", body: JSON.stringify({ stage, detail, t: performance.now() | 0 }) });
};

const system = await (await fetch("./faq.md")).text();
const history = [];
let ask;

function trim(msgs) {
  let t = msgs.slice(-MAX_MESSAGES);
  while (t.length && t[0].role !== "user") t = t.slice(1);
  return t;
}

async function startLocal() {
  const adapter = await navigator.gpu?.requestAdapter();
  if (!adapter) throw new Error("no WebGPU adapter");
  const i = adapter.info ?? {};
  report("adapter", `${i.vendor} ${i.architecture} ${i.description} shader-f16=${adapter.features.has("shader-f16")}`);
  // The default q4f16 builds need shader-f16; older GPUs need the q4f32 build.
  const model = MODEL_OVERRIDE ?? (adapter.features.has("shader-f16")
    ? "Llama-3.2-1B-Instruct-q4f16_1-MLC" : "Llama-3.2-1B-Instruct-q4f32_1-MLC");
  const engine = await CreateMLCEngine(model, {
    initProgressCallback: (p) => { $("status").textContent = p.text; },
  });
  report("model-loaded");
  return async (msgs, onToken) => {
    const stream = await engine.chat.completions.create({
      messages: [{ role: "system", content: system }, ...msgs], stream: true, max_tokens: 400,
    });
    let out = "";
    for await (const c of stream) { out += c.choices[0]?.delta?.content ?? ""; onToken(out); }
    return out;
  };
}

function startRemote() {
  if (!FALLBACK_URL) throw new Error("WebGPU unavailable and no fallback configured");
  return async (msgs, onToken) => {
    const r = await fetch(FALLBACK_URL, { method: "POST",
      body: JSON.stringify({ messages: msgs.map((m) => ({ role: m.role, text: m.content })) }) });
    const { answer } = await r.json(); onToken(answer); return answer;
  };
}

async function start() {
  $("start").disabled = true;
  report("module-loaded", navigator.gpu ? "navigator.gpu present" : "navigator.gpu missing");
  try { ask = await startLocal(); $("status").textContent = "Ready. Answers are generated on this device."; }
  catch (e) {
    report("local-failed", String(e));
    try { ask = startRemote(); $("status").textContent = "Using the server version."; }
    catch (e2) { $("status").textContent = String(e2); report("no-backend", String(e2)); return; }
  }
  $("form").hidden = false;
  if (params.get("autotest")) await send(params.get("autotest"));
}

async function send(text) {
  history.push({ role: "user", content: text });
  $("log").insertAdjacentHTML("beforeend", `<p class="user"></p><p class="bot"></p>`);
  const [u, b] = [...$("log").querySelectorAll("p")].slice(-2);
  u.textContent = text;
  const answer = await ask(trim(history), (s) => { b.textContent = s; });
  history.push({ role: "assistant", content: answer });
  report("answer", answer);
}

$("start").onclick = start;   // load on intent, not on page load
$("form").onsubmit = (e) => { e.preventDefault(); const v = $("input").value; $("input").value = ""; send(v); };
if (params.get("autotest")) start();
