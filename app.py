import streamlit as st
from PIL import Image
import math
from fpdf import FPDF
from datetime import datetime

# --- アプリの基本設定 ---
st.set_page_config(page_title="宮宅建 中年部会 割り勘精算くん", layout="centered")
st.title("⚖️ 割り勘インボイス精算くん")
st.write("レシートをアップして、人数を入れるだけで精算書PDFを作成します。")

# --- 入力エリア ---
uploaded_file = st.file_uploader("領収書（レシート）画像をアップロードしてください", type=['jpg', 'jpeg', 'png'])
num_people = st.number_input("割り勘の人数", min_value=1, value=4)
purpose = st.text_input("懇親会の目的（摘要）", value="中年部会 懇親会")
issuer = st.text_input("発行元（立替者）", value="宮宅建中年部会")
recipient = st.text_input("宛名（空欄でもOK）", placeholder="〇〇様")

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

# --- PDF生成機能 ---
def create_pdf():
    pdf = FPDF()
    pdf.add_font('IPAexGothic', '', 'ipaexg.ttf', uni=True)
    
    # 【1ページ目：領収書（A5横サイズ）】
    pdf.add_page(orientation='L', format='A5')
    # 自動改ページを無効化（ハンコなどが2ページ目に押し出されるのを防ぐ）
    pdf.set_auto_page_break(auto=False) 
    
    # 日付
    pdf.set_font('IPAexGothic', '', 10)
    today_str = datetime.now().strftime("%Y年%m月%d日")
    pdf.cell(0, 5, today_str, align='R', ln=True)
    pdf.ln(2)
    
    # タイトル
    pdf.set_font('IPAexGothic', '', 22)
    pdf.cell(0, 10, '領収書（割り勘）', align='C', ln=True)
    # タイトルの下線（文字にかぶらないように数ミリ下にずらしました）
    pdf.line(75, 28, 135, 28)
    pdf.ln(6)
    
    # 宛名
    pdf.set_font('IPAexGothic', '', 16)
    recipient_name = recipient if recipient else "関係者各位"
    pdf.cell(100, 8, f'{recipient_name} 様', border='B', align='L', ln=True)
    pdf.ln(6)
    
    # 金額
    pdf.set_font('IPAexGothic', '', 26)
    amount_text = f'￥{amount_per_person:,} -'
    pdf.cell(0, 15, amount_text, align='C', ln=True)
    # 金額の下二重線
    pdf.line(75, 66, 135, 66)
    pdf.line(75, 67, 135, 67)
    pdf.ln(6)
    
    # 摘要
    pdf.set_font('IPAexGothic', '', 11)
    pdf.cell(0, 6, f'但： {purpose}として', ln=True)
    
    # 詳細枠（全体を少し上に詰めました）
    pdf.set_font('IPAexGothic', '', 9)
    pdf.set_fill_color(250, 250, 250)
    pdf.set_draw_color(200, 200, 200) # 薄いグレーの枠線
    pdf.rect(10, 84, 190, 26, 'FD') 
    pdf.set_draw_color(0, 0, 0) # 黒に戻す
    
    pdf.set_xy(12, 86)
    pdf.cell(25, 5, '（支払先）', ln=0)
    pdf.cell(60, 5, shop_name, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（登録番号）', ln=0)
    pdf.cell(60, 5, t_number, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（元支払額）', ln=0)
    pdf.cell(100, 5, f'総額 ￥{total_amount:,}（内消費税 ￥{tax_10:,}）の1/{num_people}相当額', ln=True)
    
    # 発行者
    pdf.set_font('IPAexGothic', '', 14)
    pdf.set_xy(120, 115)
    pdf.cell(70, 10, issuer, align='R', ln=True)
    
    # 疑似ハンコ（赤い丸と文字）
    pdf.set_draw_color(220, 20, 60)
    pdf.set_text_color(220, 20, 60)
    pdf.set_line_width(0.4)
    stamp_x, stamp_y, stamp_r = 175, 110, 8
    pdf.ellipse(stamp_x, stamp_y, stamp_r*2, stamp_r*2, 'D')
    pdf.set_font('IPAexGothic', '', 7)
    pdf.text(stamp_x + 3, stamp_y + 5.5, '宮宅建')
    pdf.text(stamp_x + 2, stamp_y + 9.5, '中年部')
    pdf.text(stamp_x + 5, stamp_y + 13.5, '会印')
    
    # 色を黒に戻す
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    
    # 【2ページ目：元の領収書画像】
    if uploaded_file:
        # 自動改ページを元に戻す
        pdf.set_auto_page_break(auto=True, margin=15) 
        pdf.add_page(orientation='P', format='A4')
        pdf.set_font('IPAexGothic', '', 12)
        
        # ご要望通り「レシート」を「領収書」に変更
        pdf.cell(0, 10, '（証憑：元の領収書コピー）', ln=True) 
        
        img = Image.open(uploaded_file)
        img_path = "temp_receipt.png"
        img.save(img_path)
        
        # 縦長レシートがはみ出ないように縮小計算
        w_px, h_px = img.size
        aspect = h_px / w_px
        target_w = 140 # mm (基本の幅)
        target_h = target_w * aspect
        
        if target_h > 260: # A4の縦(297mm)に収まるように最大260mmに自動縮小
            target_h = 260
            target_w = target_h / aspect
            
        x_offset = (210 - target_w) / 2 # 中央寄せ
        pdf.image(img_path, x=x_offset, y=25, w=target_w, h=target_h)

    return bytes(pdf.output())

# --- 発行ボタン ---
if st.button("精算書PDFを発行する"):
    with st.spinner('PDFを作成中...'):
        pdf_data = create_pdf()
        st.success("作成完了！下のボタンからダウンロードしてください。")
        st.download_button(label="📥 PDFをダウンロード",
                           data=pdf_data,
                           file_name="seisan_receipt.pdf",
                           mime="application/pdf")
