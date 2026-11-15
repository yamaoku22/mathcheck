import os, re, time, html
import numpy as np
import sympy as sp
import plotly.graph_objects as go
import streamlit as st
from daytona import Daytona, DaytonaConfig

st.set_page_config(page_title="MathCheck", page_icon="✅", layout="wide")

# ───────────────────────── デザイン ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{--bg:#0c0d0f;--panel:#141518;--line:#26282d;--text:#e8e6e1;--mute:#8b8d93;--accent:#d4ff3a}
.stApp{background:
  linear-gradient(var(--line) 1px, transparent 1px) 0 0/48px 48px,
  linear-gradient(90deg, var(--line) 1px, transparent 1px) 0 0/48px 48px, var(--bg);
  background-blend-mode:normal;color:var(--text);font-family:'IBM Plex Sans',sans-serif}
.stApp::before{content:"";position:fixed;inset:0;background:radial-gradient(ellipse at center, transparent 40%, var(--bg) 85%);pointer-events:none}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4,p,li,label,span,[data-testid="stWidgetLabel"] p{color:var(--text)}
[data-testid="stWidgetLabel"] p{font:500 .78rem 'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.hero{padding:22px 0 10px;border-bottom:1px solid var(--line);margin-bottom:18px}
.hero .badge{font:500 .75rem 'IBM Plex Mono',monospace;color:var(--mute);letter-spacing:.1em}
.hero .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--accent);margin-right:8px;animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
.hero h1{font:700 3.2rem/1.05 'IBM Plex Sans',sans-serif;letter-spacing:-.02em;margin:.4rem 0 0;color:var(--text)}
.hero h1 b{color:var(--accent)}
.hero p{color:var(--mute);font-size:1rem;margin:.5rem 0 0}
textarea{background:var(--panel)!important;color:var(--text)!important;border:1px solid var(--line)!important;
  border-radius:6px!important;font-family:'IBM Plex Mono',monospace!important}
textarea:focus{border-color:var(--accent)!important;box-shadow:none!important}
[data-testid="stFileUploaderDropzone"]{background:var(--panel);border:1px dashed #3a3d43;border-radius:6px}
[data-testid="stFileUploaderDropzone"] *{color:var(--text)!important}
[data-testid="stFileUploaderDropzone"] small,[data-testid="stFileUploaderDropzone"] span{color:var(--mute)!important}
[data-testid="stFileUploaderDropzone"] button{background:#1d1f23!important;border:1px solid #3a3d43!important;color:var(--text)!important;border-radius:6px}
.stButton>button{background:var(--accent);color:#0c0d0f;border:0;border-radius:6px;padding:.7rem 1.4rem;
  font:700 .9rem 'IBM Plex Mono',monospace;letter-spacing:.04em}
.stButton>button:hover{background:#e6ff7a;color:#0c0d0f}
.stButton>button p{color:#0c0d0f}
.term{background:#08090a;border:1px solid var(--line);border-radius:6px;padding:14px 16px;
  font:400 .84rem/1.65 'IBM Plex Mono',monospace;color:var(--mute)}
.term .ok{color:var(--accent)}.term .run{color:var(--text)}.term .warn{color:#ffb547}
.term .cursor{display:inline-block;width:8px;height:14px;background:var(--accent);vertical-align:middle;animation:pulse 1s infinite}
.pipe{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 12px}
.chip{padding:5px 12px;border:1px solid var(--line);border-radius:4px;font:500 .75rem 'IBM Plex Mono',monospace;color:var(--mute)}
.chip b{color:var(--accent)}
.ans{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0 6px}
.ans .box{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:16px 20px}
.ans .lbl{font:500 .72rem 'IBM Plex Mono',monospace;letter-spacing:.1em;color:var(--mute);text-transform:uppercase}
.ans .val{font:700 1.7rem/1.25 'IBM Plex Mono',monospace;color:var(--text);margin-top:6px;word-break:break-word}
.ans .box.hl{border-color:var(--accent)} .ans .box.hl .val{color:var(--accent)}
.sec{font:500 .75rem 'IBM Plex Mono',monospace;letter-spacing:.1em;color:var(--mute);text-transform:uppercase;margin:18px 0 6px}
.verdict{border-radius:6px;padding:14px 18px;margin:6px 0 10px;font:500 1rem 'IBM Plex Sans',sans-serif;border:1px solid var(--line);background:var(--panel)}
.verdict.ok{border-left:4px solid var(--accent)}
.verdict.ng{border-left:4px solid #ff5a5a}
.stTabs [data-baseweb="tab"]{color:var(--mute);font:500 .85rem 'IBM Plex Mono',monospace}
.stTabs [aria-selected="true"]{color:var(--text)!important}
.stTabs [data-baseweb="tab-highlight"]{background:var(--accent)}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 16px}
[data-testid="stMetricValue"]{color:var(--text);font-family:'IBM Plex Mono',monospace}
@media (max-width:640px){
  .hero h1{font-size:2.3rem}
  .ans{grid-template-columns:1fr}
  .ans .val{font-size:1.35rem}
  .term{font-size:.74rem;padding:10px 12px;overflow-x:auto}
}
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

def nosana_client():
    from openai import OpenAI
    url = NOSANA_URL.rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    return OpenAI(base_url=url, api_key=secret("NOSANA_API_KEY") or "nosana", timeout=240)

@st.cache_resource
def nosana_model():
    return NOSANA_MODEL or nosana_client().models.list().data[0].id

def ask_llm(messages):
    if NOSANA_URL:
        try:  # Nosana の分散GPU上のオープンモデルを優先
            r = nosana_client().chat.completions.create(model=nosana_model(), messages=messages)
            return r.choices[0].message.content, f"Nosana · {nosana_model()}"
        except Exception as e:  # 落ちていても Gemini に自動フォールバック
            st.session_state["nosana_err"] = f"{type(e).__name__}: {str(e)[:120]}"
    from google import genai
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    prompt = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    r = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return r.text, "Gemini"

def extract_code(text):
    m = re.search(r"```python\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else ""

SYSTEM = """あなたは高校数学・物理の講師です。次の形式で答えてください。
1. 解き方の解説。「**Step 1**」「**Step 2**」…と番号を付け、各ステップで何をするかを一言書いてから途中式を省略せずに書く。数式は $...$（独立した式は $$...$$）で書く。最後の行は「最終答え: ...」（ここだけは $ を使わない）
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
<span class='badge'><span class='dot'></span>VERIFIED IN DAYTONA SANDBOXES</span>
<h1>Math<b>Check</b></h1>
<p>AIの解説を、実際に計算して確かめる。 — Every answer is checked by running real code.</p>
</div>""", unsafe_allow_html=True)

left, right = st.columns([3, 2], gap="large")
with left:
    q = st.text_area("問題 / Problem", "y = x^2 - 4x + 3 のグラフと頂点を求めよ", height=110)
    student = st.text_area("あなたの答え・途中式（任意） / Your working (optional)",
                           placeholder="例:\ny = (x - 2)^2 - 4 + 3\n= (x - 2)^2 + 1\n頂点 (2, 1)", height=120)
with right:
    lang = st.radio("Language / 言語", ["日本語", "English"], horizontal=True)
    photo = st.file_uploader("問題の写真 / Photo (optional)", type=["png", "jpg", "jpeg"])
    go_btn = st.button("解説＋検算する  →", width="stretch")

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
    step(f"llm: generating explanation + verification code ... ({'Nosana GPU network' if NOSANA_URL else 'Gemini'})")
    reply, engine = ask_llm(messages)
    func_str, params = parse_meta(reply)
    explanation = re.sub(r"```python.*?```", "", reply, flags=re.S)
    explanation = re.sub(r"^\s*(FUNC|PARAMS):.*$", "", explanation, flags=re.M).strip()
    step(f"llm: <span class='ok'>OK</span> ({engine})", "ok")
    if engine == "Gemini":
        why = "NOSANA_URL not set" if not NOSANA_URL else html.escape(st.session_state.get("nosana_err", "unknown"))
        step(f"nosana: <span class='warn'>fallback to Gemini</span> → {why}", "warn")

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
    st.markdown("<div class='pipe'><span class='chip'><b>01</b> EXPLAIN</span>"
                "<span class='chip'><b>02</b> EXECUTE · DAYTONA</span><span class='chip'><b>03</b> VERIFY</span></div>",
                unsafe_allow_html=True)
    ok = R["verdict"].strip().startswith("一致")
    m1 = re.search(r"(?:最終答え|Final answer)\s*[:：]\s*(.+)", R["explanation"], re.I)
    m2 = re.search(r"ANSWER:\s*(.+)", R["output"] or "")
    ai_ans = m1.group(1).strip() if m1 else "—"
    real_ans = m2.group(1).strip() if m2 else (R["output"] or "—").strip()[:80]
    st.markdown(f"""<div class='ans'>
<div class='box'><div class='lbl'>AIの答え / AI answer</div><div class='val'>{html.escape(ai_ans)}</div></div>
<div class='box hl'><div class='lbl'>Daytonaで計算した答え / Computed</div><div class='val'>{html.escape(real_ans)}</div></div>
</div>""", unsafe_allow_html=True)
    if ok:
        st.markdown("<div class='verdict ok'><b>Verified.</b>&nbsp; 2つの答えが一致しました。この解説は信頼できます。</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='verdict ng'><b>Mismatch.</b>&nbsp; AIの答えが実際の計算と一致しません。右の計算結果が正しい答えです。</div>", unsafe_allow_html=True)
        st.markdown(R["verdict"])

    st.markdown("<div class='sec'>解き方・途中式 / Step-by-step solution</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(R["explanation"])
        st.caption(f"AI engine: {R['engine']}")

    tabs = st.tabs(["グラフ / Graph", "採点 / Grading", "検算コード / Code"])

    with tabs[0]:
        expr = safe_expr(R["func"])
        if expr is None:
            st.info("この問題はグラフにできませんでした。/ No plottable function for this problem.")
        else:
            syms = sorted([s for s in expr.free_symbols if s != X], key=str)
            vals = {}
            if syms:
                st.caption("係数を動かして、グラフの変化を確かめる / Drag the coefficients")
                cols = st.columns(len(syms))
                for i, s in enumerate(syms):
                    v0 = R["params"].get(str(s), 1.0)
                    span = max(5.0, abs(v0) * 2)
                    vals[s] = cols[i].slider(str(s), float(v0 - span), float(v0 + span), float(v0), 0.1,
                                             key=f"p_{s}_{R['run']}")
            f = sp.simplify(expr.subs(vals))
            x0 = st.slider("x に代入する値 / substitute x", -10.0, 10.0, 0.0, 0.1, key=f"x0_{R['run']}")

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
                                     line=dict(color="#d4ff3a", width=2.5)))
            if np.isfinite(y0) and np.isfinite(slope):
                fig.add_trace(go.Scatter(x=xs, y=y0 + slope * (xs - x0), mode="lines", name="接線 / tangent",
                                         line=dict(color="#8b8d93", width=1.2, dash="dash")))
                fig.add_trace(go.Scatter(x=[x0], y=[y0], mode="markers", name=f"x = {x0}",
                                         marker=dict(size=12, color="#0c0d0f", line=dict(color="#d4ff3a", width=2.5))))
            special = []
            if f.is_polynomial(X) and sp.degree(f, X) >= 1:
                for label, poly, color in [("解 / root", f, "#e8e6e1"), ("頂点・極値 / extremum", sp.diff(f, X), "#ffb547")]:
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
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#101114",
                              legend=dict(orientation="h", y=1.02, x=0))
            fig.update_xaxes(zeroline=True, zerolinecolor="#4a4d53", gridcolor="#1c1e22")
            fig.update_yaxes(zeroline=True, zerolinecolor="#4a4d53", gridcolor="#1c1e22")

            g1, g2 = st.columns([3, 1])
            with g1:
                st.plotly_chart(fig, width="stretch")
            with g2:
                st.latex("f(x) = " + sp.latex(f))
                st.metric(f"f({x0})", f"{y0:.4g}" if np.isfinite(y0) else "—")
                st.metric(f"傾き f'({x0}) / slope", f"{slope:.4g}" if np.isfinite(slope) else "—")
                for label, rx, ry in special:
                    st.caption(f"{label}: ({rx:.3g}, {ry:.3g})")

    with tabs[2]:
        st.caption("このコードは Daytona の隔離サンドボックスで実際に実行されました / Executed in an isolated Daytona sandbox")
        for i, c in enumerate(R["codes"], 1):
            with st.expander(f"attempt {i}", expanded=(i == len(R["codes"]))):
                st.code(c, "python")
        st.markdown("**Output**")
        st.code(R["output"])

    with tabs[1]:
        if R["grade"] is None:
            st.info("途中式を入力すると、どのステップで間違えたかを採点します。/ Paste your working to get graded.")
        elif R["grade"].strip().startswith("正解"):
            st.success(R["grade"])
        else:
            st.error(R["grade"])
