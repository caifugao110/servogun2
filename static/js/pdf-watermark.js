/**
 * PDF水印处理脚本
 * 为PDF下载添加水印功能
 */

// 引入PDF.js库
if (typeof pdfjsLib === 'undefined') {
    console.error('PDF.js library not loaded');
}

// 设置PDF.js worker路径
pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.worker.js';

/**
 * 为PDF添加水印并下载
 * @param {string} pdfUrl - PDF文件URL
 * @param {string} filename - 下载文件名
 */
async function downloadPDFWithWatermark(pdfUrl, filename) {
    try {
        // 显示加载提示
        const loadingModal = showLoadingModal('正在处理PDF文件，请稍候...');
        
        // 加载PDF文档
        const pdf = await pdfjsLib.getDocument(pdfUrl).promise;
        const numPages = pdf.numPages;
        
        // 创建新的PDF文档
        const { PDFDocument, rgb } = PDFLib;
        const pdfDoc = await PDFDocument.create();
        
        // 处理每一页
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            const page = await pdf.getPage(pageNum);
            const viewport = page.getViewport({ scale: 2.0 });
            
            // 创建canvas渲染页面
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            
            // 渲染PDF页面
            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;
            
            // 添加水印
            addWatermarkToCanvas(context, viewport.width, viewport.height);
            
            // 将canvas转换为图片并添加到新PDF
            const imageData = canvas.toDataURL('image/png');
            const pdfPage = pdfDoc.addPage([viewport.width, viewport.height]);
            const pngImage = await pdfDoc.embedPng(imageData);
            
            pdfPage.drawImage(pngImage, {
                x: 0,
                y: 0,
                width: viewport.width,
                height: viewport.height,
            });
        }
        
        // 生成PDF字节数据
        const pdfBytes = await pdfDoc.save();
        
        // 下载文件
        const blob = new Blob([pdfBytes], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // 关闭加载提示
        loadingModal.hide();
        
    } catch (error) {
        console.error('PDF处理失败:', error);
        showToast('PDF处理失败，请重试', 'danger');
    }
}

/**
 * 在canvas上添加水印
 * @param {CanvasRenderingContext2D} context - Canvas上下文
 * @param {number} width - Canvas宽度
 * @param {number} height - Canvas高度
 */
function addWatermarkToCanvas(context, width, height) {
    // 检测语言环境
    const isChinese = navigator.language.startsWith('zh');
    const watermarkBase = isChinese ? '仅供参考[OBARA]' : 'For Reference Only[OBARA]';
    const now = new Date();
    const dateStr = now.getFullYear() + '-' + (now.getMonth() + 1).toString().padStart(2, '0') + '-' + now.getDate().toString().padStart(2, '0');
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    const user = isChinese ? '当前用户' : 'Current User'; // 假设当前用户名为'当前用户'，实际应用中应从后端获取
    const watermarkText = `${watermarkBase} ${dateStr} ${timeStr} ${user}`;
    
    // 分割水印文本为两行
    const watermarkLines = [
        watermarkBase,
        `${user}     ${dateStr} ${timeStr}`
    ];
    
    context.save();
    context.fillStyle = 'rgba(255, 0, 0, 0.3)'; // 降低透明度避免过于显眼
    context.font = '24px Arial, sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.rotate(-Math.PI / 6); // 30度倾斜
    
    // 计算水印间距
    const lineHeight = 50;
    const stepX = 300;
    const stepY = 250;
    
    // 计算文字宽度并调整间距
    const textWidth = Math.max(
        context.measureText(watermarkLines[0]).width,
        context.measureText(watermarkLines[1]).width,
        context.measureText(watermarkLines[2]).width
    );
    const rotatedWidth = textWidth / Math.cos(Math.PI / 6);
    const adjustedStepX = Math.max(stepX, rotatedWidth * 1.2);
    
    // 网格状绘制水印
    for (let x = -200; x < width + 200; x += adjustedStepX) {
        for (let y = -100; y < height + 200; y += stepY) {
            watermarkLines.forEach((line, index) => {
                context.fillText(line, x, y + (index * lineHeight));
            });
        }
    }
    
    context.restore();
}

/**
 * 显示加载模态框
 * @param {string} message - 加载消息
 * @returns {Object} Bootstrap模态框实例
 */
function showLoadingModal(message) {
    const modalHtml = `
        <div class="modal fade" id="loadingModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mb-0">${message}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('loadingModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
    
    return modal;
}

/**
 * 显示Toast消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toast = new bootstrap.Toast(toastContainer.lastElementChild);
    toast.show();
}
