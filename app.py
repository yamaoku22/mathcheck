import os, re, time
import numpy as np
import sympy as sp
import plotly.graph_objects as go
import streamlit as st
from daytona import Daytona, DaytonaConfig

st.set_page_config(page_title="MathCheck", page_icon="✅", layout="wide")

# ───────────────────────── デザイン ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap');
.stApp{
  background:
    radial-gradient(900px 500px at 0% -10%, rgba(99,102,241,.35), transparent 60%),
    radial-gradient(800px 500px at 110% 0%, rgba(6,182,212,.30), transparent 55%),
    linear-gradient(rgba(148,163,184,.06) 1px, transparent 1px) 0 0/40px 40px,
    linear-gradient(90deg, rgba(148,163,184,.06) 1px, transparent 1px) 0 0/40px 40px,
    #070b16;
  color:#e2e8f0; font-family:'Inter',sans-serif;
}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4,p,li,label,span,[data-testid="stWidgetLabel"] p{color:#e2e8f0}
.hero{padding:18px 0 6px}
.hero .badge{display:inline-flex;align-items:center;gap:8px;padding:5px 14px;border-radius:999px;
  border:1px solid rgba(103,232,249,.35);background:rgba(8,47,73,.45);color:#67e8f9;
  font:600 .78rem 'JetBrains Mono',monospace;letter-spacing:.08em}
.hero .dot{width:8px;height:8px;border-radius:50%;background:#22d3ee;box-shadow:0 0 10px #22d3ee;animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.hero h1{font-size:3.6rem;font-weight:800;margin:.25rem 0 0;line-height:1.05;
  background:linear-gradient(90deg,#67e8f9,#a78bfa,#f472b6,#67e8f9);background-size:300% 100%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:flow 8s linear infinite}
@keyframes flow{to{background-position:300% 0}}
.hero p{color:#94a3b8;font-size:1.1rem;margin:.4rem 0 0}
textarea{background:rgba(15,23,42,.75)!important;color:#e2e8f0!important;border:1px solid #1e293b!important;
  border-radius:14px!important;font-family:'JetBrains Mono',monospace!important}
textarea:focus{border-color:#22d3ee!important;box-shadow:0 0 0 1px #22d3ee,0 0 22px rgba(34,211,238,.25)!important}
[data-testid="stFileUploaderDropzone"]{background:rgba(15,23,42,.6);border:1px dashed #334155;border-radius:14px}
.stButton>button{background:linear-gradient(90deg,#06b6d4,#8b5cf6);color:#fff;border:0;border-radius:14px;
  padding:.7rem 1.6rem;font-weight:800;letter-spacing:.03em;box-shadow:0 0 28px rgba(139,92,246,.45);transition:.2s}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 0 40px rgba(34,211,238,.55);color:#fff}
.term{background:#020617;border:1px solid #1e293b;border-radius:14px;padding:14px 16px;
  font:400 .86rem/1.6 'JetBrains Mono',monospace;color:#94a3b8;box-shadow:inset 0 0 30px rgba(34,211,238,.06)}
.term .ok{color:#4ade80}.term .run{color:#22d3ee}.term .warn{color:#fbbf24}
.term .cursor{display:inline-block;width:8px;height:14px;background:#22d3ee;vertical-align:middle;animation:pulse 1s infinite}
.pipe{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 14px}
.chip{padding:7px 14px;border-radius:999px;font:600 .8rem 'JetBrains Mono',monospace;
  background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.45);color:#86efac}
.verdict{border-radius:16px;padding:16px 20px;margin:6px 0 10px;font-weight:700;font-size:1.05rem}
.verdict.ok{background:linear-gradient(90deg,rgba(34,197,94,.18),rgba(34,197,94,.04));border:1px solid rgba(34,197,94,.5);color:#bbf7d0}
.verdict.ng{background:linear-gradient(90deg,rgba(244,63,94,.18),rgba(244,63,94,.04));border:1px solid rgba(244,63,94,.5);color:#fecdd3}
.stTabs [data-baseweb="tab"]{color:#94a3b8;font-weight:600}
.stTabs [aria-selected="true"]{color:#67e8f9!important}
[data-testid="stMetric"]{background:rgba(15,23,42,.7);border:1px solid #1e293b;border-radius:14px;padding:12px 16px}
[data-testid="stMetricValue"]{color:#67e8f9;font-family:'JetBrains Mono',monospace}
</style>
""", unsafe_allow_html=True)

# ───────────────────────── AI と鍵 ─────────────────────────
def secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name)

NOSANA_URL = secret("NOSANA_URL")      # 設定すればNosana上のAIを使う
NOSANA_MODEL = secret("NOSANA_MODEL")
GEMINI_MODEL = "gemini-3.5-flash-lite"

def ask_llm(messages):
    if NOSANA_URL:
        from openai import OpenAI
        client = OpenAI(base_url=NOSANA_URL, api_key="nosana")
        r = client.chat.completions.create(model=NOSANA_MODEL, messages=messages)
        return r.choices[0].message.content, "Nosana"
    from google import genai
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    prompt = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    r = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return r.text, "Gemini"

def extract_code(text):
    m = re.search(r"```python\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else ""

SYSTEM = """あなたは高校数学・物理の講師です。次の形式で答えてください。
1. わかりやすい解説。最後の行は「最終答え: ...」
2. 解説のあとに、次の2行を必ず書く（グラフにできない問題なら FUNC: NONE）
FUNC: 問題の関数を x の式で書く。係数は a, b, c などの文字に一般化する。べき乗は **、掛け算の * は省略しない
PARAMS: 各文字のこの問題での値（例: a=1, b=-4, c=3）
3. 答えを検算するPythonコードを ```python ``` で1つだけ。
   最後に print("ANSWER:", 答え) すること。sympyが無ければ標準ライブラリで書くこと。"""

# ───────────────────────── 安全な数式パース ─────────────────────────
X = sp.Symbol("x")
ALLOWED = {"x", "sin", "cos", "tan", "exp", "log", "sqrt", "pi", "E", "abs"} | set("abcdkmnpqrst")

def safe_expr(s):
    s = (s or "").replace("^", "**").strip()
    if not s or s.upper() == "NONE" or not re.fullmatch(r"[0-9A-Za-z_+\-*/().\s]*", s):
        return None
    if any(n not in ALLOWED for n in re.findall(r"[A-Za-z_]+", s)):
        return None
    try:
        return sp.sympify(s, locals={"abs": sp.Abs})
    except Exception:
        return None

def parse_meta(reply):
    fm = re.search(r"^\s*FUNC:\s*(.+)$", reply, re.M)
    pm = re.search(r"^\s*PARAMS:\s*(.+)$", reply, re.M)
    params = {k: float(v) for k, v in re.findall(r"([a-z])\s*=\s*(-?\d+(?:\.\d+)?)", pm.group(1))} if pm else {}
    return (fm.group(1).strip() if fm else None), params

# ───────────────────────── ターミナル風ログ ─────────────────────────
def terminal(box, lines, running=True):
    body = "<br>".join(lines) + (" <span class='cursor'></span>" if running else "")
    box.markdown(f"<div class='term'>{body}</div>", unsafe_allow_html=True)

# ───────────────────────── 画面：入力 ─────────────────────────
st.markdown("""<div class='hero'>
<span class='badge'><span class='dot'></span>LIVE · DAYTONA SANDBOX VERIFIED</span>
<h1>MathCheck</h1>
<p>AIの解説を、実際に計算して証明する。&nbsp;/&nbsp; AI math explanations, proven by real code execution.</p>
</div>""", unsafe_allow_html=True)

left, right = st.columns([3, 2], gap="large")
with left:
    q = st.text_area("問題 / Problem", "y = x^2 - 4x + 3 のグラフと頂点を求めよ", height=110)
    student = st.text_area("あなたの答え・途中式（任意） / Your working (optional)",
                           placeholder="例:\ny = (x - 2)^2 - 4 + 3\n= (x - 2)^2 + 1\n頂点 (2, 1)", height=120)
with right:
    lang = st.radio("Language / 言語", ["日本語", "English"], horizontal=True)
    photo = st.file_uploader("📷 問題の写真 / Photo (optional)", type=["png", "jpg", "jpeg"])
    go_btn = st.button("⚡ 解説＋検算する / Explain & Verify", width="stretch")

# ───────────────────────── 処理 ─────────────────────────
if go_btn:
    log_box = st.empty()
    log = []
    def step(msg, cls="run"):
        log.append(f"<span class='{cls}'>›</span> {msg}")
        terminal(log_box, log)

    if photo:
        from google import genai
        from google.genai import types
        step("vision: reading problem from photo ...")
        vision = genai.Client(api_key=secret("GEMINI_API_KEY"))
        r = vision.models.generate_content(model=GEMINI_MODEL, contents=[
            types.Part.from_bytes(data=photo.getvalue(), mime_type=photo.type),
            "この画像の数学の問題文を、そのまま文字で書き起こしてください。問題文だけを出力してください。"])
        q = r.text.strip()
        step(f"vision: <span class='ok'>OK</span> → {q[:60]}", "ok")

    messages = [{"role": "system", "content": SYSTEM + f"\n解説は必ず{lang}で書くこと。"},
                {"role": "user", "content": q}]
    step("llm: generating explanation + verification code ...")
    reply, engine = ask_llm(messages)
    func_str, params = parse_meta(reply)
    explanation = re.sub(r"```python.*?```", "", reply, flags=re.S)
    explanation = re.sub(r"^\s*(FUNC|PARAMS):.*$", "", explanation, flags=re.M).strip()
    step(f"llm: <span class='ok'>OK</span> ({engine})", "ok")

    step("daytona: creating isolated sandbox ...")
    t0 = time.time()
    daytona = Daytona(DaytonaConfig(api_key=secret("DAYTONA_API_KEY")))
    sandbox = daytona.create()
    codes = []
    try:
        step(f"daytona: <span class='ok'>sandbox ready</span> ({time.time() - t0:.1f}s) · id={sandbox.id[:8]}", "ok")
        step("daytona: pip install sympy numpy ...")
        sandbox.process.exec("pip install -q sympy numpy")
        for attempt in range(1, 4):
            code = extract_code(reply)
            codes.append(code)
            step(f"daytona: executing verification code (attempt {attempt}) ...")
            res = sandbox.process.code_run(code)
            if res.exit_code == 0:
                step(f"daytona: <span class='ok'>exit 0</span> → {res.result.strip()[:70]}", "ok")
                break
            step(f"daytona: <span class='warn'>exit {res.exit_code}</span> → llm self-correcting ...", "warn")
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": f"このエラーが出ました。修正したコードを ```python ``` で1つだけ:\n{res.result}"}]
            reply, _ = ask_llm(messages)
    finally:
        sandbox.delete()
        step("daytona: sandbox destroyed", "ok")

    step("judge: comparing explanation vs computed result ...")
    verdict, _ = ask_llm([{"role": "user", "content":
        f"解説:\n{explanation}\n\n検算プログラムの出力:\n{res.result}\n\n"
        "解説の最終答えと検算結果は一致していますか？1行目に「一致」か「不一致」とだけ書き、"
        f"不一致なら2行目以降に正しい答えと短い説明を{lang}で書いてください。"}])
    grade = None
    if student.strip():
        step("grader: locating the wrong step in your working ...")
        grade, _ = ask_llm([{"role": "user", "content":
            f"問題:\n{q}\n\n実際に計算した正しい結果:\n{res.result}\n\n生徒の答え・途中式:\n{student}\n\n"
            "生徒の答えを採点してください。1行目に「正解」か「不正解」とだけ書き、"
            f"不正解なら、何行目のどのステップで間違えたかと正しい考え方を{lang}で短く説明してください。"}])
    step("<span class='ok'>DONE ✓</span>", "ok")
    terminal(log_box, log, running=False)

    st.session_state["result"] = dict(
        run=time.time(), q=q, engine=engine, explanation=explanation, codes=codes,
        output=res.result, exit_code=res.exit_code, verdict=verdict, grade=grade,
        func=func_str, params=params, log=log)

# ───────────────────────── 画面：結果 ─────────────────────────
R = st.session_state.get("result")
if R:
    if not go_btn:
        terminal(st, R["log"], running=False)
    st.markdown("<div class='pipe'><span class='chip'>① AI EXPLAIN ✓</span>"
                "<span class='chip'>② DAYTONA EXECUTE ✓</span><span class='chip'>③ VERIFY ✓</span></div>",
                unsafe_allow_html=True)
    if R["verdict"].strip().startswith("一致"):
        st.markdown("<div class='verdict ok'>✅ VERIFIED — 解説の答えは実際の計算結果と一致しました</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='verdict ng'>⚠️ MISMATCH — 解説の答えが計算結果と一致しません</div>", unsafe_allow_html=True)
        st.markdown(R["verdict"])

    tabs = st.tabs(["📈 インタラクティブグラフ", "📘 解説", "🧪 Daytona検算", "📝 採点"])

    with tabs[0]:
        expr = safe_expr(R["func"])
        if expr is None:
            st.info("この問題はグラフにできませんでした。/ No plottable function for this problem.")
        else:
            syms = sorted([s for s in expr.free_symbols if s != X], key=str)
            vals = {}
            if syms:
                st.caption("🎛️ 係数を動かして、グラフがどう変わるか確かめよう / Drag the coefficients")
                cols = st.columns(len(syms))
                for i, s in enumerate(syms):
                    v0 = R["params"].get(str(s), 1.0)
                    span = max(5.0, abs(v0) * 2)
                    vals[s] = cols[i].slider(str(s), float(v0 - span), float(v0 + span), float(v0), 0.1,
                                             key=f"p_{s}_{R['run']}")
            f = sp.simplify(expr.subs(vals))
            x0 = st.slider("🎯 x に代入する値 / substitute x =", -10.0, 10.0, 0.0, 0.1, key=f"x0_{R['run']}")

            fx = sp.lambdify(X, f, "numpy")
            dfx = sp.lambdify(X, sp.diff(f, X), "numpy")
            xs = np.linspace(-10, 10, 801)
            with np.errstate(all="ignore"):
                ys = np.asarray(fx(xs), dtype=complex) * np.ones_like(xs)
                ys = np.where(np.abs(ys.imag) < 1e-9, ys.real, np.nan).astype(float)
                y0 = complex(fx(x0)); slope = complex(dfx(x0))
            y0 = y0.real if abs(y0.imag) < 1e-9 else float("nan")
            slope = slope.real if abs(slope.imag) < 1e-9 else float("nan")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="f(x)",
                                     line=dict(color="#22d3ee", width=3)))
            if np.isfinite(y0) and np.isfinite(slope):
                fig.add_trace(go.Scatter(x=xs, y=y0 + slope * (xs - x0), mode="lines", name="接線 / tangent",
                                         line=dict(color="#a78bfa", width=1.5, dash="dash")))
                fig.add_trace(go.Scatter(x=[x0], y=[y0], mode="markers", name=f"x = {x0}",
                                         marker=dict(size=14, color="#f472b6", line=dict(color="#fff", width=2))))
            special = []
            if f.is_polynomial(X) and sp.degree(f, X) >= 1:
                for label, poly, color in [("解 / root", f, "#4ade80"), ("頂点・極値 / extremum", sp.diff(f, X), "#fbbf24")]:
                    if sp.degree(poly, X) >= 1:
                        for r in sp.Poly(poly, X).nroots():
                            if abs(sp.im(r)) < 1e-9 and -10 <= float(sp.re(r)) <= 10:
                                rx = float(sp.re(r)); ry = float(f.subs(X, rx))
                                special.append((label, rx, ry))
                                fig.add_trace(go.Scatter(x=[rx], y=[ry], mode="markers", name=label, showlegend=False,
                                                         marker=dict(size=10, color=color, symbol="diamond")))
            finite = ys[np.isfinite(ys)]
            if finite.size:
                lo, hi = np.percentile(finite, [2, 98]); pad = (hi - lo) * 0.15 + 1
                fig.update_yaxes(range=[lo - pad, hi + pad])
            fig.update_layout(template="plotly_dark", height=460, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(2,6,23,.6)",
                              legend=dict(orientation="h", y=1.02, x=0))
            fig.update_xaxes(zeroline=True, zerolinecolor="#475569", gridcolor="#1e293b")
            fig.update_yaxes(zeroline=True, zerolinecolor="#475569", gridcolor="#1e293b")

            g1, g2 = st.columns([3, 1])
            with g1:
                st.plotly_chart(fig, width="stretch")
            with g2:
                st.latex("f(x) = " + sp.latex(f))
                st.metric(f"f({x0})", f"{y0:.4g}" if np.isfinite(y0) else "—")
                st.metric(f"傾き f'({x0}) / slope", f"{slope:.4g}" if np.isfinite(slope) else "—")
                for label, rx, ry in special:
                    st.caption(f"◆ {label}: ({rx:.3g}, {ry:.3g})")

    with tabs[1]:
        st.markdown(R["explanation"])
        st.caption(f"AI engine: {R['engine']}")

    with tabs[2]:
        st.caption("このコードは Daytona の隔離サンドボックスで実際に実行されました / Executed in an isolated Daytona sandbox")
        for i, c in enumerate(R["codes"], 1):
            with st.expander(f"attempt {i}", expanded=(i == len(R["codes"]))):
                st.code(c, "python")
        st.markdown("**Output**")
        st.code(R["output"])

    with tabs[3]:
        if R["grade"] is None:
            st.info("途中式を入力すると、どのステップで間違えたかを採点します。/ Paste your working to get graded.")
        elif R["grade"].strip().startswith("正解"):
            st.success(R["grade"])
        else:
            st.error(R["grade"])
