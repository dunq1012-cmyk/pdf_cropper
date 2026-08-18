import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper
from core.pdf_handler import get_pdf_page_image, build_reconstructed_pdf

st.set_page_config(page_title="PDF交互式切块与重组", layout="wide")

st.title("✂️ 多页 PDF 交互式自由划框切块与拼接")
st.caption("上传多页 PDF ➡️ 切换页面画框裁切碎片 ➡️ 勾选留存 & 跨页自由排序 ➡️ 重新排版导出")

# 初始化 Session State
if "fragments" not in st.session_state:
    st.session_state.fragments = []
if "frag_counter" not in st.session_state:
    st.session_state.frag_counter = 1

# --- 1. PDF 上传 ---
uploaded_pdf = st.file_uploader("上传你的 PDF 报告（支持单页/多页）", type=["pdf"])

if uploaded_pdf:
    pdf_bytes = uploaded_pdf.read()

    col_crop, col_list = st.columns([1.1, 0.9])

    # --- 2. 左侧：页面选择与裁切区 ---
    with col_crop:
        st.subheader("1. 在图上移动框/划定分割区域")

        # 预先获取第 0 页以拿到总页数
        _, total_pages = get_pdf_page_image(pdf_bytes, 0)

        if total_pages > 1:
            selected_page_idx = st.selectbox(
                f"📄 该 PDF 共 {total_pages} 页，请选择当前要裁剪的页面：",
                options=list(range(total_pages)),
                format_func=lambda x: f"第 {x + 1} 页"
            )
        else:
            selected_page_idx = 0

        # 调用核心模块获取指定页图片
        pdf_img, _ = get_pdf_page_image(pdf_bytes, selected_page_idx)

        st.info("💡 移动或缩放红框选择需要的模块，然后点击下方【确认截取】。可以随时切换页面继续截取！")

        cropped_img = st_cropper(
            pdf_img,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=None,
            key=f"cropper_page_{selected_page_idx}"
        )

        if st.button("✂️ 确认截取此模块碎片", type="primary", use_container_width=True):
            target_w = 800
            w_pct = target_w / float(cropped_img.size[0])
            h_size = int(float(cropped_img.size[1]) * w_pct)
            resized_crop = cropped_img.resize((target_w, h_size), Image.Resampling.LANCZOS)

            st.session_state.fragments.append({
                "id": f"frag_{st.session_state.frag_counter}",
                "name": f"P{selected_page_idx+1} 模块碎片 #{st.session_state.frag_counter}",
                "image": resized_crop,
                "keep": True
            })
            st.session_state.frag_counter += 1
            st.success(f"✅ 已成功从第 {selected_page_idx+1} 页截取碎片！可在右侧管理。")
            st.rerun()

    # --- 3. 右侧：碎片卡片管理 ---
    with col_list:
        st.subheader("2. 碎片卡片管理 & 顺序调整")

        if not st.session_state.fragments:
            st.warning("👈 请在左侧选择页面、移动框并点击【确认截取】生成第一个碎片。")
        else:
            st.caption("💡 所有碎片都可以在这里混合自由上下排序：")
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

                    st.image(item["image"], use_container_width=True)

    # --- 4. 底部：导出 A4 PDF ---
    st.markdown("---")
    st.subheader("3. 最终重新排版与 PDF 预览")

    active_frags = [f for f in st.session_state.fragments if f["keep"]]

    if active_frags:
        preview_col, download_col = st.columns([2, 1])

        with preview_col:
            st.caption("📄 模拟 A4 最终打印流：")
            st.markdown('<div style="border:1px solid #ccc; padding:10px; background:#fff;">', unsafe_allow_html=True)
            for f in active_frags:
                st.image(f["image"], caption=f.get("name"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with download_col:
            pdf_data = build_reconstructed_pdf(active_frags)

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
