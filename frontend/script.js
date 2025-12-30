const API_BASE_URL = 'http://localhost:5000/api';
let selectedFiles = [];

// DOM元素
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const actionButtons = document.getElementById('actionButtons');
const uploadBtn = document.getElementById('uploadBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultInfo = document.getElementById('resultInfo');
const downloadBtn = document.getElementById('downloadBtn');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const historyList = document.getElementById('historyList');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadHistory();
});

function setupEventListeners() {
    // 文件选择
    fileInput.addEventListener('change', handleFileSelect);

    // 拖拽上传
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        handleFileSelect({ target: { files: e.dataTransfer.files } });
    });
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    const allowedExtensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx'];

    files.forEach(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (allowedExtensions.includes(ext)) {
            if (!selectedFiles.find(f => f.name === file.name)) {
                selectedFiles.push(file);
            }
        } else {
            alert(`不支持的文件类型: ${file.name}`);
        }
    });

    updateFileList();
    fileInput.value = '';
}

function updateFileList() {
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        actionButtons.style.display = 'none';
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-icon">${getFileIcon(file.name)}</div>
                <div class="file-details">
                    <h4>${file.name}</h4>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
            </div>
            <button class="file-remove" onclick="removeFile(${index})">删除</button>
        </div>
    `).join('');

    actionButtons.style.display = 'flex';
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': 'PDF',
        'doc': 'DOC',
        'docx': 'DOC',
        'xls': 'XLS',
        'xlsx': 'XLS'
    };
    return icons[ext] || 'FILE';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

function clearFiles() {
    selectedFiles = [];
    updateFileList();
}

async function uploadFiles() {
    if (selectedFiles.length === 0) {
        alert('请选择至少一个文件');
        return;
    }

    // 隐藏上传区域，显示进度条
    document.querySelector('.upload-section').style.display = 'none';
    progressSection.style.display = 'block';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';

    // 创建FormData
    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    // 模拟进度
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 5;
        if (progress <= 90) {
            progressFill.style.width = progress + '%';
        }
    }, 200);

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        progressFill.style.width = '100%';

        const data = await response.json();

        if (response.ok && data.success) {
            // 显示成功结果
            setTimeout(() => {
                progressSection.style.display = 'none';
                resultSection.style.display = 'block';

                resultInfo.innerHTML = `
                    <p><strong>处理文件数量:</strong> ${data.data_summary.documents_count}</p>
                    <p><strong>提取关键词数据:</strong> ${data.data_summary.keywords_extracted} 条</p>
                    <p><strong>提取表格行数:</strong> ${data.data_summary.table_rows} 行</p>
                    <p><strong>提取条款数量:</strong> ${data.data_summary.clauses_found} 条</p>
                `;

                downloadBtn.onclick = () => downloadFile(data.output_file);
                loadHistory();
            }, 500);
        } else {
            throw new Error(data.error || '处理失败');
        }
    } catch (error) {
        clearInterval(progressInterval);
        progressSection.style.display = 'none';
        errorSection.style.display = 'block';
        errorMessage.textContent = error.message || '网络错误，请检查服务器是否运行';
    }
}

function downloadFile(filename) {
    window.open(`${API_BASE_URL}/download/${filename}`, '_blank');
}

function resetApp() {
    selectedFiles = [];
    document.querySelector('.upload-section').style.display = 'block';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
    updateFileList();
    loadHistory();
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/files`);
        const data = await response.json();

        if (data.files && data.files.length > 0) {
            historyList.innerHTML = data.files.map(file => `
                <div class="history-item">
                    <div class="history-info">
                        <h4>${file.filename}</h4>
                        <div class="history-meta">
                            大小: ${formatFileSize(file.size)} |
                            创建时间: ${new Date(file.created_at * 1000).toLocaleString('zh-CN')}
                        </div>
                    </div>
                    <button class="btn-download" onclick="downloadFile('${file.filename}')">
                        下载
                    </button>
                </div>
            `).join('');
        } else {
            historyList.innerHTML = '<p class="empty-message">暂无历史文件</p>';
        }
    } catch (error) {
        console.error('加载历史文件失败:', error);
        historyList.innerHTML = '<p class="empty-message">加载历史文件失败</p>';
    }
}
