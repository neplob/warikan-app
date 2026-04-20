import streamlit as st
from PIL import Image
import math
from fpdf import FPDF
from datetime import datetime
import fitz  # PDF読み込み用の追加機能

# --- アプリの基本設定 ---
st.set_page_config(page_title="宮宅建 中年部会 割り勘精算くん", layout="centered")
st.title("⚖️ 割り勘インボイス精算くん")
st.write("領収書をアップして、人数を入れるだけで精算書PDFを作成します。")

# --- 入力エリア ---
# typeに 'pdf' を追加しました
uploaded_file = st.file_uploader("領収書（レシート）画像またはPDFをアップロードしてください", type=['jpg', 'jpeg', 'png', 'pdf'])
num_people = st.number_input("割り勘の人数", min_value=1, value=4)

# 初期値(value)をなくし、薄い文字(placeholder)に仮の値を設定しました
purpose = st.text_input("懇親会の目的（摘要）", placeholder="例：〇〇部会 懇親会")
issuer = st.text_input("発行元（立替者）", placeholder="例：〇〇会")
recipient = st.text_input("宛名（空欄でもOK）", placeholder="〇〇様")

st.subheader("精算内容の確認")
col1, col2 = st.columns(2)
with col1:
    shop_name = st.text_input("店名", placeholder="例：居酒屋〇〇 駅前店")
    t_number = st.text_input("登録番号", placeholder="例：T1234567890123")
with col2:
    # 金額の初期値を空にし、プレースホルダーを設定しました
    total_amount = st.number_input("支払総額（円）", min_value=0, value=None, placeholder="例：10000")
    tax_10 = st.number_input("内、10%対象の消費税（円）", min_value=0, value=None, placeholder="例：909")

# --- 計算ロジック ---
amount_per_person = 0
if total_amount is not None and num_people > 0:
    amount_per_person = math.floor(total_amount / num_people)

# 未入力のままPDFにされるのを防ぐための処理
purpose_val = purpose if purpose else ""
issuer_val = issuer if issuer else ""
shop_name_val = shop_name if shop_name else ""
t_number_val = t_number if t_number else ""
total_amount_val = total_amount if total_amount is not None else 0
tax_10_val = tax_10 if tax_10 is not None else 0

# --- PDF生成機能 ---
def create_pdf():
    pdf = FPDF()
    pdf.add_font('IPAexGothic', '', 'ipaexg.ttf', uni=True)
    
    # 【1ページ目：領収書（A5横サイズ）】
    pdf.add_page(orientation='L', format='A5')
    pdf.set_auto_page_break(auto=False) 
    
    pdf.set_font('IPAexGothic', '', 10)
    today_str = datetime.now().strftime("%Y年%m月%d日")
    pdf.cell(0, 5, today_str, align='R', ln=True)
    pdf.ln(2)
    
    pdf.set_font('IPAexGothic', '', 22)
    pdf.cell(0, 10, '領収書（割り勘）', align='C', ln=True)
    pdf.line(75, 28, 135, 28)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 16)
    recipient_name = recipient if recipient else "関係者各位"
    pdf.cell(100, 8, f'{recipient_name} 様', border='B', align='L', ln=True)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 26)
    amount_text = f'￥{amount_per_person:,} -'
    pdf.cell(0, 15, amount_text, align='C', ln=True)
    pdf.line(75, 66, 135, 66)
    pdf.line(75, 67, 135, 67)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 11)
    pdf.cell(0, 6, f'但： {purpose_val}として', ln=True)
    
    pdf.set_font('IPAexGothic', '', 9)
    pdf.set_fill_color(250, 250, 250)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, 84, 190, 26, 'FD') 
    pdf.set_draw_color(0, 0, 0)
    
    pdf.set_xy(12, 86)
    pdf.cell(25, 5, '（支払先）', ln=0)
    pdf.cell(60, 5, shop_name_val, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（登録番号）', ln=0)
    pdf.cell(60, 5, t_number_val, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（元支払額）', ln=0)
    pdf.cell(100, 5, f'総額 ￥{total_amount_val:,}（内消費税 ￥{tax_10_val:,}）の1/{num_people}相当額', ln=True)
    
    pdf.set_font('IPAexGothic', '', 14)
    pdf.set_xy(120, 115)
    pdf.cell(70, 10, issuer_val, align='R', ln=True)
    
    # 疑似ハンコ
    pdf.set_draw_color(220, 20, 60)
    pdf.set_text_color(220, 20, 60)
    pdf.set_line_width(0.4)
    stamp_x, stamp_y, stamp_r = 175, 110, 8
    pdf.ellipse(stamp_x, stamp_y, stamp_r*2, stamp_r*2, 'D')
    pdf.set_font('IPAexGothic', '', 7)
    pdf.text(stamp_x + 3, stamp_y + 5.5, '宮宅建')
    pdf.text(stamp_x + 2, stamp_y + 9.5, '中年部')
    pdf.text(stamp_x + 5, stamp_y + 13.5, '会印')
    
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    
    # 【2ページ目：元の領収書（画像またはPDF）】
    if uploaded_file:
        pdf.set_auto_page_break(auto=True, margin=15) 
        pdf.add_page(orientation='P', format='A4')
        pdf.set_font('IPAexGothic', '', 12)
        pdf.cell(0, 10, '（証憑：元の領収書コピー）', ln=True) 
        
        # PDFがアップロードされた場合は1ページ目を画像化して貼り付け
        if uploaded_file.name.lower().endswith('.pdf'):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(uploaded_file)
            
        img_path = "temp_receipt.png"
        img.save(img_path)
        
        w_px, h_px = img.size
        aspect = h_px / w_px
        target_w = 140
        target_h = target_w * aspect
        
        if target_h > 260:
            target_h = 260
            target_w = target_h / aspect
            
        x_offset = (210 - target_w) / 2
        pdf.image(img_path, x=x_offset, y=25, w=target_w, h=target_h)

    return bytes(pdf.output())

# --- 発行ボタン ---
if st.button("精算書PDFを発行する"):
    # 支払総額が未入力の場合はストップをかける
    if total_amount is None:
        st.warning("⚠️「支払総額」を入力してください。")
    else:
        with st.spinner('PDFを作成中...'):
            pdf_data = create_pdf()
            st.success("作成完了！下のボタンからダウンロードしてください。")
            st.download_button(label="📥 PDFをダウンロード",
                               data=pdf_data,
                               file_name="seisan_receipt.pdf",
                               mime="application/pdf")
