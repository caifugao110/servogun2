// Asynchronous compression download implementation

// WebSocket connection for real-time compression updates
let compressionWebSocket = null;

// Initialize WebSocket connection - handle failures gracefully
function initWebSocket() {
    // Skip WebSocket initialization altogether
    // The Django development server (runserver) doesn't support WebSockets
    // We'll rely on the polling fallback for all cases
    console.log('Skipping WebSocket initialization, using polling fallback');
    return;
    
    // Original WebSocket code (commented out)
    /*
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/compression/`;
    
    compressionWebSocket = new WebSocket(wsUrl);
    
    compressionWebSocket.onopen = function(event) {
        console.log('WebSocket connection opened for compression updates');
    };
    
    compressionWebSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('Compression update received:', data);
        
        // Update progress display if a callback is registered
        if (window.compressionCallbacks && window.compressionCallbacks[data.task_id]) {
            window.compressionCallbacks[data.task_id](data.progress, data.status === 'completed');
        }
    };
    
    compressionWebSocket.onclose = function(event) {
        console.log('WebSocket connection closed for compression updates');
        // Don't automatically reconnect to avoid continuous failed attempts
    };
    
    compressionWebSocket.onerror = function(error) {
        console.error('WebSocket error:', error);
        // Don't show error to user, just continue with polling
        console.log('WebSocket failed, falling back to periodic polling');
    };
    */
}

// Initialize compression callbacks object
window.compressionCallbacks = {};

// Initialize WebSocket when the page loads, but only if not on development server
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', initWebSocket);
}

// Start compression task
function startCompression(productIds, fileType, callback) {
    // Debug: Check what file type is actually being sent
    console.log('=== startCompression 函数调用开始 ===');
    console.log('参数 - productIds:', productIds);
    console.log('参数 - fileType:', fileType);
    
    // Prepare JSON data instead of FormData
    const requestData = {
        product_ids: productIds.join(','),
        file_type: fileType,
        language: window.location.pathname.includes('en') || window.location.pathname.includes('_en') ? 'en' : 'zh'
    };
    
    // Debug: Show the actual request data
    console.log('发送到服务器的请求数据:', requestData);
    
    // Start asynchronous compression with proper CSRF headers
    fetch('/async_compression/start/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.CSRF_TOKEN  // Use CSRF token in header
        },
        body: JSON.stringify(requestData),
        credentials: 'same-origin'  // Ensure cookies are sent
    })
    .then(response => response.json())
    .then(data => {
        console.log('服务器响应:', data);
        if (data.success) {
            callback(data.task_id);
        } else {
            showToast(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('启动压缩任务时出错:', error);
        showToast('Error starting compression, please try again later', 'danger');
    });
}

// Check compression progress
function checkCompressionProgress(taskId, callback) {
    fetch(`/async_compression/progress/?task_id=${taskId}`, {
        credentials: 'same-origin'  // Ensure cookies are sent
    })
    .then(response => response.json())
    .then(data => {
        callback(data.progress || 0, data.is_completed || false);
    })
    .catch(error => {
        console.error('Error checking compression progress:', error);
        callback(0, false);
    });
}

// Download compressed file
function downloadCompressedFile(taskId, fileType) {
    // First check if the compression is complete
    checkCompressionProgress(taskId, (progress, isCompleted) => {
        if (isCompleted) {
            // Create form and submit to download the compressed file
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/async_compression/download/';
            
            // Add CSRF token
            if (window.CSRF_TOKEN) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = window.CSRF_TOKEN;
                form.appendChild(csrfInput);
            }
            
            // Add task ID
            const taskIdInput = document.createElement('input');
            taskIdInput.type = 'hidden';
            taskIdInput.name = 'task_id';
            taskIdInput.value = taskId;
            form.appendChild(taskIdInput);
            
            // Add file type
            const fileTypeInput = document.createElement('input');
            fileTypeInput.type = 'hidden';
            fileTypeInput.name = 'file_type';
            fileTypeInput.value = fileType;
            form.appendChild(fileTypeInput);
            
            // Submit form
            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } else {
            // If not completed, show warning and continue checking
            showToast('压缩任务尚未完成，请稍候再试', 'warning');
            
            // Continue checking progress every 2 seconds
            let retryCount = 0;
            const maxRetries = 10;
            
            const retryInterval = setInterval(() => {
                checkCompressionProgress(taskId, (retryProgress, retryCompleted) => {
                    retryCount++;
                    
                    if (retryCompleted) {
                        clearInterval(retryInterval);
                        // Try download again
                        downloadCompressedFile(taskId, fileType);
                    } else if (retryCount >= maxRetries) {
                        clearInterval(retryInterval);
                        showToast('压缩任务超时，请稍后手动重试', 'danger');
                    }
                });
            }, 2000);
        }
    });
}