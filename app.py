import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import math

# --- アプリの基本設定 ---
st.set_page_config(page_title="宮宅建 中年部会 割り勘精算くん", layout="centered")
st.title("⚖️ 割り勘インボイス精算くん")
st.write("レシートをアップして、人数を入れるだけで精算書PDFを作成します。")

# --- 入力エリア ---
uploaded_file = st.file_uploader("レシート画像をアップロードしてください", type=['jpg', 'jpeg', 'png'])
num_people = st.number_input("割り勘の人数", min_value=1, value=4)
purpose = st.text_input("懇親会の目的（摘要）", value="中年部会 懇親会")
issuer = st.text_input("発行元（立替者）", value="宮宅建中年部会")
recipient = st.text_input("宛名（空欄でもOK）", placeholder="〇〇様")

# 本来はここでAI（OCR）が読み取りますが、確実性のために確認・入力欄を設けます
st.subheader("精算内容の確認")
col1, col2 = st.columns(2)
with col1:
    shop_name = st.text_input("店名", value="タコとハイボール一番町店")
    t_number = st.text_input("登録番号", value="T8100001025796")
with col2:
    total_amount = st.number_input("支払総額（円）", value=8410)
    tax_10 = st.number_input("内、10%対象の消費税（円）", value=765)

# --- 計算ロジック（全員一律切り捨て） ---
amount_per_person = math.floor(total_amount / num_people)
tax_per_person = math.floor(tax_10 / num_people)

# --- PDF生成機能 ---
def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('IPAexGothic', '', 'ipaexg.ttf', uni=True) # 日本語フォント設定
    pdf.set_font('IPAexGothic', '', 16)

    # 1ページ目：精算書
    pdf.cell(0, 10, '立替金精算書', ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('IPAexGothic', '', 12)
    pdf.cell(0, 10, f'宛名：{recipient if recipient else "関係者各位"}', ln=True)
    pdf.ln(5)
    pdf.set_font('IPAexGothic', '', 20)
    pdf.cell(0, 15, f'金額：￥{amount_per_person:,} -', border=1, ln=True, align='C')
    pdf.set_font('IPAexGothic', '', 10)
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"但：{purpose}として（{shop_name} 支払分）\n"
                          f"----------------------------------------\n"
                          f"【元のインボイス情報】\n"
                          f"支払先：{shop_name}\n"
                          f"登録番号：{t_number}\n"
                          f"元支払総額：￥{total_amount:,}（内消費税 ￥{tax_10:,}）\n"
                          f"※上記金額の1/{num_people}を精算いたします。\n"
                          f"----------------------------------------\n"
                          f"発行者：{issuer}")

    # 2ページ目：レシート画像
    if uploaded_file:
        pdf.add_page()
        pdf.cell(0, 10, '（証憑：元のレシートコピー）', ln=True)
        img = Image.open(uploaded_file)
        img_path = "temp_receipt.png"
        img.save(img_path)
        pdf.image(img_path, x=10, y=30, w=100) # サイズは調整可

    return bytes(pdf.output())

# --- 発行ボタン ---
if st.button("精算書PDFを発行する"):
    with st.spinner('PDFを作成中...'):
        pdf_data = create_pdf()
        st.success("作成完了！下のボタンからダウンロードしてください。")
        st.download_button(label="📥 PDFをダウンロード",
                           data=pdf_data,
                           file_name="seisan.pdf",
                           mime="application/pdf")
