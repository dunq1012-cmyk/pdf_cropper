import io
import fitz  # PyMuPDF
import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import reportlab.lib.utils

st.set_page_config(page_title="PDF交互式切块与重组", layout="wide")

st.title("✂️ PDF 交互式自由划框切块与拼接")
st.caption("上传PDF ➡️ 画框裁切碎片 ➡️ 勾选留存 & 调整顺序 ➡️ 重新排版导出")

# 初始化 Session State
if "fragments" not in st.session_state:
    st.session_state.fragments = []  # 保存所有切好的碎片 [{id, name, image, keep}]
if "frag_counter" not in st.session_state:
    st.session_state.frag_counter = 1

# --- 1. PDF 上传与加载 ---
uploaded_pdf = st.file_uploader("上传你的 PDF 报告", type=["pdf"])

if uploaded_pdf:
    @st.cache_data
    def pdf_to_image(pdf_bytes):
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]  # 默认处理第 1 页
        pix = page.get_pixmap(dpi=150)
        return Image.open(io.BytesIO(pix.tobytes("png")))

    pdf_img = pdf_to_image(uploaded_pdf.read())

    col_crop, col_list = st.columns([1.1, 0.9])

    # --- 2. 左侧：交互式划框裁切区 ---
    with col_crop:
        st.subheader("1. 在图上移动框/划定分割区域")
        st.info("💡 调整框的大小和位置，选择你要截取的模块，然后点击下方【确认截取】。")

        cropped_img = st_cropper(
            pdf_img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None
        )

        if st.button("✂️ 确认截取此模块碎片", type="primary", use_container_width=True):
            target_w = 800
            w_pct = target_w / float(cropped_img.size[0])
            h_size = int(float(cropped_img.size[1]) * w_pct)
            resized_crop = cropped_img.resize((target_w, h_size), Image.Resampling.LANCZOS)

            st.session_state.fragments.append({
                "id": f"frag_{st.session_state.frag_counter}",
                "name": f"模块碎片 #{st.session_state.frag_counter}",
                "image": resized_crop,
                "keep": True
            })
            st.session_state.frag_counter += 1
            st.success("✅ 已添加为碎片！可在右侧管理。")
            st.rerun()

    # --- 3. 右侧：碎片管理 ---
    with col_list:
        st.subheader("2. 碎片卡片管理 & 顺序调整")

        if not st.session_state.fragments:
            st.warning("👈 请在左侧移动框并点击【确认截取】生成第一个碎片。")
        else:
            for idx, item in enumerate(st.session_state.fragments):
                with st.expander(f"📌 {item['name']}", expanded=True):
                    c_chk, c_up, c_down, c_del = st.columns([0.4, 0.2, 0.2, 0.2])

                    with c_chk:
                        item["keep"] = st.checkbox("留存/显示", value=item["keep"], key=f"chk_{item['id']}")
                    with c_up:
                        if st.button("⬆️", key=f"up_{item['id']}") and idx > 0:
                            st.session_state.fragments[idx], st.session_state.fragments[idx-1] = (
                                st.session_state.fragments[idx-1], st.session_state.fragments[idx]
                            )
                            st.rerun()
                    with c_down:
                        if st.button("⬇️", key=f"dn_{item['id']}") and idx < len(st.session_state.fragments)-1:
                            st.session_state.fragments[idx], st.session_state.fragments[idx+1] = (
                                st.session_state.fragments[idx+1], st.session_state.fragments[idx]
                            )
                            st.rerun()
                    with c_del:
                        if st.button("🗑️", key=f"del_{item['id']}"):
                            st.session_state.fragments.pop(idx)
                            st.rerun()

                    # 修复点：替换为 use_container_width
                    st.image(item["image"], use_container_width=True)

    # --- 4. 底部：合成 A4 预览与 PDF 导出 ---
    st.markdown("---")
    st.subheader("3. 最终重新排版与 PDF 预览")

    active_frags = [f for f in st.session_state.fragments if f["keep"]]

    if active_frags:
        preview_col, download_col = st.columns([2, 1])

        with preview_col:
            st.caption("📄 模拟 A4 最终打印流：")
            st.markdown('<div style="border:1px solid #ccc; padding:10px; background:#fff;">', unsafe_allow_html=True)
            for f in active_frags:
                # 修复点：替换为 use_container_width
                st.image(f["image"], caption=f.get("name"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with download_col:
            def build_pdf(frags):
                pdf_buf = io.BytesIO()
                c = canvas.Canvas(pdf_buf, pagesize=A4)
                a4_w, a4_h = A4
                y_pos = a4_h - 20

                for item in frags:
                    img = item["image"]
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="PNG")
                    img_buf.seek(0)

                    draw_w = a4_w - 40
                    draw_h = (img.height / img.width) * draw_w

                    if y_pos - draw_h < 20:
                        c.showPage()
                        y_pos = a4_h - 20

                    c.drawImage(
                        reportlab.lib.utils.ImageReader(img_buf),
                        20, y_pos - draw_h, width=draw_w, height=draw_h
                    )
                    y_pos -= (draw_h + 10)

                c.save()
                pdf_buf.seek(0)
                return pdf_buf

            pdf_data = build_pdf(active_frags)

            st.write("### 导出成果")
            st.download_button(
                label="🖨️ 下载重排版后的 PDF 报告",
                data=pdf_data,
                file_name="重新排版报告.pdf",
                mime="application/pdf",
                use_container_width=True
            )
else:
    st.info("👈 请先上传 PDF 报告文件开始体验拉框切块功能！")
