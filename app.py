import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import date

st.set_page_config(page_title="紅葉國小疲勞監控系統", layout="centered")

SHEET_ID = "1ySyEo3isdzzpOtqvitNZrrW-ucznre5RLsFxRLn6Czs"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyNeX3uM-rhdY428GM44G7CmQfIxl9s_jwZLkL5z0nZm65dV8skOKfFLeuJmRazUChO/exec"

st.markdown("""
<style>
.block-container {
    padding-top: 4rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 760px;
}
h1 {
    font-size: 34px !important;
    font-weight: 800 !important;
    margin-bottom: 1.5rem !important;
}
h2, h3 {
    font-size: 26px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    font-size: 42px;
}
[data-baseweb="select"] {
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    raw = pd.read_csv(CSV_URL, header=None)

    names = raw.iloc[0, 1:].tolist()
    data = raw.iloc[1:, :].copy()
    data.columns = ["日期"] + names

    data["日期"] = (
        data["日期"]
        .astype(str)
        .str.replace("月", "-", regex=False)
        .str.replace("日", "", regex=False)
    )

    data["日期"] = "2026-" + data["日期"]
    data["日期"] = pd.to_datetime(data["日期"], errors="coerce")

    long_df = data.melt(
        id_vars="日期",
        var_name="選手",
        value_name="平均心跳率"
    )

    long_df["平均心跳率"] = pd.to_numeric(
        long_df["平均心跳率"],
        errors="coerce"
    )

    long_df = long_df.dropna(subset=["日期", "平均心跳率"])

    return long_df


df = load_data()

if df.empty:
    st.error("目前沒有可用資料，請確認 Google Sheet 是否有正確填寫日期與心跳率。")
    st.stop()

st.title("紅葉心跳監控")

page = st.selectbox(
    "選擇頁面",
    ["團體監控", "個人監控", "新增資料"]
)

if page == "團體監控":
    st.subheader("團體靜止心跳率")

    group_df = df.groupby("日期", as_index=False)["平均心跳率"].mean()
    latest_avg = group_df.iloc[-1]["平均心跳率"]
    group_avg_line = group_df["平均心跳率"].mean()

    st.metric("今日團體平均", f"{latest_avg:.1f} bpm")

    fig = px.line(
        group_df,
        x="日期",
        y="平均心跳率",
        markers=True
    )

    fig.add_hline(
        y=group_avg_line,
        line_dash="dash",
        annotation_text=f"團體平均線：{group_avg_line:.1f} bpm",
        annotation_position="top left"
    )

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="日期",
        yaxis_title="心跳率"
    )

    st.plotly_chart(fig, use_container_width=True)


elif page == "個人監控":
    st.subheader("個人靜止心跳率")

    athletes = sorted(df["選手"].unique())

    selected_athlete = st.selectbox(
        "選擇選手",
        athletes
    )

    athlete_df = df[df["選手"] == selected_athlete]
    latest_hr = athlete_df.iloc[-1]["平均心跳率"]
    athlete_avg_line = athlete_df["平均心跳率"].mean()

    st.metric(
        f"{selected_athlete} 今日心跳率",
        f"{latest_hr:.1f} bpm"
    )

    fig = px.line(
        athlete_df,
        x="日期",
        y="平均心跳率",
        markers=True
    )

    fig.add_hline(
        y=athlete_avg_line,
        line_dash="dash",
        annotation_text=f"個人平均線：{athlete_avg_line:.1f} bpm",
        annotation_position="top left"
    )

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="日期",
        yaxis_title="心跳率"
    )

    st.plotly_chart(fig, use_container_width=True)


elif page == "新增資料":
    st.subheader("新增今日資料")

    athletes = sorted(df["選手"].unique())

    with st.form("add_data_form"):
        input_date = st.date_input(
            "日期",
            value=date.today()
        )

        selected_athlete = st.selectbox(
            "選擇選手",
            athletes
        )

        heart_rate = st.number_input(
            "輸入心跳率",
            min_value=30,
            max_value=200,
            step=1
        )

        submitted = st.form_submit_button("送出資料")

        if submitted:
            payload = {
                "date": f"{input_date.month}月{input_date.day}日",
                "athlete": selected_athlete,
                "heartRate": int(heart_rate)
            }

            response = requests.post(
                WEB_APP_URL,
                json=payload
            )

            if response.status_code == 200:
                st.success("資料已成功送出！請重新整理頁面查看更新。")
                st.cache_data.clear()
            else:
                st.error("送出失敗，請檢查 Apps Script 權限。")


with st.expander("查看資料"):
    st.dataframe(df, use_container_width=True)
