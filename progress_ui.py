import time
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

import streamlit as st


def run_with_progress(task):
    started = time.monotonic()
    events = Queue()

    def report(stage, detail):
        events.put((time.monotonic(), stage, detail))

    with st.status("研究进度 · 准备开始", expanded=True) as status:
        timer = st.empty()
        activity = st.empty()
        with st.container(height=220, border=False):
            log = st.container()
        stage = "准备开始"
        step_started = started
        last_tick = None
        try:
            # Only the script thread renders UI; the worker sends actual events.
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(task, report)
                while True:
                    try:
                        event_time, next_stage, detail = events.get(timeout=0.25)
                        if next_stage != stage:
                            stage, step_started = next_stage, event_time
                            status.update(label=f"研究进度 · {stage}", expanded=True)
                        activity.text(detail)
                        with log:
                            st.text(f"{int(event_time - started)} 秒 · {stage}：{detail}")
                    except Empty:
                        pass
                    now = time.monotonic()
                    tick = (int(now - started), int(now - step_started))
                    if tick != last_tick:
                        timer.caption(f"已用 {tick[0]} 秒 · 当前步骤 {tick[1]} 秒")
                        last_tick = tick
                    if future.done() and events.empty():
                        result = future.result()
                        break
            activity.text("研究完成，结果已通过格式与引用编号校验。")
            status.update(label=f"研究完成 · 用时 {int(time.monotonic() - started)} 秒", state="complete", expanded=False)
            return result
        except Exception:
            activity.text(f"停止于：{stage}。本次未生成新结果。")
            status.update(label="研究未完成", state="error", expanded=True)
            raise
