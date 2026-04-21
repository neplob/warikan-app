import streamlit as st
from PIL import Image
import math
from fpdf import FPDF
from datetime import datetime
import fitz  # PyMuPDF
import io

# --- アプリの基本設定 ---
st.set_page_config(page_title="割り勘精算くん", layout="centered")
st.title("⚖️ 割り勘精算くん")
st.write("領収書をアップして、人数を入れるだけで精算書PDFを作成します。")

# --- セッションステート（記憶領域）の初期化 ---
if "show_downloads" not in st.session_state:
    st.session_state.show_downloads = False
if "generated_pdfs" not in st.session_state:
    st.session_state.generated_pdfs = []

# --- 入力エリア ---
uploaded_file = st.file_uploader("領収書（レシート）画像またはPDFをアップロードしてください", type=['jpg', 'jpeg', 'png', 'pdf'])
num_people = st.number_input("割り勘の人数", min_value=1, value=4)

purpose = st.text_input("懇親会の目的（摘要）", placeholder="例：〇〇部会 懇親会")
issuer = st.text_input("発行元（立替者）", placeholder="例：〇〇会")
recipient = st.text_input("宛名（カンマ「,」区切りで複数入力可）", placeholder="例：A社様, B様")

st.subheader("精算内容の確認")
col1, col2 = st.columns(2)
with col1:
    shop_name = st.text_input("店名", placeholder="例：居酒屋〇〇 駅前店")
    t_number = st.text_input("登録番号", placeholder="例：1234567890123（Tは自動付与）")
with col2:
    total_amount = st.number_input("支払総額（円）", min_value=0, value=None, placeholder="例：10000")
    tax_10 = st.number_input("内、10%対象の消費税（円）", min_value=0, value=None, placeholder="例：909")
    tax_8 = st.number_input("内、8%対象の消費税（円）", min_value=0, value=None, placeholder="例：80")

# --- ロジック準備 ---
amount_per_person = 0
if total_amount is not None and num_people > 0:
    amount_per_person = math.floor(total_amount / num_people)

purpose_val = purpose if purpose else ""
issuer_val = issuer if issuer else ""
shop_name_val = shop_name if shop_name else ""
t_number_val = t_number.strip() if t_number else ""
if t_number_val:
    t_number_val = 'T' + (t_number_val[1:] if t_number_val[0].upper() == 'T' else t_number_val)
total_amount_val = total_amount if total_amount is not None else 0

# --- 税区分テキストの動的生成 ---
tax_texts = []
if tax_10 is not None:
    tax_texts.append(f"10%消費税 ￥{tax_10:,}")
if tax_8 is not None:
    tax_texts.append(f"8%消費税 ￥{tax_8:,}")

if tax_texts:
    tax_str = "、".join(tax_texts)
    amount_desc = f'総額 ￥{total_amount_val:,}（内、{tax_str}）の1/{num_people}相当額'
else:
    amount_desc = f'総額 ￥{total_amount_val:,} の1/{num_people}相当額'

# 宛名リストの作成
input_recipients = [r.strip() for r in recipient.split(',')] if recipient else []
input_recipients = [r for r in input_recipients if r]

recipients_list = input_recipients.copy()
if len(recipients_list) < num_people:
    recipients_list.append("") 

# --- PDF生成関数 ---
def create_pdf(target_recipient):
    pdf = FPDF()
    pdf.add_font('IPAexGothic', '', 'ipaexg.ttf', uni=True)
    pdf.add_page(orientation='L', format='A5')
    pdf.set_auto_page_break(auto=False) 
    
    pdf.set_font('IPAexGothic', '', 10)
    pdf.cell(0, 5, datetime.now().strftime("%Y年%m月%d日"), align='R', ln=True)
    pdf.ln(2)
    pdf.set_font('IPAexGothic', '', 22)
    pdf.cell(0, 10, '領収書（割り勘）', align='C', ln=True)
    pdf.line(75, 28, 135, 28)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 16)
    disp_name = target_recipient if target_recipient else "　　　　　　　　"
    if target_recipient and not any(disp_name.endswith(s) for s in ["様", "御中", "殿"]):
        disp_name += " 様"
    pdf.cell(100, 8, disp_name, border='B', align='L', ln=True)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 26)
    pdf.cell(0, 15, f'￥{amount_per_person:,} -', align='C', ln=True)
    pdf.line(75, 66, 135, 66)
    pdf.line(75, 67, 135, 67)
    pdf.ln(6)
    
    pdf.set_font('IPAexGothic', '', 11)
    pdf.cell(0, 6, f'但： {purpose_val}として', ln=True)
    
    pdf.set_font('IPAexGothic', '', 9)
    pdf.set_fill_color(250, 250, 250)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, 84, 190, 26, 'FD') 
    
    pdf.set_xy(12, 86)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(25, 5, '（支払先）', ln=0)
    pdf.cell(60, 5, shop_name_val, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（登録番号）', ln=0)
    pdf.cell(60, 5, t_number_val, ln=True)
    pdf.set_x(12)
    pdf.cell(25, 5, '（元支払額）', ln=0)
    pdf.cell(100, 5, amount_desc, ln=True)
    
    # ----------------------------------------------------
    # 発行者名と、正方形スタンプの描画
    # ----------------------------------------------------
    issuer_text = issuer_val if issuer_val else "宮宅建中年部会"
    stamp_text = issuer_text # 「印」は勝手に追加しない
    
    # 黒文字の発行者名の幅を取得
    pdf.set_font('IPAexGothic', '', 14)
    text_width = pdf.get_string_width(issuer_text)
    
    # スタンプのサイズを正方形に固定（14mm）
    stamp_size = 14
        
    # 全体の幅から配置のスタート地点を逆算（右端から綺麗に揃える）
    margin_between = 4 
    total_width = text_width + margin_between + stamp_size
    start_x = 195 - total_width 
    text_y = 115
    
    # 黒文字の描画
    pdf.set_font('IPAexGothic', '', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(start_x, text_y)
    pdf.cell(text_width, 10, issuer_text, align='L')
    
    # スタンプ枠の描画（赤色・二重線・正方形）
    stamp_x = start_x + text_width + margin_between
    stamp_y = text_y - 2 # 見栄えが良くなるよう少し上げる
    
    pdf.set_draw_color(220, 20, 60)
    pdf.set_text_color(220, 20, 60)
    pdf.set_line_width(0.4)
    pdf.rect(stamp_x, stamp_y, stamp_size, stamp_size) # 外枠
    pdf.set_line_width(0.15)
    pdf.rect(stamp_x + 0.8, stamp_y + 0.8, stamp_size - 1.6, stamp_size - 1.6) # 内枠
    
    # テキストをよしなに分割（3文字以下は1行、4〜8文字は2行、9文字以上は3行）
    length = len(stamp_text)
    if length <= 3:
        lines = [stamp_text]
    elif length <= 8:
        mid = math.ceil(length / 2)
        lines = [stamp_text[:mid], stamp_text[mid:]]
    else:
        third = math.ceil(length / 3)
        lines = [stamp_text[:third], stamp_text[third:third*2], stamp_text[third*2:]]
        
    # フォントサイズの自動調整（枠内に収まるように）
    pt_size = 18.0
    pdf.set_font('IPAexGothic', '', pt_size)
    
    while True:
        max_w = max([pdf.get_string_width(line) for line in lines])
        line_height = pt_size * 0.4
        total_h = line_height * len(lines)
        
        if max_w <= (stamp_size - 2) and total_h <= (stamp_size - 2):
            break
        pt_size -= 0.5
        if pt_size < 3: 
            break
        pdf.set_font('IPAexGothic', '', pt_size)
        
    # スタンプ内の文字描画（ど真ん中に配置）
    line_height = pt_size * 0.4
    total_h = line_height * len(lines)
    start_y = stamp_y + (stamp_size - total_h) / 2
    
    for i, line in enumerate(lines):
        pdf.set_xy(stamp_x, start_y + i * line_height)
        pdf.cell(stamp_size, line_height, line, align='C')
    # ----------------------------------------------------

    # 【証憑ページ】
    if uploaded_file:
        pdf.set_text_color(0, 0, 0); pdf.set_draw_color(0, 0, 0); pdf.set_line_width(0.2)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page(orientation='P', format='A4')
        pdf.set_font('IPAexGothic', '', 12)
        pdf.cell(0, 10, '（証憑：元の領収書コピー）', ln=True)
        uploaded_file.seek(0)
        images = []
        if uploaded_file.name.lower().endswith('.pdf'):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            for p in range(len(doc)):
                pix = doc.load_page(p).get_pixmap(dpi=150)
                images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
        else:
            images.append(Image.open(uploaded_file))
        
        cols = 1 if len(images)==1 else 2 if len(images)<=4 else 3
        rows = math.ceil(len(images)/cols)
        cw, ch = 190/cols, 260/rows
        for i, img in enumerate(images):
            img.save(f"t_{i}.png")
            iw, ih = img.size
            dw = cw-5; dh = dw*(ih/iw)
            if dh > ch-5: dh = ch-5; dw = dh/(ih/iw)
            pdf.image(f"t_{i}.png", x=10+(i%cols)*cw+(cw-dw)/2, y=25+(i//cols)*ch+(ch-dh)/2, w=dw, h=dh)

    return bytes(pdf.output())

# --- 実行セクション ---
if st.button("精算用データを作成する"):
    if total_amount is None:
        st.warning("⚠️「支払総額」を入力してください。")
    else:
        with st.spinner("準備中です。しばらくお待ちください..."):
            temp_pdfs = []
            for i, rec in enumerate(recipients_list):
                pdf_data = create_pdf(rec)
                label = f"📥 {rec if rec else '宛名なし'} の領収書をダウンロード"
                fname = f"receipt_{rec if rec else 'blank'}.pdf"
                temp_pdfs.append((label, pdf_data, fname, f"dl_{i}"))
            
            st.session_state.generated_pdfs = temp_pdfs
            st.session_state.show_downloads = True

if st.session_state.show_downloads:
    st.success("精算用領収書ができたので下記からダウンロードください。")
    for label, pdf_data, fname, key in st.session_state.generated_pdfs:
        st.download_button(label=label, data=pdf_data, file_name=fname, mime="application/pdf", key=key)
