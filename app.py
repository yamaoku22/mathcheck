import os, re
import streamlit as st
from daytona import Daytona, DaytonaConfig

st.set_page_config(page_title="MathCheck", page_icon="✅")

def secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name)

NOSANA_URL = secret("NOSANA_URL")      # 設定すればNosana上のAIを使う
NOSANA_MODEL = secret("NOSANA_MODEL")

def ask_llm(messages):
    if NOSANA_URL:
        from openai import OpenAI
        client = OpenAI(base_url=NOSANA_URL, api_key="nosana")
        r = client.chat.completions.create(model=NOSANA_MODEL, messages=messages)
        return r.choices[0].message.content, "Nosana"
    from google import genai
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    prompt = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    r = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt)
    return r.text, "Gemini"

def extract_code(text):
    m = re.search(r"```python\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else ""

SYSTEM = """あなたは高校数学・物理の講師です。次の形式で答えてください。
1. 日本語のわかりやすい解説。最後の行は「最終答え: ...」
2. その答えを検算するPythonコードを ```python ``` で1つだけ。
   最後に print("ANSWER:", 答え) すること。sympyが無ければ標準ライブラリで書くこと。"""

st.title("✅ MathCheck")
st.caption("AIの数学解説を、Daytonaのサンドボックスで実際に計算して検算します")
q = st.text_area("問題を入力", "x^3 - 6x^2 + 11x - 6 = 0 を解け")

if st.button("解説＋検算する", type="primary"):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
    with st.spinner("AIが解説を作成中..."):
        reply, engine = ask_llm(messages)
    explanation = re.sub(r"```python.*?```", "", reply, flags=re.S).strip()
    st.subheader("📘 AIの解説")
    st.markdown(explanation)
    st.caption(f"AI: {engine}")

    daytona = Daytona(DaytonaConfig(api_key=secret("DAYTONA_API_KEY")))
    with st.spinner("Daytonaのサンドボックスで検算中..."):
        sandbox = daytona.create()
        try:
            for attempt in range(1, 4):
                code = extract_code(reply)
                with st.expander(f"🧪 検算コード（{attempt}回目）"):
                    st.code(code, "python")
                res = sandbox.process.code_run(code)
                if res.exit_code == 0:
                    break
                st.warning(f"{attempt}回目でエラー → AIが自分でコードを修正中...")
                messages += [{"role": "assistant", "content": reply},
                             {"role": "user", "content": f"このエラーが出ました。修正したコードを ```python ``` で1つだけ:\n{res.result}"}]
                reply, _ = ask_llm(messages)
        finally:
            sandbox.delete()

    st.subheader("🧮 検算結果（実際に計算）")
    st.code(res.result)
    judge = [{"role": "user", "content":
        f"解説:\n{explanation}\n\n検算プログラムの出力:\n{res.result}\n\n"
        "解説の最終答えと検算結果は一致していますか？1行目に「一致」か「不一致」とだけ書き、"
        "不一致なら2行目以降に正しい答えと短い説明を書いてください。"}]
    verdict, _ = ask_llm(judge)
    if verdict.strip().startswith("一致"):
        st.success("✅ 検算済み：解説の答えは実際の計算結果と一致しました")
    else:
        st.error("⚠️ 解説の答えが計算結果と一致しません")
        st.markdown(verdict)
