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
    # 10%、8%、非課税の入力欄を追加
    tax_10 = st.number_input("内、10%対象の消費税（円）", min_value=0, value=None, placeholder="例：909")
    tax_8 = st.number_input("内、8%対象の消費税（円）", min_value=0, value=None, placeholder="例：80")
    non_tax = st.number_input("内、非課税対象の金額（円）", min_value=0, value=None, placeholder="例：1000")

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

# --- 税区分テキストの動的生成（入力されたものだけを抽出） ---
tax_texts = []
if tax_10 is not None:
    tax_texts.append(f"10%消費税 ￥{tax_10:,}")
if tax_8 is not None:
    tax_texts.append(f"8%消費税 ￥{tax_8:,}")
if non_tax is not None:
    tax_texts.append(f"非課税 ￥{non_tax:,}")

if tax_texts:
    # 複数ある場合は「、」で繋げる
    tax_str = "、".join(tax_texts)
    amount_desc = f'総額 ￥{total_amount_val:,}（内、{tax_str}）の1/{num_people}相当額'
else:
    # 1つも入力されなかった場合
    amount_desc = f'総額 ￥{total_amount_val:,} の1/{num_people}相当額'

# 宛名リストの作成
input_recipients = [r.strip() for r in recipient.split(',')] if recipient else []
input_recipients = [r for r in input_recipients if r]

# 割り勘人数に対して不足している分を「空欄（宛名なし）」で補填
recipients_list = input_recipients.copy()
if len(recipients_list) < num_people:
    recipients_list.append("") # 空欄は1つだけ

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
    disp_name = target_recipient if target_recipient else "　　　　　　　　" # 空欄時はスペース
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
    # ここに動的生成した内訳テキストを配置
    pdf.cell(100, 5, amount_desc, ln=True)
    
    # 発行者と角印
    pdf.set_font('IPAexGothic', '', 14)
    issuer_text = issuer_val if issuer_val else "宮宅建中年部会"
    tw = pdf.get_string_width(issuer_text)
    ss = 16
    start_x = 195 - (tw + 4 + ss)
    pdf.set_xy(start_x, 115)
    pdf.cell(tw, 10, issuer_text, align='L')
    
    sx, sy = start_x + tw + 4, 112
    st_txt = (issuer_text + "印")[:9].ljust(9)
    pdf.set_draw_color(220, 20, 60); pdf.set_text_color(220, 20, 60)
    pdf.set_line_width(0.5); pdf.rect(sx, sy, ss, ss)
    pdf.set_line_width(0.15); pdf.rect(sx+0.8, sy+0.8, ss-1.6, ss-1.6)
    pdf.set_font('IPAexGothic', '', 5.5)
    for c in range(3):
        for r in range(3):
            pdf.set_xy(sx + (2-c)*(ss/3), sy + r*(ss/3))
            pdf.cell(ss/3, ss/3, st_txt[c*3+r], align='C')

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
            
            # 作成したデータをセッションステート（記憶領域）に保存
            st.session_state.generated_pdfs = temp_pdfs
            st.session_state.show_downloads = True

# 記憶領域にデータがあれば、常にダウンロードボタンを表示する
if st.session_state.show_downloads:
    st.success("精算用領収書ができたので下記からダウンロードください。")
    for label, pdf_data, fname, key in st.session_state.generated_pdfs:
        st.download_button(label=label, data=pdf_data, file_name=fname, mime="application/pdf", key=key)
