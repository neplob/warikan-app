import streamlit as st
from PIL import Image
import math
from fpdf import FPDF
from datetime import datetime
import fitz  # PyMuPDF
import io

# --- アプリの基本設定 ---
st.set_page_config(page_title="宮宅建 中年部会 割り勘精算くん", layout="centered")
st.title("⚖️ 割り勘インボイス精算くん")
st.write("領収書をアップして、人数を入れるだけで精算書PDFを作成します。")

# --- 入力エリア ---
uploaded_file = st.file_uploader("領収書（レシート）画像またはPDFをアップロードしてください", type=['jpg', 'jpeg', 'png', 'pdf'])
num_people = st.number_input("割り勘の人数", min_value=1, value=4)

purpose = st.text_input("懇親会の目的（摘要）", placeholder="例：〇〇部会 懇親会")
issuer = st.text_input("発行元（立替者）", placeholder="例：〇〇会")
recipient = st.text_input("宛名（空欄でもOK）", placeholder="〇〇様")

st.subheader("精算内容の確認")
col1, col2 = st.columns(2)
with col1:
    shop_name = st.text_input("店名", placeholder="例：居酒屋〇〇 駅前店")
    t_number = st.text_input("登録番号", placeholder="例：T1234567890123")
with col2:
    total_amount = st.number_input("支払総額（円）", min_value=0, value=None, placeholder="例：10000")
    tax_10 = st.number_input("内、10%対象の消費税（円）", min_value=0, value=None, placeholder="例：909")

# --- 計算ロジック ---
amount_per_person = 0
if total_amount is not None and num_people > 0:
    amount_per_person = math.floor(total_amount / num_people)

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
    
    # 発行者と角印
    pdf.set_font('IPAexGothic', '', 14)
    issuer_text = issuer_val if issuer_val else "宮宅建中年部会"
    text_width = pdf.get_string_width(issuer_text)
    stamp_size = 16
    margin_between = 4
    total_width = text_width + margin_between + stamp_size
    start_x = 195 - total_width 
    text_y = 115
    pdf.set_xy(start_x, text_y)
    pdf.cell(text_width, 10, issuer_text, align='L')
    
    stamp_x, stamp_y = start_x + text_width + margin_between, text_y - 3 
    stamp_text = issuer_text + "印"
    if len(stamp_text) > 9: stamp_text = stamp_text[:8] + "印"
    
    length = len(stamp_text)
    cols_s, rows_s = (2, 2) if length <= 4 else (2, 3) if length <= 6 else (3, 3)
    stamp_text = stamp_text.ljust(cols_s * rows_s, " ")
    
    pdf.set_draw_color(220, 20, 60)
    pdf.set_text_color(220, 20, 60)
    pdf.set_line_width(0.5)
    pdf.rect(stamp_x, stamp_y, stamp_size, stamp_size)
    pdf.set_line_width(0.15)
    pdf.rect(stamp_x+0.8, stamp_y+0.8, stamp_size-1.6, stamp_size-1.6)
    
    cell_w, cell_h = stamp_size / cols_s, stamp_size / rows_s
    pdf.set_font('IPAexGothic', '', min(cell_w, cell_h) * 2.2)
    for c in range(cols_s):
        for r in range(rows_s):
            idx = c * rows_s + r
            if idx < len(stamp_text):
                char = stamp_text[idx]
                pdf.set_xy(stamp_x + (cols_s - 1 - c) * cell_w, stamp_y + r * cell_h - 0.5)
                pdf.cell(cell_w, cell_h, char, align='C')
                
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)
    
    # 【2ページ目：元の領収書を「まとめて1枚」に配置】
    if uploaded_file:
        pdf.set_auto_page_break(auto=True, margin=15) 
        pdf.add_page(orientation='P', format='A4')
        pdf.set_font('IPAexGothic', '', 12)
        pdf.cell(0, 10, '（証憑：元の領収書コピー）', ln=True) 
        
        images = []
        if uploaded_file.name.lower().endswith('.pdf'):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                images.append(Image.open(io.BytesIO(img_data)))
        else:
            images.append(Image.open(uploaded_file))
            
        # 複数ページをグリッド配置する計算
        num_imgs = len(images)
        cols = 1 if num_imgs == 1 else 2 if num_imgs <= 4 else 3
        rows = math.ceil(num_imgs / cols)
        
        available_w = 190 # A4横幅マイナスマージン
        available_h = 260 # A4縦幅マイナスマージン
        
        cell_w = available_w / cols
        cell_h = available_h / rows
        
        for i, img in enumerate(images):
            img_path = f"temp_page_{i}.png"
            img.save(img_path)
            
            # セル内でのアスペクト比調整
            w_px, h_px = img.size
            aspect = h_px / w_px
            
            draw_w = cell_w - 5 # マージン
            draw_h = draw_w * aspect
            
            if draw_h > (cell_h - 5):
                draw_h = cell_h - 5
                draw_w = draw_h / aspect
                
            col_idx = i % cols
            row_idx = i // cols
            
            cur_x = 10 + col_idx * cell_w + (cell_w - draw_w) / 2
            cur_y = 25 + row_idx * cell_h + (cell_h - draw_h) / 2
            
            pdf.image(img_path, x=cur_x, y=cur_y, w=draw_w, h=draw_h)

    return bytes(pdf.output())

# --- 発行ボタン ---
if st.button("精算書PDFを発行する"):
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
