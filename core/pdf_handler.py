import io
import fitz  # PyMuPDF
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import reportlab.lib.utils

def get_pdf_page_image(pdf_bytes: bytes, page_num: int):
    """
    解析 PDF 并将指定页转换为 PIL Image 图像对象
    返回: (PIL.Image 对象, 总页数)
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    if page_num >= total_pages:
        page_num = 0

    page = doc[page_num]
    pix = page.get_pixmap(dpi=150)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img, total_pages


def build_reconstructed_pdf(active_fragments: list) -> io.BytesIO:
    """
    根据勾选的碎片列表，自动计算排版与智能分页，生成新的 A4 规格 PDF 字节流
    """
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    a4_w, a4_h = A4
    y_pos = a4_h - 20

    for item in active_fragments:
        img = item["image"]
        img_buf = io.BytesIO()
        img.save(img_buf, format="PNG")
        img_buf.seek(0)

        # 按 A4 宽度等比例缩放绘制高度
        draw_w = a4_w - 40
        draw_h = (img.height / img.width) * draw_w

        # 智能分页：如果当前页剩余高度不够放置该碎片，开启新一页
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
