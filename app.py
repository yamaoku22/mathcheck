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
1. わかりやすい解説。最後の行は「最終答え: ...」
2. その答えを検算するPythonコードを ```python ``` で1つだけ。
   最後に print("ANSWER:", 答え) すること。sympyが無ければ標準ライブラリで書くこと。
   グラフで示せる問題なら matplotlib で描き plt.savefig('/home/daytona/plot.png') で保存すること。"""

st.title("✅ MathCheck")
st.caption("AIの数学解説を、Daytonaのサンドボックスで実際に計算して検算します / AI math explanations, verified by real code execution")
lang = st.radio("Language / 言語", ["日本語", "English"], horizontal=True)
q = st.text_area("問題を入力 / Problem", "y = x^2 - 4x + 3 のグラフと頂点を求めよ")
student = st.text_area("あなたの答え・途中式（任意） / Your answer (optional)", placeholder="例: 頂点 (2, 1)")
photo = st.file_uploader("📷 問題の写真（任意） / Photo of the problem (optional)", type=["png", "jpg", "jpeg"])

if st.button("解説＋検算する / Explain & Verify", type="primary"):
    if photo:
        from google import genai
        from google.genai import types
        with st.spinner("写真から問題を読み取り中..."):
            vision = genai.Client(api_key=secret("GEMINI_API_KEY"))
            r = vision.models.generate_content(model="gemini-3.5-flash-lite", contents=[
                types.Part.from_bytes(data=photo.getvalue(), mime_type=photo.type),
                "この画像の数学の問題文を、そのまま文字で書き起こしてください。問題文だけを出力してください。"])
            q = r.text.strip()
        st.info(f"📷 写真から読み取った問題: {q}")
    messages = [{"role": "system", "content": SYSTEM + f"\n解説は必ず{lang}で書くこと。"},
                {"role": "user", "content": q}]
    with st.spinner("AIが解説を作成中..."):
        reply, engine = ask_llm(messages)
    explanation = re.sub(r"```python.*?```", "", reply, flags=re.S).strip()
    st.subheader("📘 AIの解説 / Explanation")
    st.markdown(explanation)
    st.caption(f"AI: {engine}")

    daytona = Daytona(DaytonaConfig(api_key=secret("DAYTONA_API_KEY")))
    with st.spinner("Daytonaのサンドボックスで検算中..."):
        sandbox = daytona.create()
        try:
            sandbox.process.exec("pip install -q matplotlib sympy numpy")
            for attempt in range(1, 4):
                code = extract_code(reply)
                with st.expander(f"🧪 検算コード（{attempt}回目） / Verification code"):
                    st.code(code, "python")
                res = sandbox.process.code_run(code)
                if res.exit_code == 0:
                    break
                st.warning(f"{attempt}回目でエラー → AIが自分でコードを修正中...")
                messages += [{"role": "assistant", "content": reply},
                             {"role": "user", "content": f"このエラーが出ました。修正したコードを ```python ``` で1つだけ:\n{res.result}"}]
                reply, _ = ask_llm(messages)
            try:
                img = sandbox.fs.download_file("/home/daytona/plot.png")
                st.image(img, caption="📈 Daytonaのサンドボックスで実際に計算して描いたグラフ")
            except Exception:
                pass
        finally:
            sandbox.delete()

    st.subheader("🧮 検算結果（実際に計算） / Computed result")
    st.code(res.result)
    judge = [{"role": "user", "content":
        f"解説:\n{explanation}\n\n検算プログラムの出力:\n{res.result}\n\n"
        "解説の最終答えと検算結果は一致していますか？1行目に「一致」か「不一致」とだけ書き、"
        f"不一致なら2行目以降に正しい答えと短い説明を{lang}で書いてください。"}]
    verdict, _ = ask_llm(judge)
    if verdict.strip().startswith("一致"):
        st.success("✅ 検算済み：解説の答えは実際の計算結果と一致しました / Verified by real computation")
    else:
        st.error("⚠️ 解説の答えが計算結果と一致しません / Mismatch detected")
        st.markdown(verdict)

    if student.strip():
        grade, _ = ask_llm([{"role": "user", "content":
            f"問題:\n{q}\n\n実際に計算した正しい結果:\n{res.result}\n\n生徒の答え・途中式:\n{student}\n\n"
            "生徒の答えを採点してください。1行目に「正解」か「不正解」とだけ書き、"
            f"不正解なら、どのステップで間違えたかと正しい考え方を{lang}で短く説明してください。"}])
        st.subheader("📝 あなたの答えの採点 / Grading")
        if grade.strip().startswith("正解"):
            st.success(grade)
        else:
            st.error(grade)