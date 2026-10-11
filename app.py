import html
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from demo import DEMO_AUDIENCE, DEMO_FOCUS, DEMO_REVISION, DEMO_SUBJECT, sample_outline, sample_run
from models import Topic
from pipeline import ModelConfig, ResearchError, deepen, export_markdown, research
from progress_ui import run_with_progress
from storage import Library

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="题见 · 选题工作台", page_icon=":material/lightbulb:", layout="wide", initial_sidebar_state="auto")
st.markdown("""<style>
:root {font-synthesis:none;}
html, body, [class*="st-"] {letter-spacing:0;}
html, body, p, h1, h2, h3, label, input, textarea, button {font-family:"Segoe UI","Microsoft YaHei",sans-serif!important;}
.stMainBlockContainer {max-width:1480px; padding:4rem 2.4rem 3rem;}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {display:none;}
[data-testid="stSidebar"] {border-right:1px solid #e3e8eb;}
[data-testid="stSidebar"] > div:first-child {padding-top:1.1rem;}
h1 {font-size:30px!important; line-height:1.35!important; font-weight:700!important;}
h2 {font-size:23px!important; line-height:1.45!important;}
h3 {font-size:19px!important; line-height:1.55!important;}
p, li {line-height:1.75; overflow-wrap:anywhere;}
button {border-radius:6px!important;}
button p {line-height:1.45!important;}
[data-testid="stMetricValue"] {font-size:26px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:8px!important; box-shadow:none!important;}
.brand {display:flex;align-items:center;gap:10px;font-size:23px;font-weight:750;margin-bottom:4px;}
.brand-mark {display:grid;place-items:center;background:#087f75;color:white;width:34px;height:34px;border-radius:6px;font-size:21px;}
.brand-sub {font-size:12px;color:#66777d;margin:0 0 20px 44px;}
.eyebrow {font-size:11px;font-weight:700;color:#087f75;margin-bottom:8px;}
.muted {font-size:13px;color:#697b81;}
.topic-meta {font-size:12px;color:#536e79;margin:0 0 8px;}
.section-label {font-size:12px;font-weight:600;color:#687a81;margin:18px 0 6px;}
.rule {border-top:1px solid #e6ebed;margin:16px 0;}
.status-dot {display:inline-block;width:7px;height:7px;background:#087f75;border-radius:50%;margin-right:7px;}
[data-testid="stAlert"] {border-radius:6px;}
@media(max-width:768px){
 .stMainBlockContainer{padding:3.5rem 1rem 2rem;}h1{font-size:25px!important;}
 [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]){display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}
 [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"]{width:100%!important;min-width:0!important;}
}
</style>""", unsafe_allow_html=True)


def safe(text: str) -> str:
    return html.escape(text)


@st.cache_resource
def library():
    return Library(Path(os.getenv("TOPIC_STUDIO_DATA_DIR", str(ROOT / ".local"))) / "library.sqlite3")


db = library()
if "run" not in st.session_state or (
    st.session_state.run.mode == "demo"
    and st.session_state.get("demo_revision") != DEMO_REVISION
):
    st.session_state.run = sample_run()
    st.session_state.selected_topic = st.session_state.run.topics[0].id
    st.session_state.outlines = {}
st.session_state.demo_revision = DEMO_REVISION


def source_list(sources, source_ids=None):
    for source in sources:
        if source_ids is not None and source.id not in source_ids:
            continue
        with st.expander(f"{source.id} · {source.title}"):
            st.caption(source.basis)
            st.write(source.excerpt[:1400])
            st.link_button("打开原始来源", source.url, icon=":material/open_in_new:")


with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">题</span>题见</div><div class="brand-sub">TOPIC RESEARCH STUDIO</div>', unsafe_allow_html=True)
    page = st.radio("导航", ["选题工作台", "收藏夹", "研究记录"], label_visibility="collapsed")
    st.divider()
    mode = st.segmented_control("运行模式", ["样例演示", "联网研究"], default="样例演示", selection_mode="single", required=True)
    demo_mode = mode == "样例演示"
    subject = st.text_input("关注领域", DEMO_SUBJECT, max_chars=100, disabled=demo_mode)
    audience = st.text_input("目标读者", DEMO_AUDIENCE, max_chars=120, disabled=demo_mode)
    focus = st.text_area("研究方向", DEMO_FOCUS, height=90, max_chars=300, disabled=demo_mode)
    period = st.selectbox("搜索时间范围", ["不限时间", "近一个月"], disabled=demo_mode)
    generate = st.button("载入样例" if demo_mode else "生成选题", type="primary", icon=":material/auto_awesome:", width="stretch")
    with st.expander("模型连接", icon=":material/settings:"):
        provider = st.selectbox("服务", ["Gemini", "OpenAI 兼容", "DeepSeek"])
        if provider == "Gemini":
            env_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
            default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        elif provider == "DeepSeek":
            env_key = os.getenv("DEEPSEEK_API_KEY", "")
            default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            env_key = os.getenv("OPENAI_API_KEY", "")
            default_model = os.getenv("OPENAI_MODEL", "")
        key_input = st.text_input("API Key", type="password", key=f"key_{provider}", placeholder="本地环境已配置" if env_key else "未配置")
        model = st.text_input("模型", value=default_model, key=f"model_{provider}")
        if provider == "DeepSeek":
            endpoint = st.text_input("API 地址", value=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), key="endpoint_DeepSeek")
        else:
            endpoint = st.text_input("API 地址", value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")) if provider != "Gemini" else ""
        st.caption("密钥仅用于当前会话或本地 .env，不写入研究记录。")
    st.divider()
    st.markdown('<span class="status-dot"></span><span class="muted">本地工作区 · 独立原型</span>', unsafe_allow_html=True)

config = ModelConfig(provider, model, key_input or env_key, endpoint)

if generate:
    if not subject.strip() or not audience.strip():
        st.error("请填写关注领域和目标读者。")
    elif not demo_mode and (not config.api_key or not config.model.strip()):
        st.error("联网研究需要模型 API Key 和模型名称。请展开左侧“模型连接”完成配置；原有结果已保留。")
    else:
        try:
            if demo_mode:
                new_run = sample_run()
            else:
                new_run = run_with_progress(
                    lambda progress: research(subject.strip(), audience.strip(), focus.strip(), period, config, progress)
                )
            db.add_run(new_run)
            st.session_state.run = new_run
            st.session_state.selected_topic = new_run.topics[0].id
            st.session_state.outlines = {}
            st.toast("研究结果已更新", icon=":material/check_circle:")
        except ResearchError as exc:
            st.error(str(exc))
        except Exception:
            st.error("本次研究未完成，已有结果已保留。请检查网络、模型配置和本地存储后重试。")

run = st.session_state.run
saved_ids = {entry["topic"]["id"] for entry in db.saved()}
verdicts = db.verdicts()

if page == "收藏夹":
    st.markdown('<div class="eyebrow">LIBRARY</div>', unsafe_allow_html=True)
    st.title("收藏夹")
    saved = db.saved()
    st.caption(f"已收藏 {len(saved)} 个选题")
    if not saved:
        st.info("还没有收藏的选题。")
    for entry in saved:
        topic = Topic.model_validate(entry["topic"])
        with st.container(border=True):
            st.caption(f"{topic.angle} · {'样例' if entry['mode'] == 'demo' else '联网研究'}")
            st.subheader(topic.title)
            st.write(topic.why)
            st.caption(f"证据边界：{topic.caveat}")
            for source in entry["sources"]:
                st.link_button(f"{source['id']} · {source['title']}", source["url"], icon=":material/open_in_new:")
            if st.button("移除收藏", key=f"remove_{topic.id}", icon=":material/bookmark_remove:"):
                db.remove(topic.id)
                st.rerun()
    st.stop()

if page == "研究记录":
    st.markdown('<div class="eyebrow">RESEARCH HISTORY</div>', unsafe_allow_html=True)
    st.title("研究记录")
    history = db.runs()
    if not history:
        st.info("尚无研究记录。")
    for item in history:
        with st.container(border=True):
            st.subheader(item.subject)
            st.caption(f"{item.created_at.replace('T', ' ')} · {'样例演示' if item.mode == 'demo' else '联网研究'} · {len(item.topics)} 个选题")
            st.write(f"目标读者：{item.audience}")
            if st.button("载入研究", key=f"history_{item.id}", icon=":material/restore:"):
                st.session_state.run = item
                st.session_state.selected_topic = item.topics[0].id
                st.session_state.outlines = {}
                st.success("已载入。切换到“选题工作台”查看。")
            st.download_button("导出 Markdown", export_markdown(item), file_name=f"research-{item.id[:8]}.md", mime="text/markdown", key=f"download_{item.id}", icon=":material/download:")
    st.stop()

heading, export = st.columns([4, 1], vertical_alignment="bottom")
with heading:
    st.markdown('<div class="eyebrow">RESEARCH / TOPICS</div>', unsafe_allow_html=True)
    st.title("选题工作台")
    st.caption(f"{run.subject}  /  {run.audience}")
with export:
    st.download_button("导出研究", export_markdown(run), file_name="topic-research.md", mime="text/markdown", icon=":material/download:", width="stretch")

if run.mode == "demo":
    st.info(f"固定样例 · {run.subject}。未采集热度数据，不代表实时热榜。", icon=":material/info:")
else:
    st.caption(f"联网研究 · {run.created_at.replace('T', ' ')} · 选题建议不代表知乎热度")

metrics = st.columns(4)
metrics[0].metric("候选选题", f"{len(run.topics):02}")
metrics[1].metric("参考来源", f"{len(run.sources):02}")
metrics[2].metric("证据摘要", f"{len(run.evidence):02}")
metrics[3].metric("本轮已收藏", f"{sum(t.id in saved_ids for t in run.topics):02}")
st.divider()
topics_tab, evidence_tab, trace_tab = st.tabs(["候选选题", "证据与来源", "研究过程"])

with topics_tab:
    angle = st.segmented_control("选题角度", ["全部", "决策", "争议", "实践", "认知"], default="全部", required=True, label_visibility="collapsed")
    visible = [t for t in run.topics if angle == "全部" or t.angle == angle]
    selected = next((t for t in visible if t.id == st.session_state.selected_topic), visible[0] if visible else None)
    if not visible:
        st.info("本轮没有该角度的选题。")
    else:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            for index, topic in enumerate(visible):
                with st.container(border=True):
                    st.markdown(f'<div class="topic-meta">{run.topics.index(topic) + 1:02} / {safe(topic.angle)} · {len(topic.source_ids)} 份来源{(" · 已收藏" if topic.id in saved_ids else "")}</div>', unsafe_allow_html=True)
                    st.subheader(topic.title)
                    st.write(topic.why)
                    a, b = st.columns([3, 1])
                    if a.button("查看选题" if selected.id != topic.id else "正在查看", key=f"select_{topic.id}", icon=":material/arrow_forward:", width="stretch", type="primary" if selected.id == topic.id else "secondary"):
                        st.session_state.selected_topic = topic.id
                        st.rerun()
                    if b.button("取消收藏" if topic.id in saved_ids else "收藏", key=f"save_{topic.id}", icon=":material/bookmark_added:" if topic.id in saved_ids else ":material/bookmark_add:", width="stretch"):
                        if topic.id in saved_ids:
                            db.remove(topic.id)
                        else:
                            db.save(run, topic.id)
                        st.rerun()
        with right:
            st.markdown('<div class="eyebrow">TOPIC BRIEF</div>', unsafe_allow_html=True)
            st.subheader(selected.title)
            st.caption(f"目标读者：{selected.audience}")
            st.markdown('<div class="section-label">关键分歧</div>', unsafe_allow_html=True)
            st.write(selected.tension)
            st.markdown('<div class="section-label">证据边界</div>', unsafe_allow_html=True)
            st.write(selected.caveat)
            st.markdown('<div class="section-label">参考来源</div>', unsafe_allow_html=True)
            source_list(run.sources, selected.source_ids)
            st.divider()
            if st.button("生成研究提纲", icon=":material/article:", key=f"deepen_{selected.id}", width="stretch"):
                try:
                    with st.spinner("整理研究提纲…"):
                        outline = sample_outline(selected) if run.mode == "demo" else deepen(run, selected, config)
                    st.session_state.outlines[selected.id] = outline
                except ResearchError as exc:
                    st.error(str(exc))
            outline = st.session_state.outlines.get(selected.id)
            if outline:
                st.caption("样例提纲 · 固定模板" if run.mode == "demo" else "基于本轮资料 · 未追加搜索")
                st.markdown("**核心问题**")
                st.write(outline.thesis)
                st.markdown("**研究提纲**")
                for index, section in enumerate(outline.sections, 1):
                    st.write(f"{index}. {section}")
                st.markdown("**反向思考**")
                st.write(outline.counterargument)
                st.markdown("**待核实**")
                for check in outline.checks:
                    st.write(f"• {check}")
                content = export_markdown(run, [selected]) + "\n\n## 研究提纲\n\n" + outline.thesis + "\n\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(outline.sections, 1)) + "\n\n### 反向思考\n" + outline.counterargument + "\n\n### 待核实\n" + "\n".join(f"- {x}" for x in outline.checks)
                st.download_button("导出提纲", content, file_name="topic-outline.md", mime="text/markdown", icon=":material/download:", key=f"outline_export_{selected.id}")
            st.divider()
            st.caption("这条选题值得继续吗？")
            feedback_cols = st.columns(3)
            for col, label, icon in zip(feedback_cols, ["有价值", "太宽泛", "证据不足"], ["thumb_up", "unfold_more", "fact_check"]):
                if col.button(label, key=f"feedback_{selected.id}_{label}", icon=f":material/{icon}:", type="primary" if verdicts.get(selected.id) == label else "secondary", width="stretch"):
                    db.feedback(selected.id, label)
                    st.rerun()
            if selected.id in verdicts:
                st.caption(f"已记录：{verdicts[selected.id]} · 仅用于本地复盘，尚未自动调整模型")

with evidence_tab:
    st.subheader("证据摘要")
    for index, evidence in enumerate(run.evidence, 1):
        st.markdown(f"**{index:02} · {evidence.statement}**")
        st.caption(f"来源：{' / '.join(evidence.source_ids)}")
        st.write(f"局限：{evidence.limitation}")
        st.divider()
    st.subheader("原始资料")
    source_list(run.sources)

with trace_tab:
    st.subheader("本轮研究记录")
    st.caption("固定三步流程 · Agno + Streamlit" if run.mode == "live" else "固定样例回放 · 未执行 Agent")
    for index, step in enumerate(run.trace, 1):
        st.markdown(f"**{index:02} / {step['stage']}**")
        st.write(step["detail"])
        st.caption(step["elapsed"])
        st.divider()
