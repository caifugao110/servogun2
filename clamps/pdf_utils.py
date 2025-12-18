# Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter


class PDFProcessor:
    """PDF处理工具类，提供水印添加等功能"""
    
    @staticmethod
    def create_watermark(watermark_text, output_path):
        """创建水印PDF文件，支持文件路径或BytesIO对象"""
        # 将页面尺寸设置为A4横向
        pagesize_landscape_a4 = landscape(A4)
        c = canvas.Canvas(output_path, pagesize=pagesize_landscape_a4)

        # 水印内容拆分为两行
        # 假设 watermark_text 格式为 "For Reference Only[OBARA] {username} {datetime}"
        # 第一行："For Reference Only[OBARA]"
        # 第二行："{username} {datetime}"
        if '[OBARA]' in watermark_text:
            prefix, suffix = watermark_text.split('[OBARA]', 1)
            line1 = prefix.strip() + '[OBARA]'
            line2 = suffix.strip()
        else:
            line1 = watermark_text
            line2 = ''

        # 调整字体大小和透明度
        font_size = 18  # 调整字体大小以合理填充纸张，减小
        c.setFillColor(Color(1, 0, 0, alpha=0.3))  # 红色，颜色改为红色
        c.setFont("Helvetica-Bold", font_size)

        # 旋转水印
        c.rotate(30)  # 调整旋转角度

        # 获取页面尺寸
        page_width, page_height = pagesize_landscape_a4

        # 计算水印的重复间隔和起始位置
        # 假设每行水印的宽度和高度
        line1_width = c.stringWidth(line1, "Helvetica-Bold", font_size)
        line2_width = c.stringWidth(line2, "Helvetica-Bold", font_size)
        max_line_width = max(line1_width, line2_width)
        line_height = font_size * 2  # 行高，略大于字体大小

        # 调整循环范围和步长，使水印合理填充整个纸张
        # 增加水印密度，调整x和y的步长
        x_step = max_line_width * 1.5  # 调整x方向的步长
        y_step = line_height * 4.5  # 调整y方向的步长

        # 调整起始位置，确保水印覆盖整个页面
        start_x = -page_width / 2
        start_y = -page_height / 2

        for x in range(int(start_x), int(page_width * 1.5), int(x_step)):
            for y in range(int(start_y), int(page_height * 1.5), int(y_step)):
                c.drawString(x, y, line1)
                c.drawString(x, y - line_height, line2)  # 第二行在第一行下方

        c.save()

    @staticmethod
    def add_watermark(input_pdf_path, output_pdf_path, watermark_text):
        """为PDF文件添加水印"""
        watermark_buffer = io.BytesIO()
        PDFProcessor.create_watermark(watermark_text, watermark_buffer)
        watermark_buffer.seek(0)
        watermark_pdf = PdfReader(watermark_buffer)
        watermark_page = watermark_pdf.pages[0]
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            page.merge_page(watermark_page)
            writer.add_page(page)
        with open(output_pdf_path, "wb") as output_file:
            writer.write(output_file)

    @staticmethod
    def validate_file_size(file_path, user_profile, is_batch=False):
        """验证文件大小是否满足下载条件"""
        import os
        if not os.path.exists(file_path):
            return False, "文件不存在"
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
        return user_profile.can_download_file(file_size_mb, is_batch)
